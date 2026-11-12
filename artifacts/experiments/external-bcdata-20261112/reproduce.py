"""Replay the locked BCData check on independently acquired local source files.

Outputs aggregate results only. This small research runner does not download or
redistribute source data and is not a clinical or whole-slide evaluation system.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import importlib
import json
from pathlib import Path
import sys


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True,
                        help="Directory containing BCData/images and BCData/annotations")
    parser.add_argument("--output", type=Path, required=True,
                        help="New aggregate JSON file; existing files are never overwritten")
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[3])
    args = parser.parse_args()
    evidence = Path(__file__).resolve().parent
    protocol = read_json(evidence / "protocol.json")
    lock = read_json(evidence / "inference-lock.json")
    if args.output.exists():
        raise FileExistsError(args.output)
    assert sha256(evidence / "protocol.json") == lock["protocol_sha256"]
    assert sha256(evidence / "selected-manifest.json") == lock["selected_manifest_sha256"]
    assert sha256(args.repo / protocol["model_path"]) == lock["model_sha256"]
    assert sha256(args.repo / protocol["feature_module_path"]) == lock["feature_module_sha256"]
    manifest = read_json(evidence / "selected-manifest.json")
    for entry in manifest:
        source = args.data_dir / entry["name"]
        assert source.stat().st_size == entry["uncompressed_bytes"], source
        assert sha256(source) == entry["sha256"], source

    # Import only the verified local project feature/model implementation.
    sys.path.insert(0, str(args.repo / "src"))
    baseline = importlib.import_module("pathology_edge.ihc_baseline")
    import h5py
    import numpy as np
    from PIL import Image

    model = read_json(args.repo / protocol["model_path"])
    assert model["classes"] == list(baseline.CLASSES)
    assert model["feature_radii_pixels"] == [3, 7]
    matrices, per_image, truth_all, predicted_all = [], [], [], []
    for name in protocol["selected_images"]:
        with Image.open(args.data_dir / name) as image:
            assert image.mode == "RGB" and image.size == (640, 640)
            rgb = np.asarray(image)
        points, truth = [], []
        for label, target in [("positive", 0), ("negative", 1)]:
            source = args.data_dir / "BCData/annotations/test" / label / f"{Path(name).stem}.h5"
            with h5py.File(source) as handle:
                assert list(handle) == ["coordinates"]
                values = handle["coordinates"][:]
                assert values.ndim == 2 and values.shape[1] == 2
                assert np.isfinite(values).all() and (values == np.floor(values)).all()
                assert ((values >= 0) & (values < 640)).all()
                points.extend(values.tolist())
                truth.extend([target] * len(values))
        points = np.asarray(points, dtype=np.int64).reshape(-1, 2)
        truth = np.asarray(truth, dtype=np.int64)
        assert len(points) and len(np.unique(points, axis=0)) == len(points)
        probabilities = baseline.predict_proba(baseline.extract_features(rgb, points), model)
        assert np.isfinite(probabilities).all() and np.allclose(probabilities.sum(1), 1)
        predicted = probabilities.argmax(1)
        metrics = baseline.classification_metrics(truth, predicted)
        # Independent integer counts verify the four-class confusion matrix.
        counts = defaultdict(int)
        for target, guess in zip(truth.tolist(), predicted.tolist()):
            counts[target, guess] += 1
        assert metrics["confusion_matrix"] == [[counts[i, j] for j in range(4)] for i in range(4)]
        per_image.append({"image": name, "metrics": metrics,
                          "tumor_ratio": baseline.tumor_ratios(truth, predicted)})
        truth_all.extend(truth.tolist())
        predicted_all.extend(predicted.tolist())
        matrices.append(metrics["confusion_matrix"])
    metrics = baseline.classification_metrics(np.asarray(truth_all), np.asarray(predicted_all))
    assert metrics["confusion_matrix"] == np.asarray(matrices).sum(0).tolist()
    errors = [item["tumor_ratio"]["absolute_error_percentage_points"] for item in per_image
              if item["tumor_ratio"]["absolute_error_percentage_points"] is not None]
    result = {
        "scope": protocol["purpose"],
        "protocol_sha256": sha256(evidence / "protocol.json"),
        "model_sha256": lock["model_sha256"],
        "selected_manifest_sha256": sha256(evidence / "selected-manifest.json"),
        "reproduction_runner_sha256": sha256(Path(__file__)),
        "image_count": len(per_image), "patient_count": None,
        "metrics": metrics,
        "reference_tumor_classes_mean_f1": sum(x["f1"] for x in metrics["per_class"][:2])/2,
        "per_image": per_image,
        "mean_per_image_absolute_error_percentage_points": sum(errors)/len(errors) if errors else None,
        "ratio_defined_images": len(errors),
        "undefined_gt_denominator_images": sum(x["tumor_ratio"]["gt"] is None for x in per_image),
        "undefined_predicted_denominator_images": sum(x["tumor_ratio"]["predicted"] is None for x in per_image),
        "predicted_nontumor_at_GT_tumor_centers": sum(x in (2, 3) for x in predicted_all),
        "coordinates_or_cell_level_records_written": False,
    }
    expected = read_json(evidence / "results.json")
    for key in ["image_count", "metrics", "reference_tumor_classes_mean_f1", "per_image",
                "mean_per_image_absolute_error_percentage_points", "ratio_defined_images",
                "undefined_gt_denominator_images", "undefined_predicted_denominator_images",
                "predicted_nontumor_at_GT_tumor_centers"]:
        assert result[key] == expected[key], f"Reproduction differs: {key}"
    result["matches_published_aggregate_results"] = True
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(json.dumps({"matches_published_aggregate_results": True,
                      "images": len(per_image), "cells": metrics["cell_count"],
                      "accuracy": metrics["accuracy"],
                      "ratio_mae_pp": result["mean_per_image_absolute_error_percentage_points"]}))


if __name__ == "__main__":
    main()
