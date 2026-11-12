"""Create a PRIVATE local original/GT/prediction comparison for locked extrema.

The generated HTML contains source coordinates and references original images.
Keep it with the ignored local data; do not redistribute it or its screenshots.
This is deterministic scientific display, not image generation or new inference.
"""
import argparse
import gzip
import html
import json
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    evidence = Path(__file__).resolve().parent
    assert not args.output.resolve().is_relative_to(evidence.resolve())
    if args.output.exists():
        raise FileExistsError(args.output)
    result = json.loads((evidence / "results.json").read_text())
    extrema = result["groups"]["all_402"]["extrema"]
    names = sorted(set(name for metric in extrema.values()
                       for key in ("minimum_images", "maximum_images") for name in metric[key]))
    reports = {row["image"]: row for row in result["per_image"]}
    with gzip.open(args.predictions, "rt", encoding="utf-8") as stream:
        saved = {row["image"]: row for row in map(json.loads, stream) if row["image"] in names}
    colors = ["#ffe600", "#00e5ff", "#ff43dd", "#5dff54"]
    labels = ["tumor +", "tumor -", "other +", "other -"]
    parts = ['<!doctype html><meta charset="utf-8"><title>Private BCData source comparison</title>',
             '<style>body{font:16px system-ui;background:#111;color:#eee;margin:24px}a{color:#80caff}.panels{display:flex;gap:12px;overflow-x:auto}.panel{min-width:480px;max-width:640px;flex:1}svg{width:100%;height:auto}h2{margin-top:48px}li{margin:5px 0}</style>',
             '<h1>Private BCData original / supplied GT / frozen prediction</h1>',
             '<p>All four-class labels are evaluated at supplied GT centers. Source annotation duplicates were canonicalized before inference. Display scaling only; inference used native pixels. These examples are the full-set extrema with all ties, not selected successes.</p>',
             '<p>Non-commercial research only. This local page contains coordinates and references original data. Keep it and screenshots private.</p>',
             '<p>' + ' &nbsp; '.join(f'<span style="color:{c}">● {label}</span>' for c, label in zip(colors, labels)) + '</p>']
    for name in names:
        row, report = saved[name], reports[name]
        ratio = report["tumor_ratio"]
        gt_percent = ratio["gt"]*100
        pred_percent = ratio["predicted"]*100 if ratio["predicted"] is not None else None
        parts.append(f'<h2>{html.escape(name)}</h2>')
        parts.append(f'<p>GT positive ratio {gt_percent:.4f}%; predicted {pred_percent:.4f}%; absolute error {ratio["absolute_error_percentage_points"]:.5f} pp. Cell accuracy {report["metrics"]["accuracy"]*100:.4f}%. GT denominator {ratio["gt_tumor_cell_count"]}; predicted tumor denominator {ratio["predicted_tumor_cell_count"]}.</p>')
        relative = html.escape(os.path.relpath(args.data_dir / name, args.output.parent))
        links = [f'<a href="{relative}">Original PNG</a>']
        for label in ("positive", "negative"):
            h5 = args.data_dir / f"BCData/annotations/test/{label}/{Path(name).stem}.h5"
            links.append(f'<a href="{html.escape(os.path.relpath(h5, args.output.parent))}">{label} original HDF5</a>')
        parts.append('<p>' + ' · '.join(links) + '</p><div class="panels">')
        for title, key in (("Original pixels", None), ("Supplied GT at unique centers", "truth"), ("Frozen four-class predictions", "predicted")):
            parts.append(f'<div class="panel"><h3>{title}</h3><svg viewBox="0 0 640 640" xmlns="http://www.w3.org/2000/svg"><image href="{relative}" width="640" height="640"/>')
            if key:
                for point, target in zip(row["points"], row[key]):
                    parts.append(f'<circle cx="{point[0]}" cy="{point[1]}" r="4" fill="none" stroke="{colors[target]}" stroke-width="2"><title>{labels[target]} ({point[0]}, {point[1]})</title></circle>')
            parts.append('</svg></div>')
        parts.append('</div>')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        stream.write("\n".join(parts))
    print(json.dumps({"private_review": str(args.output), "images": names, "new_inference": False}))


if __name__ == "__main__":
    main()
