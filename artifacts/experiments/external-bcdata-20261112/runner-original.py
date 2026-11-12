"""Bounded BCData source audit and locked-model external check. Research only."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import struct
import sys
import time
import urllib.parse
import urllib.request
import zlib

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
sys.path[:0] = [str(ROOT / "python-deps"), str(REPO / "src")]
import h5py
import numpy as np
from PIL import Image
from pathology_edge.ihc_baseline import CLASSES, extract_features, predict_proba, classification_metrics, tumor_ratios


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(name):
    return json.loads((ROOT / name).read_text())


def write(name, content, exclusive=False):
    with (ROOT / name).open("x" if exclusive else "w") as stream:
        json.dump(content, stream, indent=2, allow_nan=False)
        stream.write("\n")


def source_names(protocol):
    names = []
    for name in protocol["selected_images"]:
        stem = Path(name).stem
        names.extend([name, f"BCData/annotations/test/positive/{stem}.h5", f"BCData/annotations/test/negative/{stem}.h5"])
    return names


def locked_inputs():
    protocol = read("bcdata-evaluation-protocol.json")
    for file_key, hash_key in [("model_path", "model_sha256"), ("feature_module_path", "feature_module_sha256")]:
        assert sha(REPO / protocol[file_key]) == protocol[hash_key], file_key
    assert sha(ROOT / "bcdata-archive-manifest.json") == protocol["archive_manifest_sha256"]
    assert sha(ROOT / "bcdata-central-directory.bin") == protocol["archive_central_directory_sha256"]
    all_entries = read("bcdata-archive-manifest.json")
    selected = sorted(x["name"] for x in all_entries if x["name"].startswith("BCData/images/test/") and x["name"].endswith(".png"))[:10]
    assert selected == protocol["selected_images"]
    return protocol, {x["name"]: x for x in all_entries}


def download():
    protocol, entries = locked_inputs()
    names = source_names(protocol)
    assert sum(entries[n]["compressed_bytes"] + 1025 for n in names) < 40_000_000
    page_url = "https://drive.usercontent.google.com/download?id=16W04QOR1E-G3ifc4061Be4eGpjRYDlkA&export=download"
    with urllib.request.urlopen(page_url, timeout=35) as response:
        html = response.read(200_000).decode()
    fields = dict(re.findall(r'<input[^>]+name="([^"]+)"[^>]+value="([^"]*)"', html))
    action = re.search(r'<form[^>]+action="([^"]+)"', html).group(1)
    url = action + "?" + urllib.parse.urlencode(fields)

    def fetch(name):
        entry = entries[name]
        dest = ROOT / "bcdata-selected" / name
        if dest.exists():
            data = dest.read_bytes()
            assert len(data) == entry["uncompressed_bytes"] and zlib.crc32(data) == entry["crc32"]
            return dict(entry, sha256=sha(dest), downloaded_range_bytes=0)
        low = entry["offset"]
        high = low + entry["compressed_bytes"] + 1024
        request = urllib.request.Request(url, headers={"Range": f"bytes={low}-{high}"})
        with urllib.request.urlopen(request, timeout=35) as response:
            assert response.status == 206, "Server must honor range; refuse full ZIP"
            assert response.headers["Content-Range"] == f"bytes {low}-{high}/{protocol['archive_bytes']}"
            raw = response.read(high - low + 2)
        assert len(raw) == high - low + 1
        header = struct.unpack_from("<4s5H3L2H", raw, 0)
        assert header[0] == b"PK\x03\x04" and header[3] == entry["method"] == 8
        name_length, extra_length = header[-2:]
        assert raw[30:30+name_length].decode() == name
        start = 30 + name_length + extra_length
        data = zlib.decompress(raw[start:start + entry["compressed_bytes"]], -15)
        assert len(data) == entry["uncompressed_bytes"] and zlib.crc32(data) == entry["crc32"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return dict(entry, sha256=sha(dest), downloaded_range_bytes=len(raw))

    with ThreadPoolExecutor(max_workers=4) as executor:
        manifest = list(executor.map(fetch, names))
    write("bcdata-selected-manifest.json", manifest)
    print(json.dumps({"files": len(manifest), "range_bytes": sum(x["downloaded_range_bytes"] for x in manifest)}))


def load_sample(image_name):
    image_path = ROOT / "bcdata-selected" / image_name
    with Image.open(image_path) as image:
        assert image.mode == "RGB" and image.size == (640, 640)
        rgb = np.asarray(image)
        image_metadata = dict(image.info)
    points, truth, metadata = [], [], []
    for label, index in [("positive", 0), ("negative", 1)]:
        filename = ROOT / "bcdata-selected/BCData/annotations/test" / label / f"{Path(image_name).stem}.h5"
        with h5py.File(filename) as handle:
            assert list(handle) == ["coordinates"]
            coords = handle["coordinates"][:]
            assert coords.ndim == 2 and coords.shape[1] == 2
            assert np.isfinite(coords).all() and (coords == np.floor(coords)).all()
            assert ((coords >= 0) & (coords < 640)).all()
            assert len(np.unique(coords, axis=0)) == len(coords), f"duplicate {filename}"
            metadata.append({"label": label, "shape": list(coords.shape), "dtype": str(coords.dtype), "file_attributes": dict(handle.attrs), "coordinate_attributes": dict(handle["coordinates"].attrs)})
            points.extend(coords.tolist())
            truth.extend([index] * len(coords))
    points = np.asarray(points, dtype=np.int64).reshape(-1, 2)
    truth = np.asarray(truth, dtype=np.int64)
    assert len(points) and len(np.unique(points, axis=0)) == len(points), "cross-class duplicate/conflicting points"
    return rgb, points, truth, {"image": image_name, "image_metadata": image_metadata, "point_sources": metadata, "positive": int((truth == 0).sum()), "negative": int((truth == 1).sum()), "pixel_sha256": hashlib.sha256(rgb.tobytes()).hexdigest()}


def audit():
    protocol, _ = locked_inputs()
    manifest = read("bcdata-selected-manifest.json")
    for entry in manifest:
        assert sha(ROOT / "bcdata-selected" / entry["name"]) == entry["sha256"]
    observations = [load_sample(name)[3] for name in protocol["selected_images"]]
    assert len(set(x["pixel_sha256"] for x in observations)) == 10, "duplicate selected image pixels"
    previous_source_text = (REPO / "artifacts/ihc/source-manifest.json").read_text()
    overlapping = [entry["name"] for entry in manifest if entry["name"].endswith(".png") and entry["sha256"] in previous_source_text]
    assert not overlapping
    result = {"protocol_sha256": sha(ROOT / "bcdata-evaluation-protocol.json"), "selected_manifest_sha256": sha(ROOT / "bcdata-selected-manifest.json"), "images": observations, "total_points": sum(x["positive"]+x["negative"] for x in observations), "all_coordinates_valid_unique_and_nonconflicting": True, "all_selected_pixels_distinct": True, "exact_file_hash_matches_to_Patherea_source_manifest": overlapping, "duplicate_check_limit": "No identical whole-image file hashes; subimages, near duplicates and patient identities are not established by this check.", "physical_resolution": "No per-image MPP metadata. Native pixels preserved; physical-scale equivalence not established.", "patient_mapping": "Absent from source ZIP."}
    write("bcdata-pre-inference-audit.json", result)
    print(json.dumps(result, indent=2))


def independent_metrics(truth, pred):
    matrix = [[0] * 4 for _ in range(4)]
    for t, p in zip(truth, pred):
        matrix[int(t)][int(p)] += 1
    per_class = []
    for k, name in enumerate(CLASSES):
        tp, support, calls = matrix[k][k], sum(matrix[k]), sum(row[k] for row in matrix)
        per_class.append({"id": k, "name": name, "precision": tp/calls if calls else 0.0, "recall": tp/support if support else 0.0, "f1": 2*tp/(support+calls) if support+calls else 0.0, "support": support})
    return {"accuracy": sum(matrix[i][i] for i in range(4))/len(truth), "macro_f1": sum(x["f1"] for x in per_class)/4, "per_class": per_class, "confusion_matrix": matrix, "cell_count": len(truth)}


def evaluate():
    protocol, _ = locked_inputs()
    audit_data = read("bcdata-pre-inference-audit.json")
    assert audit_data["protocol_sha256"] == sha(ROOT / "bcdata-evaluation-protocol.json")
    assert audit_data["selected_manifest_sha256"] == sha(ROOT / "bcdata-selected-manifest.json")
    for entry in read("bcdata-selected-manifest.json"):
        assert sha(ROOT / "bcdata-selected" / entry["name"]) == entry["sha256"]
    model = json.loads((REPO / protocol["model_path"]).read_text())
    assert model["classes"] == list(CLASSES) and model["feature_radii_pixels"] == [3, 7]
    lock = {"started_utc": datetime.now(timezone.utc).isoformat(), "protocol_sha256": sha(ROOT / "bcdata-evaluation-protocol.json"), "model_sha256": protocol["model_sha256"], "feature_module_sha256": protocol["feature_module_sha256"], "selected_manifest_sha256": sha(ROOT / "bcdata-selected-manifest.json"), "pre_inference_audit_sha256": sha(ROOT / "bcdata-pre-inference-audit.json"), "runner_sha256": sha(Path(__file__)), "training_or_tuning": False}
    write("bcdata-inference-lock.json", lock, exclusive=True)
    start = time.perf_counter()
    rows, per_image = [], []
    for image_name in protocol["selected_images"]:
        rgb, points, truth, metadata = load_sample(image_name)
        features = extract_features(rgb, points)
        proba = predict_proba(features, model)
        assert np.isfinite(proba).all() and np.allclose(proba.sum(1), 1)
        predicted = proba.argmax(axis=1)
        metrics = classification_metrics(truth, predicted)
        assert metrics == independent_metrics(truth.tolist(), predicted.tolist())
        ratios = tumor_ratios(truth, predicted)
        gt_n = sum(int(x) in (0, 1) for x in truth)
        pred_n = sum(int(x) in (0, 1) for x in predicted)
        gt_ratio = sum(int(x) == 0 for x in truth)/gt_n if gt_n else None
        pred_ratio = sum(int(x) == 0 for x in predicted)/pred_n if pred_n else None
        assert (ratios["gt"], ratios["predicted"]) == (gt_ratio, pred_ratio)
        for point, target, prediction, scores in zip(points, truth, predicted, proba):
            rows.append({"image": image_name, "x": int(point[0]), "y": int(point[1]), "truth": int(target), "predicted": int(prediction), "probabilities": scores.tolist()})
        per_image.append({"image": image_name, "metrics": metrics, "tumor_ratio": ratios})
    write("bcdata-cell-predictions.json", rows, exclusive=True)
    # Re-read predictions to verify reporting from persisted observations.
    saved = read("bcdata-cell-predictions.json")
    truth = np.array([x["truth"] for x in saved]); predicted = np.array([x["predicted"] for x in saved])
    metrics = classification_metrics(truth, predicted)
    assert metrics == independent_metrics(truth.tolist(), predicted.tolist())
    errors = [x["tumor_ratio"]["absolute_error_percentage_points"] for x in per_image if x["tumor_ratio"]["absolute_error_percentage_points"] is not None]
    report = {"schema": "bcdata-bounded-external-results-v1", "scope": protocol["purpose"], "frozen_model_sha256": protocol["model_sha256"], "inference_lock_sha256": sha(ROOT / "bcdata-inference-lock.json"), "prediction_sha256": sha(ROOT / "bcdata-cell-predictions.json"), "selected_images": protocol["selected_images"], "image_count": 10, "patient_count": None, "metrics": metrics, "reference_tumor_classes_mean_f1": sum(x["f1"] for x in metrics["per_class"][:2])/2, "gt_nontumor_support": 0, "four_class_macro_f1_caveat": "Two reference classes have no support; this metric uses the unchanged zero_division=0 convention and is not comparable to the complete four-class Patherea test.", "per_image": per_image, "mean_per_image_absolute_error_percentage_points": sum(errors)/len(errors) if errors else None, "ratio_defined_images": len(errors), "undefined_gt_denominator_images": sum(x["tumor_ratio"]["gt"] is None for x in per_image), "undefined_predicted_denominator_images": sum(x["tumor_ratio"]["predicted"] is None for x in per_image), "predicted_nontumor_at_GT_tumor_centers": int(np.isin(predicted,[2,3]).sum()), "independent_count_metrics_verified": True, "native_pixel_resolution_caveat": protocol["physical_scale"], "wall_seconds_including_data_read_feature_extraction_and_verification": time.perf_counter()-start, "software": {"python": sys.version.split()[0], "numpy": np.__version__, "h5py": h5py.__version__}, "limitations": ["Ten lexicographically selected image ROIs; not the entire official test set.", "No patient or slide mapping, so no patient-independent cohort assertion or patient-level confidence intervals.", "Only provided tumor-cell centers are evaluated; no detection, non-tumor reference, tumor-area selection, whole-slide scoring, or clinical endpoint.", "Native pixels; per-image microns-per-pixel unverified; no physical-scale matching.", "No new pathologist consensus or clinical adjudication."]}
    write("bcdata-results.json", report, exclusive=True)
    print(json.dumps({k: report[k] for k in ["image_count","metrics","mean_per_image_absolute_error_percentage_points","ratio_defined_images","undefined_predicted_denominator_images","predicted_nontumor_at_GT_tumor_centers","wall_seconds_including_data_read_feature_extraction_and_verification"]}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["download", "audit", "evaluate"])
    args = parser.parse_args()
    {"download": download, "audit": audit, "evaluate": evaluate}[args.stage]()
