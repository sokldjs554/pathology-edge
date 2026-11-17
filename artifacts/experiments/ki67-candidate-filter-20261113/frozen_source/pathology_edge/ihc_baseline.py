"""CPU color baseline at expert-provided Ki67 cell centers.

This is conditional four-class cell classification, not detection, segmentation,
whole-slide scoring, or a clinical assay. No Patherea model code is reused.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import re
import resource
import time
import warnings

import numpy as np
from PIL import Image
from scipy.ndimage import label


CLASSES = ("positive_tumor_cell", "negative_tumor_cell", "others_positive", "others_negative")
LABELS_KO = ("Ki67 양성 종양 세포", "Ki67 음성 종양 세포", "Ki67 양성 비종양 세포", "Ki67 음성 비종양 세포")
MASK_NAMES = (*CLASSES, "normal_cell")
CHANNELS = ("red", "green", "blue", "hue_sin", "hue_cos", "saturation", "value", "od_red", "od_green", "od_blue")
RADII = (3, 7)
ZIP_SHA256 = "1194dbfb145ca3aee1a27fcff9d92799d73d34b5da972118424a7b67047034e7"
DATA_REVISION = "eb8a6c38cb1df3381b22385ed7b6175091c87ea5"
DATA_URL = "https://huggingface.co/datasets/ds2268/patherea"


def case_id(filename: str) -> str:
    match = re.match(r"^(case_\d{4})_region_\d+_patch_\d+_.*\.png$", filename)
    if match is None or Path(filename).name != filename:
        raise ValueError(f"Invalid case filename: {filename}")
    return match.group(1)


def make_split(author_train, author_test, seed=20261108, validation_cases=4):
    """Hold author fold 1 test fixed; split author train by whole case IDs."""
    train, test = set(author_train), set(author_test)
    if len(train) != len(author_train) or len(test) != len(author_test):
        raise ValueError("Duplicate image in author split")
    train_cases = sorted({case_id(name) for name in train})
    test_cases = sorted({case_id(name) for name in test})
    if train & test or set(train_cases) & set(test_cases):
        raise ValueError("Author train/test case or image overlap")
    if not 0 < validation_cases < len(train_cases):
        raise ValueError("Validation case count must leave training cases")
    shuffled = list(train_cases)
    random.Random(seed).shuffle(shuffled)
    validation = set(shuffled[:validation_cases])
    assignment = {name: "validation" if case_id(name) in validation else "train" for name in sorted(train)}
    assignment.update({name: "test" for name in sorted(test)})
    info = {}
    for subset in ("train", "validation", "test"):
        names = [name for name, split in assignment.items() if split == subset]
        info[subset] = {"case_ids": sorted({case_id(name) for name in names}), "image_count": len(names)}
    return assignment, info


def read_points(masks):
    """Require isolated one-pixel centers, never convert area masks to cells."""
    if set(masks) != set(MASK_NAMES):
        raise ValueError("Missing or unexpected point-mask classes")
    shape = masks["normal_cell"].shape
    if len(shape) != 2 or np.any(masks["normal_cell"]):
        raise ValueError("Expected empty two-dimensional normal_cell mask")
    occupied = np.zeros(shape, dtype=bool)
    points, classes = [], []
    for index, name in enumerate(CLASSES):
        mask = np.asarray(masks[name])
        if mask.shape != shape or not np.isin(mask, [0, 255]).all():
            raise ValueError("Point masks must have matching shapes and values 0/255")
        foreground = mask == 255
        if np.any(occupied & foreground):
            raise ValueError("Conflicting classes at the same point")
        components, _ = label(foreground, structure=np.ones((3, 3), dtype=int))
        if np.any(np.bincount(components.ravel())[1:] != 1):
            raise ValueError("Mask contains connected areas, not isolated one-pixel centers")
        occupied |= foreground
        yy, xx = np.nonzero(foreground)
        points.extend(zip(xx.tolist(), yy.tolist()))
        classes.extend([index] * len(xx))
    return np.asarray(points, dtype=np.int64).reshape(-1, 2), np.asarray(classes, dtype=np.int64)


def feature_names():
    return [f"disk{radius}_{stat}_{channel}" for radius in RADII for stat in ("mean", "std") for channel in CHANNELS]


def extract_features(rgb, centers):
    """40 fixed local color statistics; no label-dependent feature extraction."""
    rgb = np.asarray(rgb)
    if rgb.ndim != 3 or rgb.shape[2] != 3 or rgb.dtype != np.uint8:
        raise ValueError("Expected uint8 RGB image")
    normalized = rgb.astype(np.float64) / 255.0
    high, low = normalized.max(axis=2), normalized.min(axis=2)
    delta = high - low
    hue = np.zeros_like(high)
    nonzero = delta > 0
    for channel, offset in ((0, 0), (1, 2), (2, 4)):
        selected = nonzero & (normalized.argmax(axis=2) == channel)
        first, second = ((1, 2), (2, 0), (0, 1))[channel]
        hue[selected] = ((normalized[..., first][selected] - normalized[..., second][selected]) / delta[selected] + offset) / 6.0
    hue %= 1.0
    saturation = np.divide(delta, high, out=np.zeros_like(high), where=high > 0)
    optical_density = -np.log((rgb.astype(np.float64) + 1.0) / 256.0)
    channels = np.dstack((normalized, np.sin(2 * np.pi * hue), np.cos(2 * np.pi * hue), saturation, high, optical_density))
    height, width = rgb.shape[:2]
    output = np.empty((len(centers), len(feature_names())), dtype=np.float64)
    for row, (x, y) in enumerate(centers):
        if not (0 <= x < width and 0 <= y < height):
            raise ValueError("Cell center outside image")
        values = []
        for radius in RADII:
            x0, x1 = max(0, x - radius), min(width, x + radius + 1)
            y0, y1 = max(0, y - radius), min(height, y + radius + 1)
            yy, xx = np.mgrid[y0:y1, x0:x1]
            pixels = channels[y0:y1, x0:x1][(xx - x) ** 2 + (yy - y) ** 2 <= radius ** 2]
            values.extend(pixels.mean(axis=0))
            values.extend(pixels.std(axis=0))
        output[row] = values
    return output


def classification_metrics(truth, predicted):
    truth, predicted = np.asarray(truth), np.asarray(predicted)
    if truth.shape != predicted.shape or truth.size == 0 or not np.isin(truth, range(4)).all() or not np.isin(predicted, range(4)).all():
        raise ValueError("Expected nonempty matched four-class predictions")
    matrix = np.bincount(4 * truth + predicted, minlength=16).reshape(4, 4)
    per_class = []
    for index, name in enumerate(CLASSES):
        tp, support, called = int(matrix[index, index]), int(matrix[index].sum()), int(matrix[:, index].sum())
        precision = tp / called if called else 0.0
        recall = tp / support if support else 0.0
        f1 = 2 * tp / (support + called) if support + called else 0.0
        per_class.append({"id": index, "name": name, "precision": precision, "recall": recall, "f1": f1, "support": support})
    return {"accuracy": float(np.trace(matrix) / matrix.sum()), "macro_f1": float(np.mean([item["f1"] for item in per_class])),
            "per_class": per_class, "confusion_matrix": matrix.tolist(), "cell_count": int(matrix.sum())}


def predict_proba(features, model):
    scaled = (np.asarray(features) - np.asarray(model["scaler"]["mean"])) / np.asarray(model["scaler"]["scale"])
    logits = scaled @ np.asarray(model["coefficients"]).T + np.asarray(model["intercepts"])
    logits -= logits.max(axis=1, keepdims=True)
    exponentials = np.exp(logits)
    return exponentials / exponentials.sum(axis=1, keepdims=True)


def select_model(train_x, train_y, validation_x, validation_y, candidates=(0.1, 1.0, 10.0)):
    from sklearn.exceptions import ConvergenceWarning
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from threadpoolctl import threadpool_limits

    if set(np.unique(train_y)) != set(range(4)):
        raise ValueError("All four real classes must be present in training")
    scaler = StandardScaler().fit(train_x)
    scaled_train, scaled_validation = scaler.transform(train_x), scaler.transform(validation_x)
    trials, best = [], None
    with threadpool_limits(limits=1), warnings.catch_warnings():
        warnings.simplefilter("error", ConvergenceWarning)
        for strength in sorted(candidates):
            estimator = LogisticRegression(C=strength, class_weight="balanced", max_iter=2000, solver="lbfgs", tol=1e-6)
            estimator.fit(scaled_train, train_y)
            probability = estimator.predict_proba(scaled_validation)
            metrics = classification_metrics(validation_y, probability.argmax(axis=1))
            trials.append({"C": float(strength), "validation_macro_f1": metrics["macro_f1"], "iterations": int(estimator.n_iter_.max())})
            if best is None or metrics["macro_f1"] > best[0]:
                model = {"schema_version": "pathology-edge.ihc-model.v1", "type": "multinomial_logistic_regression",
                         "classes": list(CLASSES), "class_ids": estimator.classes_.tolist(), "C": float(strength),
                         "class_weight": "balanced", "scaler": {"mean": scaler.mean_.tolist(), "scale": scaler.scale_.tolist()},
                         "coefficients": estimator.coef_.tolist(), "intercepts": estimator.intercept_.tolist()}
                best = (metrics["macro_f1"], model, probability)
    selected_model = best[1]
    error = float(np.max(np.abs(predict_proba(validation_x, selected_model) - best[2])))
    if error > 1e-12:
        raise ValueError("JSON model does not reproduce fitted model probabilities")
    return selected_model, {"C_candidates": list(candidates), "selected_C": selected_model["C"], "selection_metric": "validation_macro_f1",
                            "tie_rule": "smaller_C", "trials": trials, "export_probability_max_abs_error": error,
                            "scaler_fit": "training_cells_only", "refit_with_validation": False, "probability_calibration": "none"}


def tumor_ratios(truth, predicted):
    truth, predicted = np.asarray(truth), np.asarray(predicted)
    gt_denominator, pred_denominator = int(np.isin(truth, [0, 1]).sum()), int(np.isin(predicted, [0, 1]).sum())
    gt = float((truth == 0).sum() / gt_denominator) if gt_denominator else None
    pred = float((predicted == 0).sum() / pred_denominator) if pred_denominator else None
    return {"gt": gt, "predicted": pred, "gt_tumor_cell_count": gt_denominator, "predicted_tumor_cell_count": pred_denominator,
            "absolute_error_percentage_points": None if gt is None or pred is None else abs(gt - pred) * 100,
            "scope": "annotated_cells_at_GT_centers_only; not a whole-slide or clinical Ki67 index"}


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def _export_examples(data_dir, public_dir, cells, truth, predicted, probabilities):
    examples = []
    directory = public_dir / "examples"
    directory.mkdir(parents=True, exist_ok=True)
    for kind, equality in (("correct", True), ("incorrect", False)):
        used_images, used_cases, chosen = set(), set(), []
        queues = {index: [i for i, cell in enumerate(cells) if truth[i] == index and bool(predicted[i] == truth[i]) == equality] for index in range(4)}
        for _ in range(8):
            progress = False
            for class_index in range(4):
                available = [i for i in queues[class_index] if cells[i]["image"] not in used_images]
                new_cases = [i for i in available if cells[i]["case_id"] not in used_cases]
                available = new_cases or available
                if available and len(chosen) < 8:
                    index = available[0]
                    chosen.append(index)
                    used_images.add(cells[index]["image"])
                    used_cases.add(cells[index]["case_id"])
                    progress = True
            if len(chosen) == 8 or not progress:
                break
        for number, index in enumerate(chosen):
            cell = cells[index]
            example_id = f"{kind}-{number + 1:02d}"
            source = data_dir / "images" / cell["image"]
            rgb = Image.open(source).convert("RGB")
            x, y = cell["x"], cell["y"]
            left, top = max(0, min(x - 24, rgb.width - 48)), max(0, min(y - 24, rgb.height - 48))
            bbox = (left, top, left + 48, top + 48)
            source_name, crop_name = f"{example_id}-source.png", f"{example_id}-crop.png"
            # Save actual pixels; center overlays are represented as coordinates.
            rgb.save(directory / source_name)
            rgb.crop(bbox).save(directory / crop_name)
            examples.append({"id": example_id, "kind": kind, "case_id": cell["case_id"], "image_name": cell["image"],
                             "center": [x, y], "gt_class": int(truth[index]), "pred_class": int(predicted[index]),
                             "probabilities": probabilities[index].tolist(), "confidence": float(probabilities[index].max()),
                             "source_image": f"ihc/examples/{source_name}", "crop_image": f"ihc/examples/{crop_name}",
                             "crop_bbox": list(bbox), "point_in_crop": [x - left, y - top], "source_size": [rgb.width, rgb.height],
                             "source_sha256": _sha256(source), "source_pixel_sha256": hashlib.sha256(np.asarray(rgb).tobytes()).hexdigest()})
    return examples


def run(data_dir, archive, artifact_dir, public_dir, seed=20261108):
    """One frozen held-out evaluation with file-level provenance and JSON weights."""
    import sklearn
    import scipy
    import PIL

    start = time.perf_counter()
    data_dir, archive, artifact_dir, public_dir = map(Path, (data_dir, archive, artifact_dir, public_dir))
    lock_path = artifact_dir / "evaluation-lock.json"
    if lock_path.exists():
        raise ValueError("This artifact directory already contains a held-out evaluation; use a new run directory")
    if _sha256(archive) != ZIP_SHA256:
        raise ValueError("Archive hash differs from the inspected Patherea Breast-P1 v1.1 release")
    author_lists = {}
    author_hashes = {}
    for split in ("train", "test"):
        path = data_dir / "folds" / f"fold_1_{split}.txt"
        author_lists[split] = path.read_text().splitlines()
        author_hashes[split] = _sha256(path)
    assignment, split_info = make_split(author_lists["train"], author_lists["test"], seed=seed)
    image_names = sorted(path.name for path in (data_dir / "images").glob("*.png"))
    if set(image_names) != set(assignment) or len(image_names) != 1330:
        raise ValueError("Author folds do not exactly cover the 1,330 inspected images")
    if [len(split_info[s]["case_ids"]) for s in ("train", "validation", "test")] != [15, 4, 10]:
        raise ValueError("Unexpected case split")
    feature_parts, labels_parts, cells, source_manifest = [], [], [], []
    byte_hashes, pixel_hashes = set(), set()
    extraction_start = time.perf_counter()
    for filename in image_names:
        image_path = data_dir / "images" / filename
        rgb = np.asarray(Image.open(image_path).convert("RGB"))
        if rgb.shape != (224, 224, 3):
            raise ValueError("Unexpected patch resolution")
        image_hash = _sha256(image_path)
        pixel_hash = hashlib.sha256(rgb.tobytes()).hexdigest()
        if image_hash in byte_hashes or pixel_hash in pixel_hashes:
            raise ValueError("Duplicate source image")
        byte_hashes.add(image_hash)
        pixel_hashes.add(pixel_hash)
        masks, mask_hashes = {}, {}
        for name in MASK_NAMES:
            path = data_dir / "labels" / f"{image_path.stem}_{name}.png"
            masks[name] = np.asarray(Image.open(path))
            mask_hashes[name] = _sha256(path)
            if masks[name].shape != (224, 224):
                raise ValueError("Unexpected point mask resolution")
        centers, targets = read_points(masks)
        feature_parts.append(extract_features(rgb, centers))
        labels_parts.append(targets)
        for (x, y), target in zip(centers.tolist(), targets.tolist()):
            cells.append({"image": filename, "case_id": case_id(filename), "x": x, "y": y, "class_id": target, "split": assignment[filename]})
        source_manifest.append({"image": filename, "case_id": case_id(filename), "split": assignment[filename], "image_sha256": image_hash,
                                "pixel_sha256": pixel_hash, "mask_sha256": mask_hashes,
                                "class_counts": {name: int((targets == i).sum()) for i, name in enumerate(CLASSES)}})
    features, targets = np.concatenate(feature_parts), np.concatenate(labels_parts)
    if np.bincount(targets, minlength=4).tolist() != [5556, 9530, 465, 4421]:
        raise ValueError("Actual annotations differ from inspected release counts")
    extraction_seconds = time.perf_counter() - extraction_start
    indices = {split: np.array([i for i, cell in enumerate(cells) if cell["split"] == split]) for split in ("train", "validation", "test")}
    for split, selected in indices.items():
        split_info[split]["cell_count"] = int(len(selected))
        split_info[split]["class_counts"] = {name: int((targets[selected] == i).sum()) for i, name in enumerate(CLASSES)}
    _write_json(artifact_dir / "source-manifest.json", source_manifest)
    _write_json(artifact_dir / "split.json", {"seed": seed, "author_test_fold": 1, "author_fold_sha256": author_hashes, "subsets": split_info,
                                             "assignment": assignment, "image_overlap": 0, "case_overlap": 0, "duplicate_pixel_images": 0})
    training_start = time.perf_counter()
    train, validation, test = (indices[key] for key in ("train", "validation", "test"))
    model, selection = select_model(features[train], targets[train], features[validation], targets[validation])
    model["feature_names"] = feature_names()
    model["feature_radii_pixels"] = list(RADII)
    training_seconds = time.perf_counter() - training_start
    _write_json(artifact_dir / "model.json", model)
    _write_json(artifact_dir / "selection.json", selection)
    model_hash = _sha256(artifact_dir / "model.json")
    # The test data never enter model/scaler fitting or the C-selection function.
    _write_json(lock_path, {"locked_utc": datetime.now(timezone.utc).isoformat(), "model_sha256": model_hash,
                           "selected_C": model["C"], "test_evaluations": 1, "test_tuning": False})
    inference_start = time.perf_counter()
    probability = predict_proba(features[test], model)
    test_inference_seconds = time.perf_counter() - inference_start
    predicted = probability.argmax(axis=1)
    validation_predicted = predict_proba(features[validation], model).argmax(axis=1)
    test_cells = [cells[index] for index in test]
    case_results = []
    for case in split_info["test"]["case_ids"]:
        selected = np.array([i for i, cell in enumerate(test_cells) if cell["case_id"] == case])
        case_results.append({"case_id": case, "cell_count": int(len(selected)),
                             "metrics": classification_metrics(targets[test][selected], predicted[selected]),
                             "annotated_cell_ki67_ratio": tumor_ratios(targets[test][selected], predicted[selected])})
    examples = _export_examples(data_dir, public_dir, test_cells, targets[test], predicted, probability)
    ratio_errors = [case["annotated_cell_ki67_ratio"]["absolute_error_percentage_points"] for case in case_results]
    defined_errors = [value for value in ratio_errors if value is not None]
    attribution = {"authors": "Dejan Štepec, Maja Jerše, Snežana Đokić, Jera Jeruc, Nina Zidar, Danijel Skočaj",
                   "dataset": "Patherea Breast-P1 224 v1.1", "source": DATA_URL, "paper": "https://doi.org/10.1016/j.media.2025.103868",
                   "license": "CC BY-NC 4.0", "license_url": "https://creativecommons.org/licenses/by-nc/4.0/",
                   "changes": "Original 224px RGB patches re-encoded losslessly; 48px local crops and JSON coordinates exported. No generated or recolored tissue.",
                   "use": "Independent noncommercial research/education; no AIVIS affiliation"}
    result = {
        "schema_version": "pathology-edge.ihc.v1", "task": "gt_center_cell_classification", "created_utc": datetime.now(timezone.utc).isoformat(),
        "scope": {"stain": "Ki-67 IHC", "organ": "breast", "provided_centers": True, "detection_evaluated": False,
                  "segmentation_evaluated": False, "clinical_assay": False, "title_ko": "정답 중심점 조건의 IHC 세포 분류"},
        "classes": [{"id": i, "name": name, "label_ko": LABELS_KO[i]} for i, name in enumerate(CLASSES)],
        "dataset": {"id": "patherea-breast-p1-v1.1", "url": DATA_URL, "revision": DATA_REVISION, "license": "CC BY-NC 4.0",
                    "zip_sha256": ZIP_SHA256, "zip_bytes": archive.stat().st_size, "image_count": len(image_names), "case_count": 29,
                    "cell_count": len(cells), "class_counts": dict(Counter(CLASSES[int(target)] for target in targets)), "normal_cell_count": 0,
                    "point_mask_semantics": "isolated 255-valued single pixels in 0/255 arrays; all connected components size 1",
                    "statistics_discrepancy": {"global_stats_txt_and_paper": 36673, "actual_downloaded_point_masks": 19972,
                                               "fold_stats_match_actual": True, "cause": "unknown"}},
        "protocol": {"seed": seed, "author_test_fold": 1, "split": split_info, **selection, "test_evaluations": 1,
                     "features": feature_names(), "decision_rule": "argmax of four softmax scores; no tuned class threshold",
                     "calibration": "not calibrated; displayed probabilities are model scores", "case_separation_check": "filename case IDs disjoint",
                     "patient_mapping_limit": "Author describes patient-level folds; no independent clinical patient list or slide-to-patient registry supplied"},
        "metrics": {"validation": classification_metrics(targets[validation], validation_predicted), "test": classification_metrics(targets[test], predicted)},
        "cases": case_results, "annotated_cell_ratio_summary": {"case_mae_percentage_points": float(np.mean(defined_errors)) if defined_errors else None,
                                                                "defined_cases": len(defined_errors), "excluded_zero_denominator_cases": len(ratio_errors) - len(defined_errors),
                                                                "scope": "GT-center conditional classification; no missed/false detections evaluated"},
        "examples": examples, "example_selection": "8 correct and 8 incorrect when available; round robin true class, prioritize unused case then first sorted distinct image; illustrative, not representative",
        "model": {"path": "ihc/model.json", "sha256": model_hash, "pretrained_weights": False, "type": "40 fixed local color features + multinomial logistic regression"},
        "runtime": {"device": "CPU", "paid_services": False, "fit_blas_threads": 1, "feature_extraction_seconds": extraction_seconds,
                    "candidate_training_seconds": training_seconds, "test_model_inference_seconds": test_inference_seconds,
                    "total_wall_seconds": time.perf_counter() - start, "peak_process_rss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
                    "platform": platform.platform(), "python": platform.python_version(), "logical_cpus_visible": os.cpu_count(),
                    "versions": {"numpy": np.__version__, "scipy": scipy.__version__, "Pillow": PIL.__version__, "scikit-learn": sklearn.__version__},
                    "timing_scope": "One local run. Feature time includes image/mask reads, validation and hashes for all splits; test time excludes extraction. RSS includes process imports."},
        "limitations": ["Expert-provided centers eliminate localization errors; this is not detection or an end-to-end Ki67 assay.",
                        "Point labels provide no nuclear boundary ground truth; Dice/AJI are not reported.",
                        "Single institution breast subset and 10 held-out case IDs; no external validation.",
                        "Author patient-level folds are checked by case IDs, without an independent patient registry.",
                        "Actual v1.1 masks contain 19,972 cells; global metadata/paper report 36,673 for an unexplained reason.",
                        "Probabilities are uncalibrated model scores; selected examples do not estimate prevalence or accuracy."],
        "attribution": attribution,
    }
    _write_json(artifact_dir / "test-predictions.json", [{**cell, "predicted_class": int(predicted[i]), "probabilities": probability[i].tolist()} for i, cell in enumerate(test_cells)])
    _write_json(artifact_dir / "results.json", result)
    _write_json(public_dir / "results.json", result)
    _write_json(public_dir / "model.json", model)
    _write_json(public_dir / "attribution.json", attribution)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, default=Path("artifacts/ihc"))
    parser.add_argument("--public", type=Path, default=Path("dist/ihc"))
    args = parser.parse_args()
    result = run(args.data_dir, args.archive, args.artifacts, args.public)
    print(json.dumps({"test": result["metrics"]["test"], "selection": result["protocol"]["trials"], "runtime": result["runtime"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
