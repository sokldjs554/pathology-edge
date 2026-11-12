"""Independently recount persisted BCData predictions and verify source hashes.

This verifier does not import the evaluator or the project metric functions.
It reads original HDF5 coordinates locally; its output is aggregate evidence only.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import statistics
import zlib

CLASSES = ["positive_tumor_cell", "negative_tumor_cell", "others_positive", "others_negative"]


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def metrics(matrix):
    total = sum(map(sum, matrix))
    per_class = []
    for k, name in enumerate(CLASSES):
        tp, support, calls = matrix[k][k], sum(matrix[k]), sum(row[k] for row in matrix)
        per_class.append({"id": k, "name": name, "precision": tp/calls if calls else 0.0,
                          "recall": tp/support if support else 0.0,
                          "f1": 2*tp/(support+calls) if support+calls else 0.0, "support": support})
    return {"accuracy": sum(matrix[k][k] for k in range(4))/total,
            "macro_f1": sum(row["f1"] for row in per_class)/4,
            "per_class": per_class, "confusion_matrix": matrix, "cell_count": total}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--canonical-points", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--evidence-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--results-dir", type=Path,
                        help="Fresh replay directory containing audit, inference lock, and results; defaults to evidence-dir")
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[3])
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    import h5py
    import numpy as np
    from PIL import Image

    evidence = args.evidence_dir
    result_dir = args.results_dir or evidence
    protocol = read(evidence / "diagnostic-protocol.json")
    lock, results = [read(result_dir / name) for name in ("inference-lock.json", "results.json")]
    hash_checks = {
        "protocol_sha256": (evidence / "diagnostic-protocol.json", lock["protocol_sha256"]),
        "strict_protocol_sha256": (evidence / "protocol.json", lock["strict_protocol_sha256"]),
        "canonicalizer_sha256": (evidence / "canonicalize.py", lock["canonicalizer_sha256"]),
        "canonical_points_and_duplicate_map_sha256": (args.canonical_points, lock["canonical_points_and_duplicate_map_sha256"]),
        "input_manifest_sha256": (evidence / "input-manifest.json", lock["input_manifest_sha256"]),
        "input_audit_sha256": (result_dir / "input-audit.json", lock["input_audit_sha256"]),
        "model_sha256": (args.repo / protocol["model_path"], lock["model_sha256"]),
        "feature_module_sha256": (args.repo / protocol["feature_module_path"], lock["feature_module_sha256"]),
        "runner_sha256": (evidence / "evaluate.py", lock["runner_sha256"]),
        "inference_lock_sha256": (result_dir / "inference-lock.json", results["inference_lock_sha256"]),
        "private_predictions_sha256": (args.predictions, results["private_predictions_sha256"]),
    }
    for key, (path, expected) in hash_checks.items():
        assert sha(path) == expected, key
    assert sha(evidence / "strict-input-audit.json") == protocol["strict_input_audit_sha256"]
    with gzip.open(args.canonical_points, "rt", encoding="utf-8") as stream:
        canonical_records = [json.loads(line) for line in stream]
    assert [r["image"] for r in canonical_records] == protocol["selected_images"]
    canonical_by_image = {r["image"]: r for r in canonical_records}
    manifest = read(evidence / "input-manifest.json")
    assert len(manifest) == 1206 and len({row["name"] for row in manifest}) == 1206
    for entry in manifest:
        data = (args.data_dir / entry["name"]).read_bytes()
        assert len(data) == entry["uncompressed_bytes"]
        assert zlib.crc32(data) == entry["crc32"]
        assert hashlib.sha256(data).hexdigest() == entry["sha256"]
    audit_images = {row["image"]: row for row in read(result_dir / "input-audit.json")["images"]}
    strict_images = {row["image"]: row for row in read(evidence / "strict-input-audit.json")["per_image"]}
    reported = {row["image"]: row for row in results["per_image"]}
    assert len(reported) == 402
    names, rows = [], []
    with gzip.open(args.predictions, "rt", encoding="utf-8") as stream:
        for line in stream:
            saved = json.loads(line)
            name = saved["image"]
            names.append(name)
            original_points, original_labels, duplicates = [], [], []
            raw_count, empty_shapes = 0, 0
            for label, target in (("positive", 0), ("negative", 1)):
                relative = f"BCData/annotations/test/{label}/{Path(name).stem}.h5"
                with h5py.File(args.data_dir / relative, "r") as handle:
                    coords = handle["coordinates"][:]
                    strict_label = strict_images[name]["labels"][label]
                    assert list(coords.shape) == strict_label["shape"]
                    assert str(coords.dtype) == strict_label["dtype"]
                    assert len(coords) == strict_label["records"]
                    if coords.shape == (0,):
                        empty_shapes += 1
                        coords = coords.reshape(0, 2)
                    assert coords.ndim == 2 and coords.shape[1] == 2
                    assert np.isfinite(coords).all() and (coords == np.floor(coords)).all()
                    assert ((coords >= 0) & (coords < 640)).all()
                    counts = Counter(tuple(point) for point in coords.tolist())
                    assert sum(n-1 for n in counts.values()) == strict_label["same_label_duplicate_excess_records"]
                    assert sum(n>1 for n in counts.values()) == strict_label["same_label_repeated_locations"]
                    assert strict_label["nonfinite_records"] == strict_label["noninteger_records"] == strict_label["out_of_bounds_records"] == 0
                    raw_count += len(coords)
                    seen = {}
                    for index, point in enumerate(coords.astype(int).tolist()):
                        key = tuple(point)
                        if key in seen:
                            duplicates.append({"file": relative, "source_row_index": index,
                                               "first_source_row_index": seen[key], "point": point})
                        else:
                            seen[key] = index
                            original_points.append(point)
                            original_labels.append(target)
            assert len(original_points) == len({tuple(point) for point in original_points}) > 0
            assert saved["points"] == original_points and saved["truth"] == original_labels
            assert canonical_by_image[name] == {"image": name, "points": original_points, "truth": original_labels,
                                                "duplicate_source_row_map": duplicates}
            quality = "affected_66" if duplicates or empty_shapes else "clean_336"
            assert strict_images[name]["strict_valid"] == (quality == "clean_336")
            assert strict_images[name]["cross_label_conflicting_locations"] == strict_images[name]["cross_label_conflicting_records"] == 0
            assert reported[name]["source_quality"] == quality == audit_images[name]["source_quality"]
            assert raw_count == reported[name]["raw_annotation_records"] == audit_images[name]["raw_records"]
            assert len(duplicates) == reported[name]["same_label_duplicate_excess_records"] == audit_images[name]["same_label_duplicate_excess_records"]
            assert len(saved["truth"]) == len(saved["predicted"]) == len(saved["probabilities"])
            with Image.open(args.data_dir / name) as image:
                assert image.mode == "RGB" and image.size == (640, 640)
                assert hashlib.sha256(np.asarray(image).tobytes()).hexdigest() == audit_images[name]["pixel_sha256"]
            matrix = [[0]*4 for _ in range(4)]
            predicted_counts = [0]*4
            for target, guess, probability in zip(saved["truth"], saved["predicted"], saved["probabilities"]):
                assert target in (0, 1) and guess in range(4)
                assert len(probability) == 4 and all(0 <= p <= 1 for p in probability)
                assert abs(sum(probability)-1) < 1e-12
                assert guess == max(range(4), key=lambda k: probability[k])
                matrix[target][guess] += 1
                predicted_counts[guess] += 1
            actual = metrics(matrix)
            assert actual == reported[name]["metrics"], name
            n = len(saved["truth"])
            gt_positive = sum(target == 0 for target in saved["truth"])
            gt, pred_n = gt_positive / n, sum(predicted_counts[:2])
            predicted = predicted_counts[0] / pred_n if pred_n else None
            ratio = {"gt": gt, "predicted": predicted, "gt_tumor_cell_count": n,
                     "predicted_tumor_cell_count": pred_n,
                     "absolute_error_percentage_points": abs(gt-predicted)*100 if predicted is not None else None,
                     "scope": "annotated_cells_at_GT_centers_only; not a whole-slide or clinical Ki67 index"}
            assert ratio == reported[name]["tumor_ratio"], name
            cohort = "previous_10" if name in protocol["previously_evaluated_images"] else "new_392"
            assert cohort == reported[name]["cohort"]
            rows.append({"image": name, "cohort": cohort, "source_quality": quality,
                         "raw_records": raw_count, "duplicate_excess": len(duplicates),
                         "matrix": matrix, "accuracy": actual["accuracy"],
                         "ratio": ratio, "gt_positive": gt_positive, "gt_negative": n-gt_positive,
                         "predicted_counts": predicted_counts})
    assert names == protocol["selected_images"] and len(names) == 402
    assert sum(r["raw_records"] for r in rows) == results["raw_annotation_records"] == 65432
    assert sum(r["duplicate_excess"] for r in rows) == results["same_label_duplicate_excess_records"] == 267
    checks = {}
    for group_name, expected in results["groups"].items():
        selected = rows if group_name == "all_402" else [r for r in rows if r["cohort"] == group_name or r["source_quality"] == group_name]
        matrix = [[sum(row["matrix"][i][j] for row in selected) for j in range(4)] for i in range(4)]
        assert metrics(matrix) == expected["metrics"]
        errors = [r["ratio"]["absolute_error_percentage_points"] for r in selected
                  if r["ratio"]["absolute_error_percentage_points"] is not None]
        assert len(selected) == expected["image_count"]
        assert len(errors) == expected["ratio_defined_images"]
        assert sum(errors)/len(errors) == expected["mean_per_image_absolute_error_percentage_points"]
        assert statistics.median(errors) == expected["median_per_image_absolute_error_percentage_points"]
        assert [] == expected["undefined_gt_denominator_images"]
        assert [r["image"] for r in selected if r["ratio"]["predicted"] is None] == expected["undefined_predicted_denominator_images"]
        assert sum(row[2]+row[3] for row in matrix) == expected["predicted_nontumor_at_GT_tumor_centers"]
        assert sum(r["f1"] for r in metrics(matrix)["per_class"][:2])/2 == expected["reference_tumor_classes_mean_f1"]
        for label, getter in [("accuracy", lambda r: r["accuracy"]),
                              ("ratio_absolute_error_pp", lambda r: r["ratio"]["absolute_error_percentage_points"])]:
            valid = [r for r in selected if getter(r) is not None]
            extrema = expected["extrema"][label]
            lo, hi = min(map(getter, valid)), max(map(getter, valid))
            assert lo == extrema["minimum"] and hi == extrema["maximum"]
            assert sorted(r["image"] for r in valid if getter(r) == lo) == extrema["minimum_images"]
            assert sorted(r["image"] for r in valid if getter(r) == hi) == extrema["maximum_images"]
            assert [r["image"] for r in sorted(valid, key=lambda r: (getter(r), r["image"]))[:5]] == extrema["ascending_first_five"]
            assert [r["image"] for r in sorted(valid, key=lambda r: (-getter(r), r["image"]))[:5]] == extrema["descending_first_five"]
        checks[group_name] = {"image_count": len(selected), "cell_count": sum(map(sum, matrix)), "all_metrics_ratios_and_extrema_recounted": True}
    output = {"verified_utc": datetime.now(timezone.utc).isoformat(),
              "verifier_sha256": sha(Path(__file__)), "results_sha256": sha(result_dir / "results.json"),
              "unchanged_hashes": {key: True for key in hash_checks},
              "source_input_files_rehashed_crc32_size_sha256": len(manifest),
              "original_HDF5_to_canonical_points_labels_and_duplicate_map_independently_verified": True,
              "strict_failure_audit_recounted_from_original_HDF5": True,
              "saved_probability_argmax_verified": True,
              "independent_of_project_metric_implementation": True,
              "per_image_metrics_ratios_and_pixel_hashes_verified": len(rows), "groups": checks,
              "per_image_counts": [{k: r[k] for k in ("image", "cohort", "source_quality", "raw_records", "duplicate_excess", "gt_positive", "gt_negative", "predicted_counts")} for r in rows]}
    if result_dir.resolve() != evidence.resolve():
        published = read(evidence / "results.json")
        assert results["groups"] == published["groups"]
        assert results["per_image"] == published["per_image"]
        output["fresh_replay_all_groups_and_per_image_results_match_published"] = True
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        json.dump(output, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"verified": True, "groups": checks, "input_files": len(manifest)}))


if __name__ == "__main__":
    main()
