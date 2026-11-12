"""Private replay of one BCData case with the existing frozen classifier.

Uses independently acquired PNG/HDF5 files, never trains, and produces a local
self-contained SVG. This provided review tool is not user-authored model code.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import html
import importlib.util
import json
import math
from pathlib import Path
import platform
import urllib.request

SOURCE_COMMIT = "f2713b212828b87bf42da03708de931fb4431d40"
PREFIX = "artifacts/experiments/bcdata-full-test-20261112/"
SOURCES = {
    PREFIX + "input-manifest.json": "fe4ae2ab24b1c15cead74859781bd366a158912aef42162de26f613c1bfd6f9c",
    PREFIX + "results.json": "9fc4282208ff2ed4d172c682e1f6e54496bac23ddfdd13800f312a338782c754",
    PREFIX + "canonicalize.py": "7957588816914108ccaf6e0f341ec8db6f998e78d393fd6dd43812fa6a8db3d9",
    "src/pathology_edge/ihc_baseline.py": "1fe59c945939bfbad54a7236cbad535d2f20dc792f29d9687239a4bc3b373dbe",
    "artifacts/ihc/model.json": "a0d75efdada6a5a2a077e3144ffc7685430a5130de769d69ccc155d511b48a3a",
}
COLORS = ("#ffe600", "#00e5ff", "#ff43dd", "#5dff54")
LABELS = ("Tumor +", "Tumor -", "Other +", "Other -")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def checked_input(root, entry):
    path = root / entry["name"]
    data = path.read_bytes()
    require(len(data) == entry["uncompressed_bytes"] and sha(data) == entry["sha256"],
            "Original input size/SHA mismatch: " + entry["name"])
    return path, data


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def comparison_svg(image_bytes, points, truth, predicted, summary):
    """Scientific display of original pixels and recorded integer xy centers."""
    ratio = summary["tumor_ratio"]
    uri = "data:image/png;base64," + base64.b64encode(image_bytes).decode()
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="2000" height="900" viewBox="0 0 2000 900">',
             '<rect width="2000" height="900" fill="#17232d"/>',
             '<g font-family="sans-serif" fill="#edf5fa">',
             f'<text x="24" y="32" font-size="24">BCData {summary["image_id"]} | original / supplied GT / frozen prediction</text>',
             '<text x="24" y="61" font-size="18">Given tumor centers; classification only. Native 640 x 640 input; no training or tuning.</text>',
             '<text x="24" y="88" font-size="18">PRIVATE research view. These selected extrema are not representative of the full test set.</text>']
    titles = ("1. Original pixels", "2. Supplied GT centers", "3. Frozen four-class prediction")
    for column, (title, values) in enumerate(zip(titles, (None, truth, predicted))):
        offset = 24 + 656 * column
        parts.append(f'<text x="{offset}" y="125" font-size="21">{title}</text>')
        parts.append(f'<g transform="translate({offset},140)" data-panel="{column}">')
        parts.append(f'<image width="640" height="640" href="{uri}"/>')
        if values is not None:
            for index, (point, value) in enumerate(zip(points, values)):
                x, y, label = int(point[0]), int(point[1]), int(value)
                tooltip = html.escape(f"#{index} xy=({x},{y}) {LABELS[label]}")
                parts.append(f'<circle cx="{x}" cy="{y}" r="4" fill="none" stroke="{COLORS[label]}" stroke-width="2"><title>{tooltip}</title></circle>')
        parts.append('</g>')
    for index, (color, label) in enumerate(zip(COLORS, LABELS)):
        x = 24 + 240 * index
        parts.append(f'<circle cx="{x+7}" cy="810" r="6" fill="none" stroke="{color}" stroke-width="3"/>')
        parts.append(f'<text x="{x+22}" y="816" font-size="20">{label}</text>')
    gt = "undefined" if ratio["gt"] is None else f'{ratio["gt"]*100:.4f}%'
    pred = "undefined" if ratio["predicted"] is None else f'{ratio["predicted"]*100:.4f}%'
    error = "undefined" if ratio["absolute_error_percentage_points"] is None else f'{ratio["absolute_error_percentage_points"]:.5f} pp'
    parts.extend([f'<text x="24" y="849" font-size="20">Tumor positive ratio: GT {gt} / prediction {pred} | absolute error {error}</text>',
                  f'<text x="24" y="880" font-size="20">Cell accuracy {summary["accuracy"]*100:.4f}% | tumor denominator: GT {ratio["gt_tumor_cell_count"]} / prediction {ratio["predicted_tumor_cell_count"]}</text>',
                  '</g></svg>'])
    return "\n".join(parts)


def run(data_dir, output_dir, image_id, source_root=None):
    # Imports precede output creation so missing dependencies do not leave a partial run.
    import h5py
    import numpy as np
    import PIL
    import scipy
    from PIL import Image

    data_dir, output_dir = data_dir.resolve(), output_dir.resolve()
    require("work" in output_dir.parts, "Output must remain in a private work directory")
    require(data_dir.is_dir(), "Data directory does not exist: " + str(data_dir))
    output_dir.mkdir(parents=True, exist_ok=False)
    source_dir = output_dir / "source"
    source_dir.mkdir()
    paths = {}
    for relative, expected_sha in SOURCES.items():
        if source_root is None:
            url = "https://raw.githubusercontent.com/sokldjs554/pathology-edge/" + SOURCE_COMMIT + "/" + relative
            with urllib.request.urlopen(url, timeout=45) as response:
                payload = response.read(2_000_001)
        else:
            payload = (source_root / relative).read_bytes()
        require(sha(payload) == expected_sha, "Frozen source SHA mismatch: " + relative)
        local = source_dir / Path(relative).name
        local.write_bytes(payload)
        paths[relative] = local
    manifest = {row["name"]: row for row in read_json(paths[PREFIX + "input-manifest.json"])}
    name = f"BCData/images/test/{image_id}.png"
    require(name in manifest, "Image is not in the official test manifest")
    image_path, image_bytes = checked_input(data_dir, manifest[name])
    arrays, input_hashes = [], {name: sha(image_bytes)}
    for label in ("positive", "negative"):
        h5_name = f"BCData/annotations/test/{label}/{image_id}.h5"
        h5_path, h5_bytes = checked_input(data_dir, manifest[h5_name])
        input_hashes[h5_name] = sha(h5_bytes)
        with h5py.File(h5_path, "r") as handle:
            require(list(handle) == ["coordinates"], "Unexpected annotation structure")
            arrays.append(handle["coordinates"][:])
    with Image.open(image_path) as image:
        require(image.mode == "RGB" and image.size == (640, 640), "Expected native 640x640 RGB")
        rgb = np.asarray(image)
    canonicalizer = load_module(paths[PREFIX + "canonicalize.py"], "locked_bcdata_canonicalizer")
    baseline = load_module(paths["src/pathology_edge/ihc_baseline.py"], "locked_ihc_baseline")
    canonical = canonicalizer.canonicalize(*arrays)
    require(not canonical["excluded"] and canonical["cross_label_conflicting_locations"] == 0,
            "Unexpected coordinate exclusion/conflict")
    points, truth = canonical["points"], canonical["truth"]
    model = read_json(paths["artifacts/ihc/model.json"])
    require(model["classes"] == list(baseline.CLASSES) and model["feature_radii_pixels"] == [3, 7],
            "Unexpected model class order or feature radius")
    probabilities = baseline.predict_proba(baseline.extract_features(rgb, points), model)
    require(probabilities.shape == (len(points), 4) and np.isfinite(probabilities).all()
            and (probabilities >= 0).all() and np.allclose(probabilities.sum(axis=1), 1),
            "Invalid class probabilities")
    predicted = probabilities.argmax(axis=1)
    metrics = baseline.classification_metrics(truth, predicted)
    ratio = baseline.tumor_ratios(truth, predicted)
    reference = next(row for row in read_json(paths[PREFIX + "results.json"])["per_image"] if row["image"] == name)
    matches = metrics["confusion_matrix"] == reference["metrics"]["confusion_matrix"]
    for key in ("gt", "predicted", "absolute_error_percentage_points", "gt_tumor_cell_count", "predicted_tumor_cell_count"):
        a, b = ratio[key], reference["tumor_ratio"][key]
        matches = matches and ((a is None and b is None) or
                               (a is not None and b is not None and math.isclose(a, b, rel_tol=0, abs_tol=1e-12)))
    summary = {"image_id": image_id, "image": name, "cells": len(points),
               "gt_class_counts": np.bincount(truth, minlength=4).tolist(),
               "predicted_class_counts": np.bincount(predicted, minlength=4).tolist(),
               "correct_cells": int((truth == predicted).sum()), "accuracy": metrics["accuracy"],
               "confusion_matrix": metrics["confusion_matrix"], "tumor_ratio": ratio,
               "matches_published_case": bool(matches), "new_inference_images": 1,
               "training_run": False, "automatic_cell_detection_run": False,
               "clinical_validation": False, "source_commit": SOURCE_COMMIT,
               "review_runner_sha256": sha(Path(__file__).read_bytes()),
               "input_sha256": input_hashes, "source_sha256": SOURCES,
               "environment": {"python": platform.python_version(), "numpy": np.__version__,
                               "scipy": scipy.__version__, "pillow": PIL.__version__, "h5py": h5py.__version__}}
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    require(matches, "Replay differs from published case; inspect summary.json before reviewing")
    private = {"image": name, "points": points.tolist(), "truth": truth.tolist(),
               "predicted": predicted.tolist(), "probabilities": probabilities.tolist()}
    (output_dir / "private-points.json").write_text(json.dumps(private, separators=(",", ":")) + "\n")
    svg_path = output_dir / f"comparison-{image_id}.svg"
    svg_path.write_text(comparison_svg(image_bytes, points, truth, predicted, summary), encoding="utf-8")
    result = {key: summary[key] for key in ("image_id", "cells", "correct_cells", "matches_published_case", "new_inference_images", "training_run")}
    result.update(view=str(svg_path), report=str(output_dir / "summary.json"))
    print(json.dumps(result, ensure_ascii=False))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--image", choices=("109", "208", "367", "378", "379", "381"), default="109")
    parser.add_argument("--source-root", type=Path, help="Optional local source; all frozen hashes still enforced")
    args = parser.parse_args()
    run(args.data_dir, args.output_dir, args.image, args.source_root)


if __name__ == "__main__":
    main()
