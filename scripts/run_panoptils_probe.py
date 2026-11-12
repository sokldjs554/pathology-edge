#!/usr/bin/env python3
"""Frozen 3-ROI WSI-linkage probe; coverage-limited GT, never clinical validation."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image

MODELS = {
    'small_vit': '0bb2af67ca4d4e403e5789359feb6b284f9207e6c7eb9bf4e521b7d0972f5898',
    'small_vit_refined': 'b9d3892a257a06ed0b67bd4e8717a331d457272531b3501fadf1fbacd70f004f',
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False))


def table(path):
    with Path(path).open(newline='') as stream:
        return list(csv.DictReader(stream))


def masks(root, name):
    from pathology_edge.panoptils import annotation_region
    fovs = [r for r in table(root/'csv/ALL_FOV_LOCATIONS.csv') if r['roiname'] == name+'.png']
    if len(fovs) != 1:
        raise ValueError('Exactly one matching FOV required')
    return annotation_region(np.asarray(Image.open(root/'masks'/f'{name}.png')),
                             table(root/'csv'/f'{name}.csv'), fovs[0])


def check_lock(out):
    lock = read(out/'lock.json')
    for name, expected in lock['files'].items():
        if not (out/name).resolve().is_relative_to(out.resolve()) or sha(out/name) != expected:
            raise ValueError(f'Frozen input/source changed: {name}')
    return lock


def worker(out):
    import cv2
    import torch
    from pathology_edge.experiment import predict, environment
    from pathology_edge.model_comparison import build_model
    from pathology_edge.panoptils import score_roi, roi_geometry
    from pathology_edge.learner_wsi import roi_points_to_level0
    check_lock(out)
    protocol = read(out/'probe-protocol.json')
    coords = read(out/'coordinate-evidence.json')
    if ([r['id'] for r in coords] != protocol['rois'] or len(coords) != 3
            or len({r['case_id'] for r in coords}) != 3 or protocol['expected_models'] != MODELS
            or protocol['threshold'] != .35):
        raise ValueError('Prespecified cohort/model/threshold changed')
    torch.set_num_threads(4)
    cv2.setNumThreads(1)
    torch.use_deterministic_algorithms(True)
    models = {}
    for architecture, digest in MODELS.items():
        path = out/'models'/f'{architecture}.pt'
        if sha(path) != digest:
            raise ValueError('Frozen checkpoint changed')
        model = build_model(architecture)
        model.load_state_dict(torch.load(path, map_location='cpu', weights_only=True))
        models[architecture] = model.eval()
    rows = []
    for item in coords:
        name = item['id']
        image = np.asarray(Image.open(out/'wsi'/f'{name}.png').convert('RGB')).copy()
        if image.shape != (1024, 1024, 3) or sha(out/'wsi'/f'{name}.png') != item['wsi_png_sha256']:
            raise ValueError('WSI server input differs')
        for kind, asset in item['source_assets'].items():
            if sha(out/kind/asset['name']) != asset['sha256']:
                raise ValueError('Source annotations/RGB changed')
        geometry = roi_geometry(item)
        corners = roi_points_to_level0(np.array([[0., 0.], [1024., 1024.]]), geometry).tolist()
        target, valid, coverage = masks(out, name)
        np.savez_compressed(out/'predictions'/f'{name}-gt.npz', target=target, valid=valid)
        row = dict(id=name, case_id=item['case_id'], coverage=coverage, corners_level0=corners, models={})
        for architecture, model in models.items():
            result = predict(model, image, mode='no_overlap', threshold=.35)
            filename = f'predictions/{name}-{architecture}.npz'
            np.savez_compressed(out/filename, probability=result['probability'])
            row['models'][architecture] = dict(probability=filename,
                metrics=score_roi(result['probability'], target, valid, .35),
                patch_count=result['patch_count'], skipped_background=result['skipped_background'],
                descriptive_seconds=result['seconds'])
        rows.append(row)
        print(name, flush=True)
    means = {a: {region: float(np.mean([r['models'][a]['metrics'][region]['dice'] for r in rows]))
                 for region in ('all', 'boundary', 'interior')} for a in MODELS}
    save(out/'results.json', dict(rows=rows, means=means, environment=environment(),
        lock_sha256=sha(out/'lock.json'),
        files={p.relative_to(out).as_posix(): sha(p) for p in sorted((out/'predictions').glob('*.npz'))},
        external_training_run=False, threshold_tuned=False, whole_wsi_validation=False,
        clinical_validation=False, full_wsi_file_downloaded=False,
        limitations=['Three convenience-selected cases, not a representative cohort.',
                     'Only reviewed FOV pixels outside box-only/ambiguous/unlabelled areas are scored.',
                     'WSI re-read has subpixel offset and RGB differences versus provided annotation RGB.',
                     'Effective output MPP is about0.30, inconsistent with advertised0.25; no scale harmonization.',
                     'TNBC has no patient crosswalk; patient-level independence cannot be established.']))


def audit(out):
    from pathology_edge.panoptils import roi_geometry
    from pathology_edge.learner_wsi import roi_points_to_level0
    from pathology_edge.learner_metrics import dice_score
    from pathology_edge.patches import boundary_mask
    check_lock(out)
    report = read(out/'results.json')
    coords = read(out/'coordinate-evidence.json')
    if report['lock_sha256'] != sha(out/'lock.json'):
        raise ValueError('Lock differs')
    if [r['id'] for r in report['rows']] != read(out/'probe-protocol.json')['rois']:
        raise ValueError('Results cohort differs')
    required = {f"predictions/{row['id']}-{suffix}.npz"
                for row in report['rows'] for suffix in ('gt', *MODELS)}
    if set(report['files']) != required:
        raise ValueError('Prediction manifest differs')
    for name, digest in report['files'].items():
        if sha(out/name) != digest:
            raise ValueError('Prediction asset changed')
    checks = 0
    for row, source in zip(report['rows'], coords):
        target, valid, coverage = masks(out, row['id'])
        with np.load(out/'predictions'/f"{row['id']}-gt.npz", allow_pickle=False) as saved:
            if not np.array_equal(target, saved['target']) or not np.array_equal(valid, saved['valid']):
                raise ValueError('Saved target/ignore masks differ from raw annotations')
        corners = roi_points_to_level0(np.array([[0., 0.], [1024., 1024.]]), roi_geometry(source)).tolist()
        if coverage != row['coverage'] or corners != row['corners_level0']:
            raise ValueError('Coverage or coordinate transform differs')
        seams = boundary_mask(target.shape, 128, 8)
        for architecture in MODELS:
            result = row['models'][architecture]
            with np.load(out/result['probability'], allow_pickle=False) as saved:
                probability = saved['probability']
            if probability.shape != target.shape or not np.isfinite(probability).all() or np.any((probability < 0) | (probability > 1)):
                raise ValueError('Invalid persisted probabilities')
            prediction = probability >= .35
            for name, area in [('all', valid), ('boundary', valid & seams), ('interior', valid & ~seams)]:
                p, t = prediction[area], target[area]
                tp = int(np.count_nonzero(p & t)); fp = int(np.count_nonzero(p & ~t)); fn = int(np.count_nonzero(~p & t))
                expected = dict(tp=tp, fp=fp, fn=fn, pixels=int(area.sum()),
                    dice=dice_score(prediction, target, area), iou=tp/(tp+fp+fn) if tp+fp+fn else 1.,
                    precision=tp/(tp+fp) if tp+fp else 0., recall=tp/(tp+fn) if tp+fn else 0.)
                if expected != result['metrics'][name]:
                    raise ValueError('Independent persisted-prediction recount differs')
                checks += 1
    for architecture in MODELS:
        for region in ('all', 'boundary', 'interior'):
            mean = float(np.mean([r['models'][architecture]['metrics'][region]['dice'] for r in report['rows']]))
            if mean != report['means'][architecture][region]:
                raise ValueError('Mean differs')
    result = dict(all_checks_passed=True, region_checks=checks, mean_checks=6,
                  raw_annotation_reconstruction=True, coordinate_corner_checks=3,
                  results_sha256=sha(out/'results.json'), inference_run_during_audit=False)
    save(out/'audit.json', result)
    return result


def run(data, model_run, out):
    data, model_run, out = map(lambda p: Path(p).resolve(), (data, model_run, out))
    if out.exists() or out.is_relative_to(data) or out.is_relative_to(model_run):
        raise ValueError('Use a fresh independent output directory')
    protocol = read(data/'probe-protocol.json')
    out.mkdir(parents=True)
    for name in ('probe-protocol.json', 'coordinate-evidence.json'):
        shutil.copy2(data/name, out/name)
    for kind in ('rgbs', 'masks', 'csv', 'wsi', 'models', 'predictions'):
        (out/kind).mkdir()
    shutil.copy2(data/'csv/ALL_FOV_LOCATIONS.csv', out/'csv/ALL_FOV_LOCATIONS.csv')
    for name in protocol['rois']:
        for kind in ('rgbs', 'masks', 'csv', 'wsi'):
            suffix = 'csv' if kind == 'csv' else 'png'
            shutil.copy2(data/kind/f'{name}.{suffix}', out/kind/f'{name}.{suffix}')
    for architecture in MODELS:
        shutil.copy2(model_run/architecture/'model.pt', out/'models'/f'{architecture}.pt')
    source = Path(__file__).resolve().parents[1]/'src/pathology_edge'
    shutil.copytree(source, out/'source/pathology_edge', ignore=shutil.ignore_patterns('__pycache__', '*.so'))
    shutil.copy2(__file__, out/'runner.py')
    save(out/'lock.json', dict(files={p.relative_to(out).as_posix(): sha(p) for p in sorted(out.rglob('*')) if p.is_file()},
        phase='All inputs, source and model hashes recorded before predictions',
        source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip(),
        source_status=subprocess.check_output(['git', 'status', '--short'], cwd=source, text=True)))
    import os
    with (out/'worker.log').open('w') as log:
        proc = subprocess.run([sys.executable, str(out/'runner.py'), '--worker', str(out)],
            env=dict(os.environ, PYTHONPATH=str(out/'source'), PYTHONDONTWRITEBYTECODE='1'),
            cwd=out, stdout=log, stderr=subprocess.STDOUT)
    save(out/'status.json', dict(returncode=proc.returncode, inference_completed=proc.returncode == 0))
    if proc.returncode:
        raise RuntimeError(f'Probe failed; evidence preserved: {out}')
    return audit(out)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('data', 'model-run', 'output', 'worker', 'audit'):
        parser.add_argument('--'+name)
    args = parser.parse_args()
    if args.worker:
        worker(Path(args.worker))
    elif args.audit:
        print(json.dumps(audit(Path(args.audit))))
    else:
        if not all((args.data, args.model_run, args.output)):
            parser.error('--data --model-run --output required')
        print(json.dumps(run(args.data, args.model_run, args.output)))
