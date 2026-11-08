"""Recompute the saved TNBC A/B Dice values with the user's reviewed function.

NumPy and Pillow only. Reads existing predictions; does not run a model.
Run from the repository root: python scripts/audit_dice.py
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from pathology_edge.learner_metrics import dice_score
from pathology_edge.patches import boundary_mask

MODES = ("no_overlap", "overlap")
SCOPES = ("all", "boundary", "interior")


def audit():
    files = {}

    def record(path):
        path = path.resolve()
        files[path.relative_to(ROOT).as_posix()] = {
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "bytes": path.stat().st_size,
        }
        return path

    def read_json(relative):
        return json.loads(record(ROOT / relative).read_text())

    def read_mask(path):
        with Image.open(record(path)) as source:
            pixels = np.asarray(source).copy()
        if pixels.ndim != 2 or not np.isin(pixels, [0, 255]).all():
            raise ValueError(f"Expected binary 0/255 PNG: {path}")
        return pixels > 0

    shown = read_json("dist/results.json")
    measured = read_json("artifacts/evaluation.json")
    training = read_json("artifacts/training.json")
    record(ROOT / "artifacts/model.pt")
    model_sha = files["artifacts/model.pt"]["sha256"]
    if any(data["model_sha256"] != model_sha for data in (shown, measured, training)):
        raise ValueError("Checkpoint and saved result model hashes differ")

    config = training["config"]
    patch_size, radius = config["patch_size"], config["seam_radius"]
    record(Path(__file__))
    record(ROOT / "src/pathology_edge/learner_metrics.py")
    record(ROOT / "src/pathology_edge/patches.py")
    samples = shown["samples"]
    groups = sorted({s["group_id"] for s in samples})
    original_groups = sorted({row["group_id"] for mode in MODES
                              for row in measured["methods"][mode]["rows"]})
    if (len(samples) != measured["test_images"] or len(groups) != measured["test_groups"]
            or groups != original_groups):
        raise ValueError("Exported test sample/group counts differ from the experiment")
    if len({s["id"] for s in samples}) != len(samples):
        raise ValueError("Duplicate sample ID in the export")

    rows = []
    for sample in samples:
        target = read_mask(ROOT / "dist" / sample["gt"])
        if target.shape != (sample["height"], sample["width"]):
            raise ValueError(f"Ground-truth shape differs: {sample['id']}")
        boundary = boundary_mask(target.shape, patch_size, radius)
        regions = {"all": None, "boundary": boundary, "interior": ~boundary}
        for mode in MODES:
            prediction = read_mask(ROOT / "artifacts/predictions" / mode / f"{sample['id']}.png")
            method = sample["methods"][mode]
            with Image.open(record(ROOT / "dist" / method["overlay"])) as source:
                overlay = np.asarray(source).copy()
            if overlay.shape != (*target.shape, 4) or not np.array_equal(overlay[..., 3] > 0, prediction):
                raise ValueError(f"Displayed overlay differs from prediction: {sample['id']}/{mode}")
            originals = [r for r in measured["methods"][mode]["rows"] if r["id"] == sample["id"]]
            if len(originals) != 1:
                raise ValueError(f"Missing or duplicate original result: {sample['id']}/{mode}")
            for scope, region in regions.items():
                value = dice_score(prediction, target, region)
                ui = method["metrics"][scope]
                original = originals[0]["metrics"][scope]
                pixels = int(target.size if region is None else np.count_nonzero(region))
                if pixels != ui["pixels"] or pixels != original["pixels"]:
                    raise ValueError(f"Evaluation area differs: {sample['id']}/{scope}")
                if not all(math.isclose(value, m["dice"], rel_tol=0, abs_tol=1e-12) for m in (ui, original)):
                    raise ValueError(f"Dice mismatch: {sample['id']}/{mode}/{scope}: {value}")
                rows.append(dict(id=sample["id"], group_id=sample["group_id"], method=mode,
                                 scope=scope, pixels=pixels, dice=value, displayed=ui["dice"],
                                 original=original["dice"], absolute_error=abs(value - original["dice"])))

    means = {}
    for mode in MODES:
        means[mode] = {}
        for scope in SCOPES:
            value = float(np.mean([r["dice"] for r in rows if r["method"] == mode and r["scope"] == scope]))
            expected = shown["summary"][mode]["macro_dice"][scope]
            original = measured["methods"][mode]["macro_dice"][scope]
            if not all(math.isclose(value, x, rel_tol=0, abs_tol=1e-12) for x in (expected, original)):
                raise ValueError(f"Image-mean Dice mismatch: {mode}/{scope}")
            means[mode][scope] = value

    return dict(verified_utc=datetime.now(timezone.utc).isoformat(),
                dataset=shown["dataset"], scope="Saved TNBC test PNGs; not WSI or IHC evaluation",
                test_images=len(samples), test_groups=groups, dice_checks=len(rows), mean_checks=6,
                patch_size=patch_size, seam_radius=radius,
                region_definition="Common internal baseline seams ±radius; image exterior excluded",
                ground_truth_source="Exported binary annotation PNGs; no annotation quality reassessment",
                mask_conversion="Validate PNG values 0/255, then convert to bool before calling dice_score",
                function="pathology_edge.learner_metrics.dice_score (user submitted)",
                aggregation="Arithmetic mean of per-image Dice; not pooled pixel Dice",
                model_inference_run=False, training_run=False,
                max_absolute_error=max(r["absolute_error"] for r in rows),
                means=means, rows=rows, files=files)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("work/dice-audit.json"))
    args = parser.parse_args()
    report = audit()
    protected = {(ROOT / name).resolve() for name in report["files"]}
    if args.output.resolve() in protected:
        raise ValueError("Output would overwrite an audited input file")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(f"{report['dice_checks']}/{report['dice_checks']} Dice values and 6/6 image means match.")
    print(f"{report['test_images']} test images / {len(report['test_groups'])} case groups; no inference run.")
    print("method           all       boundary  interior")
    for mode, means in report["means"].items():
        print(f"{mode:16} {means['all']:.6f}  {means['boundary']:.6f}  {means['interior']:.6f}")
    print(f"Report: {args.output}")


if __name__ == "__main__":
    main()
