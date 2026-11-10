"""Reproduce Codex's STEP_40 geometry audit; no inference or artifact refresh.

From the repository root, with optional WSI dependencies installed:
PYTHONPATH=src python artifacts/learning/step40-codex-verify-mapping.py \
    --slide /path/to/CMU-1-JP2K-33005.svs --output work/roi-mapping-audit.json
"""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path

import numpy as np
import openslide
from PIL import Image

from pathology_edge.learner_wsi import roi_points_to_level0
from pathology_edge.wsi_export import SOURCE_SHA256, patch_manifest
from pathology_edge.wsi_roi import read_roi, roi_patch_manifest


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--slide', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    assert sha(args.slide) == SOURCE_SHA256
    saved = json.loads((root / 'dist/wsi.json').read_text())
    preparation = json.loads((root / 'artifacts/learning/step40-real-roi-reads.json').read_text())
    settings = [(row['name'], row['geometry']['origin_level0_xy'], row['geometry']['level'],
                 row['requested_size_wh'], row['geometry']['model_size_wh'],
                 row['geometry']['read_size_wh'], row['rgb_pixel_sha256'])
                for row in preparation['cases']]
    for row in saved['rois'][1:]:
        settings.append((f"native_{row['id']}", row['origin'], 0,
                         [row['width'], row['height']], [row['width'], row['height']],
                         [row['width'], row['height']], row['image_pixel_sha256']))
    records = []
    saved_patch_count = 0
    with openslide.OpenSlide(args.slide) as slide:
        for name, origin, level, requested, model_size, expected_read, expected_rgb in settings:
            roi = read_roi(slide, origin, level, requested, model_size)
            g = roi.geometry
            assert list(g.read_size_wh) == expected_read
            assert g.level_downsample == slide.level_downsamples[level]
            assert hashlib.sha256(roi.image.tobytes()).hexdigest() == expected_rgb
            mw, mh = g.model_size_wh
            rw, rh = g.read_size_wh
            ox, oy = g.origin_level0_xy
            dx, dy = rw * slide.level_downsamples[level], rh * slide.level_downsamples[level]
            # Independent extent oracle: original OpenSlide read footprint, before resize.
            points = np.array([[0, 0], [mw, 0], [0, mh], [mw, mh], [mw / 2, mh / 2]])
            expected = np.array([[ox, oy], [ox + dx, oy], [ox, oy + dy],
                                 [ox + dx, oy + dy], [ox + dx / 2, oy + dy / 2]])
            actual = roi_points_to_level0(points, g)
            np.testing.assert_allclose(actual, expected, rtol=0, atol=1e-9)
            manifests = {}
            native = next((r for r in saved['rois'] if name == f"native_{r['id']}"), None)
            if native:
                np.testing.assert_array_equal(roi.image, np.asarray(Image.open(root / 'dist' / native['image'])))
            for mode in ('no_overlap', 'overlap'):
                patches = roi_patch_manifest(g, mode)
                boxes = np.array([p['bbox_level0'] for p in patches])
                extent = [boxes[:, 0].min(), boxes[:, 1].min(), boxes[:, 2].max(), boxes[:, 3].max()]
                np.testing.assert_allclose(extent, [ox, oy, ox + dx, oy + dy], rtol=0, atol=1e-9)
                saved_equal = None
                if native:
                    assert patches == native['methods'][mode]['patches']
                    assert patches == patch_manifest(mw, mh, (ox, oy), mode)
                    saved_equal = True
                    saved_patch_count += len(patches)
                manifests[mode] = dict(patch_count=len(patches), last_patch=patches[-1],
                                       saved_native_manifest_equal=saved_equal)
            records.append(dict(name=name, geometry=asdict(g), requested_size_wh=requested,
                                rgb_matches_previous_read_or_saved_roi=True,
                                mapped_corners_and_center=actual.tolist(),
                                max_abs_extent_error=float(np.abs(actual - expected).max()),
                                methods=manifests))
        downsamples = list(slide.level_downsamples)
    report = dict(actor='Codex', date='2026-11-10', timezone='Asia/Seoul',
                  source_sha256=SOURCE_SHA256, source_bytes=args.slide.stat().st_size,
                  openslide_python=openslide.__version__, openslide=openslide.__library_version__,
                  code_sha256={p: sha(root / p) for p in (
                      'src/pathology_edge/learner_wsi.py', 'src/pathology_edge/learner_coordinates.py',
                      'src/pathology_edge/wsi_roi.py')},
                  actual_level_downsamples=downsamples, cases=records,
                  saved_native_roi_count=3, saved_native_patch_records_matched=saved_patch_count,
                  inference_run=False, published_files_rewritten=False,
                  scope='OpenSlide reads -> accepted user adapter -> patch footprint manifests. '
                        'Edge-coordinate geometry only; no centroid half-pixel correction, '
                        'vendor physical calibration, nonnative model inference or accuracy claim. '
                        'Original published native exporter remains unchanged.')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps(dict(real_read_mapping_cases=len(records),
                          saved_native_rois=3, saved_patch_records_matched=saved_patch_count,
                          max_abs_extent_error=max(r['max_abs_extent_error'] for r in records),
                          inference_run=False)))


if __name__ == '__main__':
    main()
