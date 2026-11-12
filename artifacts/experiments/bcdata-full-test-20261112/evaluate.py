"""Audit and evaluate the locked BCData official test split on local source data.

No training, resizing, calibration, or downloaded code execution. Public outputs
contain file hashes and ROI aggregates; optional cell records go only to a private
path explicitly supplied by the caller. Research use, not clinical validation.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import gzip
import hashlib
import importlib
import json
from pathlib import Path
import statistics
import sys
import time
import zlib

EVIDENCE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def locked_inputs(repo, data_dir):
    protocol = read(EVIDENCE / "diagnostic-protocol.json")
    assert sha(EVIDENCE / "protocol.json") == protocol["supersedes_strict_protocol_sha256"]
    assert sha(EVIDENCE / "strict-input-audit.json") == protocol["strict_input_audit_sha256"]
    for path_key, hash_key in [("model_path", "model_sha256"), ("feature_module_path", "feature_module_sha256"),
                               ("prior_protocol_path", "prior_protocol_sha256"), ("prior_results_path", "prior_results_sha256")]:
        assert sha(repo / protocol[path_key]) == protocol[hash_key], path_key
    assert sha(EVIDENCE / "archive-test-manifest.json") == protocol["archive_test_manifest_sha256"]
    archive = read(EVIDENCE / "archive-test-manifest.json")
    manifest = read(EVIDENCE / "input-manifest.json")
    assert len(archive) == len(manifest) == 1206
    assert len({e["name"] for e in manifest}) == 1206
    archive_by_name = {e["name"]: e for e in archive}
    for entry in manifest:
        assert {k: entry[k] for k in archive_by_name[entry["name"]]} == archive_by_name[entry["name"]]
        data = (data_dir / entry["name"]).read_bytes()
        assert len(data) == entry["uncompressed_bytes"]
        assert zlib.crc32(data) == entry["crc32"]
        assert hashlib.sha256(data).hexdigest() == entry["sha256"]
    images = sorted(e["name"] for e in manifest if e["name"].startswith("BCData/images/test/"))
    assert images == protocol["selected_images"] and len(images) == 402
    required = set(images)
    for name in images:
        for label in ("positive", "negative"):
            required.add(f"BCData/annotations/test/{label}/{Path(name).stem}.h5")
    assert required == {e["name"] for e in manifest}
    return protocol, manifest


def load_sample(data_dir, image_name):
    import h5py
    import numpy as np
    from PIL import Image

    with Image.open(data_dir / image_name) as image:
        assert image.mode == "RGB" and image.size == (640, 640)
        rgb = np.asarray(image)
        image_info_keys = sorted(image.info)
    from canonicalize import canonicalize
    sources, arrays = [], []
    for label in ("positive", "negative"):
        relative = f"BCData/annotations/test/{label}/{Path(image_name).stem}.h5"
        with h5py.File(data_dir / relative, "r") as handle:
            assert list(handle) == ["coordinates"]
            coords = handle["coordinates"][:]
            arrays.append(coords)
            sources.append({"file": relative, "shape": list(coords.shape), "dtype": str(coords.dtype),
                            "file_attribute_names": sorted(handle.attrs),
                            "coordinate_attribute_names": sorted(handle["coordinates"].attrs)})
    canonical = canonicalize(*arrays, width=640, height=640)
    # Hash-locked source audit found no exclusions other than same-label repeats.
    assert canonical["excluded"] == [] and canonical["cross_label_conflicting_locations"] == 0
    points, truth = canonical["points"], canonical["truth"]
    assert len(points) > 0 and len(np.unique(points, axis=0)) == len(points), image_name
    for source, counts in zip(sources, canonical["class_counts"]):
        source.update({key: counts[key] for key in ("raw_records", "unique_centers", "duplicate_excess_records")})
    duplicate_map = [{"file": sources[row["class"]]["file"], "source_row_index": row["source_row_index"],
                      "first_source_row_index": row["first_source_row_index"], "point": row["point"]}
                     for row in canonical["duplicates"]]
    raw_count = sum(c["raw_records"] for c in canonical["class_counts"])
    repeated_locations = sum(c["repeated_locations"] for c in canonical["class_counts"])
    empty_shapes = sum(c["empty_shape_normalized"] for c in canonical["class_counts"])
    metadata = {
        "image": image_name, "shape": list(rgb.shape), "dtype": str(rgb.dtype),
        "image_metadata_keys": image_info_keys, "point_sources": sources,
        "gt_positive": int((truth == 0).sum()), "gt_negative": int((truth == 1).sum()),
        "raw_records": raw_count, "unique_centers": len(points),
        "same_label_duplicate_excess_records": len(duplicate_map),
        "same_label_repeated_locations": repeated_locations,
        "empty_shape_annotation_files": empty_shapes,
        "source_quality": "affected_66" if duplicate_map or empty_shapes else "clean_336",
        "pixel_sha256": hashlib.sha256(rgb.tobytes()).hexdigest(),
    }
    return rgb, points, truth, metadata, duplicate_map


def duplicate_groups(records, key):
    groups = defaultdict(list)
    for record in records:
        groups[record[key]].append(record["name"] if "name" in record else record["image"])
    return [names for names in groups.values() if len(names) > 1]


def audit(repo, data_dir, output_dir, canonical_points):
    protocol, manifest = locked_inputs(repo, data_dir)
    assert canonical_points is not None and not canonical_points.exists()
    assert not canonical_points.resolve().is_relative_to(EVIDENCE.resolve())
    observations = []
    canonical_points.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(canonical_points, "xt", encoding="utf-8") as stream:
        for name in protocol["selected_images"]:
            _, points, truth, metadata, duplicate_map = load_sample(data_dir, name)
            observations.append(metadata)
            stream.write(json.dumps({"image": name, "points": points.tolist(), "truth": truth.tolist(),
                                     "duplicate_source_row_map": duplicate_map}, separators=(",", ":"), allow_nan=False) + "\n")
    images = [e for e in manifest if e["name"].endswith(".png")]
    prior_source = (repo / "artifacts/ihc/source-manifest.json").read_text()
    result = {
        "completed_utc": datetime.now(timezone.utc).isoformat(),
        "protocol_sha256": sha(EVIDENCE / "diagnostic-protocol.json"),
        "strict_original_protocol_passed": False,
        "diagnostic_amendment_passed": True,
        "canonical_points_and_duplicate_map_sha256": sha(canonical_points),
        "input_manifest_sha256": sha(EVIDENCE / "input-manifest.json"),
        "image_count": len(observations), "input_file_count": len(manifest),
        "input_raw_bytes": sum(e["uncompressed_bytes"] for e in manifest),
        "all_input_crc32_size_and_sha256_verified": True,
        "all_canonical_coordinates_numeric_finite_integer_in_bounds_unique_and_nonconflicting": True,
        "raw_annotation_records": sum(e["raw_records"] for e in observations),
        "same_label_duplicate_excess_records": sum(e["same_label_duplicate_excess_records"] for e in observations),
        "same_label_repeated_locations": sum(e["same_label_repeated_locations"] for e in observations),
        "empty_shape_annotation_files": sum(e["empty_shape_annotation_files"] for e in observations),
        "clean_images": sum(e["source_quality"] == "clean_336" for e in observations),
        "affected_images": sum(e["source_quality"] == "affected_66" for e in observations),
        "zero_eligible_center_images": [],
        "noninteger_nonfinite_out_of_bounds_or_conflicting_records": 0,
        "duplicate_whole_file_groups": duplicate_groups(images, "sha256"),
        "duplicate_whole_pixel_groups": duplicate_groups(observations, "pixel_sha256"),
        "exact_image_file_hash_matches_to_Patherea_source_manifest": [e["name"] for e in images if e["sha256"] in prior_source],
        "total_points": sum(e["gt_positive"] + e["gt_negative"] for e in observations),
        "gt_positive": sum(e["gt_positive"] for e in observations),
        "gt_negative": sum(e["gt_negative"] for e in observations),
        "images": observations,
        "limitations": ["No patient/slide map; no proof of patient independence.",
                        "Whole-image hash checks do not exclude near-duplicate or subimage overlap.",
                        "No verified per-image microns-per-pixel; native pixels retained."]}
    write(output_dir / "input-audit.json", result)
    print(json.dumps({k: result[k] for k in ("image_count", "input_file_count", "total_points", "gt_positive", "gt_negative", "duplicate_whole_file_groups", "duplicate_whole_pixel_groups")}), flush=True)


def summarize(per_image, baseline, np):
    matrix = np.array([r["metrics"]["confusion_matrix"] for r in per_image]).sum(axis=0)
    truth, predicted = [], []
    for i in range(4):
        for j in range(4):
            truth.extend([i] * int(matrix[i, j]))
            predicted.extend([j] * int(matrix[i, j]))
    metrics = baseline.classification_metrics(np.asarray(truth), np.asarray(predicted))
    errors = [r["tumor_ratio"]["absolute_error_percentage_points"] for r in per_image
              if r["tumor_ratio"]["absolute_error_percentage_points"] is not None]
    defined = [r for r in per_image if r["tumor_ratio"]["absolute_error_percentage_points"] is not None]
    extrema = {}
    for label, rows, accessor in [
        ("ratio_absolute_error_pp", defined, lambda r: r["tumor_ratio"]["absolute_error_percentage_points"]),
        ("accuracy", per_image, lambda r: r["metrics"]["accuracy"]),
    ]:
        if not rows:
            extrema[label] = None
            continue
        lo, hi = min(map(accessor, rows)), max(map(accessor, rows))
        extrema[label] = {
            "minimum": lo, "minimum_images": sorted(r["image"] for r in rows if accessor(r) == lo),
            "maximum": hi, "maximum_images": sorted(r["image"] for r in rows if accessor(r) == hi),
            "ascending_first_five": [r["image"] for r in sorted(rows, key=lambda r: (accessor(r), r["image"]))[:5]],
            "descending_first_five": [r["image"] for r in sorted(rows, key=lambda r: (-accessor(r), r["image"]))[:5]],
        }
    return {
        "image_count": len(per_image), "metrics": metrics,
        "reference_tumor_classes_mean_f1": sum(x["f1"] for x in metrics["per_class"][:2]) / 2,
        "predicted_nontumor_at_GT_tumor_centers": int(matrix[:, 2:].sum()),
        "mean_per_image_absolute_error_percentage_points": sum(errors) / len(errors) if errors else None,
        "median_per_image_absolute_error_percentage_points": statistics.median(errors) if errors else None,
        "ratio_defined_images": len(errors),
        "undefined_gt_denominator_images": [r["image"] for r in per_image if r["tumor_ratio"]["gt"] is None],
        "undefined_predicted_denominator_images": [r["image"] for r in per_image if r["tumor_ratio"]["predicted"] is None],
        "extrema": extrema,
    }
    assert (result["raw_annotation_records"], result["same_label_duplicate_excess_records"], result["total_points"], result["clean_images"], result["affected_images"]) == (65432, 267, 65165, 336, 66)


def evaluate(repo, data_dir, output_dir, private_predictions, canonical_points):
    protocol, _ = locked_inputs(repo, data_dir)
    audit_result = read(output_dir / "input-audit.json")
    assert audit_result["protocol_sha256"] == sha(EVIDENCE / "diagnostic-protocol.json")
    assert audit_result["input_manifest_sha256"] == sha(EVIDENCE / "input-manifest.json")
    assert audit_result["diagnostic_amendment_passed"] is True
    assert canonical_points is not None
    assert sha(canonical_points) == audit_result["canonical_points_and_duplicate_map_sha256"]
    with gzip.open(canonical_points, "rt", encoding="utf-8") as stream:
        canonical_records = [json.loads(line) for line in stream]
    assert [r["image"] for r in canonical_records] == protocol["selected_images"]
    assert private_predictions is not None and not private_predictions.exists()
    # Ensure source data and cell records cannot accidentally enter this public bundle.
    assert not private_predictions.resolve().is_relative_to(EVIDENCE.resolve())
    assert not data_dir.resolve().is_relative_to(EVIDENCE.resolve())
    sys.path.insert(0, str(repo / "src"))
    baseline = importlib.import_module("pathology_edge.ihc_baseline")
    import h5py
    import numpy as np
    import scipy
    import PIL

    model = read(repo / protocol["model_path"])
    assert model["classes"] == list(baseline.CLASSES) and model["feature_radii_pixels"] == [3, 7]
    lock = {
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "protocol_sha256": sha(EVIDENCE / "diagnostic-protocol.json"),
        "strict_protocol_sha256": sha(EVIDENCE / "protocol.json"),
        "canonical_points_and_duplicate_map_sha256": sha(canonical_points),
        "input_manifest_sha256": sha(EVIDENCE / "input-manifest.json"),
        "input_audit_sha256": sha(output_dir / "input-audit.json"),
        "model_sha256": protocol["model_sha256"], "feature_module_sha256": protocol["feature_module_sha256"],
        "runner_sha256": sha(Path(__file__)),
        "canonicalizer_sha256": sha(EVIDENCE / "canonicalize.py"), "training_or_tuning": False,
        "new_images": 392, "previously_evaluated_images": 10,
    }
    write(output_dir / "inference-lock.json", lock)
    private_predictions.parent.mkdir(parents=True, exist_ok=True)
    per_image = []
    previous = set(protocol["previously_evaluated_images"])
    start = time.perf_counter()
    with gzip.open(private_predictions, "xt", encoding="utf-8") as stream:
        for canonical in canonical_records:
            name = canonical["image"]
            rgb, points, truth, metadata, duplicate_map = load_sample(data_dir, name)
            assert points.tolist() == canonical["points"] and truth.tolist() == canonical["truth"]
            assert duplicate_map == canonical["duplicate_source_row_map"]
            probability = baseline.predict_proba(baseline.extract_features(rgb, points), model)
            assert probability.shape == (len(points), 4) and np.isfinite(probability).all()
            assert np.allclose(probability.sum(axis=1), 1)
            predicted = probability.argmax(axis=1)
            per_image.append({"image": name, "cohort": "previous_10" if name in previous else "new_392",
                              "source_quality": metadata["source_quality"],
                              "raw_annotation_records": metadata["raw_records"],
                              "same_label_duplicate_excess_records": metadata["same_label_duplicate_excess_records"],
                              "metrics": baseline.classification_metrics(truth, predicted),
                              "tumor_ratio": baseline.tumor_ratios(truth, predicted)})
            stream.write(json.dumps({"image": name, "points": points.tolist(), "truth": truth.tolist(),
                                     "predicted": predicted.tolist(), "probabilities": probability.tolist()},
                                    separators=(",", ":"), allow_nan=False) + "\n")
            if len(per_image) % 50 == 0:
                print(json.dumps({"evaluated_images": len(per_image), "wall_seconds": time.perf_counter()-start}), flush=True)
    prior_rows = read(repo / protocol["prior_results_path"])["per_image"]
    repeated = [{k: r[k] for k in ("image", "metrics", "tumor_ratio")} for r in per_image if r["cohort"] == "previous_10"]
    assert repeated == prior_rows, "Previously evaluated 10 ROIs changed"
    groups = {"all_402": summarize(per_image, baseline, np)}
    for cohort in ("new_392", "previous_10"):
        groups[cohort] = summarize([r for r in per_image if r["cohort"] == cohort], baseline, np)
    for quality in ("clean_336", "affected_66"):
        groups[quality] = summarize([r for r in per_image if r["source_quality"] == quality], baseline, np)
    result = {
        "schema": "bcdata-full-official-test-diagnostic-results-v2", "scope": protocol["purpose"],
        "strict_original_protocol_passed": False, "diagnostic_amendment_passed": True,
        "raw_annotation_records": 65432, "unique_evaluated_centers": 65165,
        "same_label_duplicate_excess_records": 267,
        "completed_utc": datetime.now(timezone.utc).isoformat(),
        "inference_lock_sha256": sha(output_dir / "inference-lock.json"),
        "private_predictions_sha256": sha(private_predictions),
        "model_sha256": protocol["model_sha256"], "patient_count": None,
        "groups": groups, "per_image": per_image,
        "previous_10_per_image_metrics_exactly_match_prior_published_results": True,
        "wall_seconds_including_reading_features_inference_and_aggregate_reporting": time.perf_counter()-start,
        "software": {"python": sys.version.split()[0], "numpy": np.__version__, "scipy": scipy.__version__,
                     "pillow": PIL.__version__, "h5py": h5py.__version__},
        "limitations": ["All 402 official test images, but 10 were previously observed; 392 newly evaluated are reported separately.",
                        "The strict original protocol failed. Diagnostic amendment removes 267 repeated same-class records and normalizes 3 empty shape(0,) arrays before inference. Unique coordinates do not establish biological cell identity.",
                        "No patient/slide mapping or clinical endpoints; no patient independence or clinical-validity claim.",
                        "Tumor GT centers only: no detection, nontumor references, tumor-area selection, or full-WSI scoring.",
                        "Two absent nontumor GT classes have zero support; four-class macro-F1 keeps zero_division=0 and is not comparable to a four-class reference dataset.",
                        "Native pixels; physical-scale equivalence is not established.",
                        "No new blinded pathologist scoring or clinical adjudication."]}
    write(output_dir / "results.json", result)
    print(json.dumps({name: {k: group[k] for k in ("image_count", "metrics", "mean_per_image_absolute_error_percentage_points", "ratio_defined_images", "undefined_predicted_denominator_images")} for name, group in groups.items()}, indent=2), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("audit", "evaluate"))
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--private-predictions", type=Path)
    parser.add_argument("--canonical-points", type=Path, required=True,
                        help="Private gzip JSONL map, created by audit and hash-verified by evaluate")
    parser.add_argument("--repo", type=Path, default=EVIDENCE.parents[2])
    args = parser.parse_args()
    if args.stage == "audit":
        audit(args.repo, args.data_dir, args.output_dir, args.canonical_points)
    else:
        evaluate(args.repo, args.data_dir, args.output_dir, args.private_predictions, args.canonical_points)


if __name__ == "__main__":
    main()
