#!/usr/bin/env python3
"""Locked zero-shot MoNuSeg ROI evaluation; never train or tune on external data."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

import numpy as np
from PIL import Image

EXPECTED_MODELS = {
    'small_vit': '0bb2af67ca4d4e403e5789359feb6b284f9207e6c7eb9bf4e521b7d0972f5898',
    'small_vit_refined': 'b9d3892a257a06ed0b67bd4e8717a331d457272531b3501fadf1fbacd70f004f',
}
ARCHIVE_SHA = '13e522387ae8b1bcc0530e13ff9c7b4d91ec74959ef6f6e57747368d7ee6f88a'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False))


def verify_payloads(data, archive):
    """Bind every extracted image/annotation byte to the inspected archive."""
    data = Path(data)
    files = sorted(p for p in data.iterdir() if p.suffix.lower() in ('.tif', '.xml'))
    with zipfile.ZipFile(archive) as zipped:
        expected = {n for n in zipped.namelist() if n.endswith(('.tif', '.xml'))}
        actual = {f'MoNuSegTestData/{p.name}' for p in files}
        if actual != expected:
            raise ValueError('Extracted archive payload file set differs')
        for p in files:
            if digest(p) != hashlib.sha256(zipped.read(f'MoNuSegTestData/{p.name}')).hexdigest():
                raise ValueError(f'Extracted archive payload changed: {p.name}')


def audit(output):
    from pathology_edge.external_validation import score_probability
    from pathology_edge.learner_metrics import dice_score
    out = Path(output)
    protocol = json.loads((out / 'protocol.json').read_text())
    report = json.loads((out / 'results.json').read_text())
    if digest(out / 'protocol.json') != report['protocol_sha256']:
        raise ValueError('Protocol changed')
    ids = [(r['id'], r['case_id']) for r in report['rows']]
    expected = [(r['id'], r['case_id']) for r in protocol['images']]
    if (len(ids) != 14 or len(set(ids)) != 14 or len({r[1] for r in ids}) != 14
            or ids != expected or protocol['image_count'] != 14 or protocol['case_count'] != 14):
        raise ValueError('External image IDs/counts differ from complete14-image protocol')
    if protocol['models'] != EXPECTED_MODELS or protocol['threshold'] != .35:
        raise ValueError('Prespecified model/threshold changed')
    status = json.loads((out / 'status.json').read_text())
    if status.get('completed') is not True or status.get('returncode') != 0:
        raise ValueError('A failed or incomplete run cannot pass the audit')
    source_hashes = {p.name: digest(p) for p in sorted((out/'source/pathology_edge').glob('*.py'))}
    if source_hashes != protocol['source_sha256'] or digest(out/'runner.py') != protocol['runner_sha256']:
        raise ValueError('Frozen source or runner differs from protocol')
    required = {f'source/pathology_edge/{name}' for name in source_hashes}
    for architecture, sha in EXPECTED_MODELS.items():
        name = f'models/{architecture}.pt'
        if digest(out/name) != sha:
            raise ValueError('Fixed checkpoint differs')
        required.add(name)
    for row in report['rows']:
        if set(row['models']) != set(EXPECTED_MODELS):
            raise ValueError('Model result set differs')
        required.add(row['target'])
        required.update(v['probability'] for v in row['models'].values())
    if not required <= set(report['files']):
        raise ValueError('Required result assets missing from file manifest')
    for name, sha in report['files'].items():
        if not (out/name).resolve().is_relative_to(out.resolve()):
            raise ValueError('Result asset escapes the run directory')
        if digest(out / name) != sha:
            raise ValueError(f'Changed result file: {name}')
    from pathology_edge.patches import boundary_mask
    checks = 0
    for row in report['rows']:
        target = np.asarray(Image.open(out / row['target'])) > 0
        seam = boundary_mask(target.shape)
        for architecture in EXPECTED_MODELS:
            saved = row['models'][architecture]
            with np.load(out / saved['probability'], allow_pickle=False) as loaded:
                probability = loaded['probability']
            metrics = score_probability(probability, target, protocol['threshold'])
            if metrics != saved['metrics']:
                raise ValueError('Stored probabilities do not reproduce metrics')
            for region, selection in [('all', None), ('boundary', seam), ('interior', ~seam)]:
                if abs(dice_score(probability >= protocol['threshold'], target, selection)
                       - metrics[region]['dice']) > 1e-12:
                    raise ValueError('Independent learner Dice mismatch')
                checks += 1
    for architecture in EXPECTED_MODELS:
        for region in ('all', 'boundary', 'interior'):
            mean = float(np.mean([r['models'][architecture]['metrics'][region]['dice'] for r in report['rows']]))
            if mean != report['means'][architecture][region]:
                raise ValueError('Mean mismatch')
    for region in ('all', 'boundary', 'interior'):
        delta = report['means']['small_vit_refined'][region] - report['means']['small_vit'][region]
        differences = [r['models']['small_vit_refined']['metrics'][region]['dice']
                       - r['models']['small_vit']['metrics'][region]['dice'] for r in report['rows']]
        counts = [sum(d > 0 for d in differences), sum(d == 0 for d in differences), sum(d < 0 for d in differences)]
        if report['delta_refined_minus_baseline'][region] != delta or report['wins_ties_losses'][region] != counts:
            raise ValueError('External aggregate delta/win counts differ')
    review = dict(all_checks_passed=True, region_checks=checks, mean_checks=6,
                  images=len(report['rows']), protocol_sha256=report['protocol_sha256'],
                  checkpoint_loading_during_audit=False, inference_during_audit=False)
    save(out / 'audit.json', review)
    return review


def worker(output):
    import cv2
    import torch
    from pathology_edge.external_validation import rasterize_xml, score_probability
    from pathology_edge.model_comparison import build_model
    from pathology_edge.experiment import predict, environment
    out = Path(output)
    protocol = json.loads((out / 'protocol.json').read_text())
    torch.set_num_threads(4)
    cv2.setNumThreads(1)
    torch.use_deterministic_algorithms(True)
    models = {}
    for architecture, sha in EXPECTED_MODELS.items():
        path = out / 'models' / f'{architecture}.pt'
        if digest(path) != sha:
            raise ValueError('Checkpoint hash mismatch')
        model = build_model(architecture)
        model.load_state_dict(torch.load(path, map_location='cpu', weights_only=True))
        models[architecture] = model.eval()
    rows = []
    for item in protocol['images']:
        image_path, xml_path = Path(item['image']), Path(item['xml'])
        if digest(image_path) != item['image_sha256'] or digest(xml_path) != item['xml_sha256']:
            raise ValueError('External image or annotation changed')
        image = np.asarray(Image.open(image_path).convert('RGB')).copy()
        if image.shape != (1000, 1000, 3):
            raise ValueError('Unexpected native external image dimensions')
        target, nuclei = rasterize_xml(xml_path, image.shape[:2])
        target_path = out / 'targets' / f"{item['id']}.png"
        Image.fromarray(target.astype(np.uint8) * 255).save(target_path)
        row = dict(id=item['id'], case_id=item['case_id'], annotation_regions=nuclei,
                   target=str(target_path.relative_to(out)), models={})
        for architecture, model in models.items():
            result = predict(model, image, mode='no_overlap', threshold=protocol['threshold'])
            path = out / 'predictions' / f"{item['id']}-{architecture}.npz"
            np.savez_compressed(path, probability=result['probability'])
            row['models'][architecture] = dict(probability=str(path.relative_to(out)),
                metrics=score_probability(result['probability'], target, protocol['threshold']),
                seconds_single_run=result['seconds'], patch_count=result['patch_count'],
                skipped_background=result['skipped_background'])
        rows.append(row)
        print(item['id'], flush=True)
    means = {a: {region: float(np.mean([r['models'][a]['metrics'][region]['dice'] for r in rows]))
                  for region in ('all', 'boundary', 'interior')} for a in models}
    deltas = {region: means['small_vit_refined'][region] - means['small_vit'][region]
              for region in ('all', 'boundary', 'interior')}
    counts = {}
    for region in deltas:
        differences = [r['models']['small_vit_refined']['metrics'][region]['dice']
                       - r['models']['small_vit']['metrics'][region]['dice'] for r in rows]
        counts[region] = [sum(d > 0 for d in differences), sum(d == 0 for d in differences),
                          sum(d < 0 for d in differences)]
    files = {p.relative_to(out).as_posix(): digest(p)
             for folder in ('targets', 'predictions', 'models', 'source')
             for p in sorted((out / folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    report = dict(protocol_sha256=digest(out / 'protocol.json'), rows=rows, means=means,
                  delta_refined_minus_baseline=deltas, wins_ties_losses=counts, files=files,
                  environment=environment(), external_training_run=False,
                  external_threshold_selection=False, whole_wsi_validation=False,
                  clinical_validation=False, timing_scope='Single descriptive inference per image; not a speed benchmark')
    save(out / 'results.json', report)
    print(json.dumps(dict(inference_finished=True, images=len(rows))), flush=True)


def run(data, model_run, tnbc, output):
    from pathology_edge.data import load_image
    data, model_run, tnbc, out = map(lambda p: Path(p).resolve(), (data, model_run, tnbc, output))
    if out.exists() or out.is_relative_to(data) or out.is_relative_to(model_run):
        raise ValueError('Use a new independent output directory')
    archive = data.parent / 'MoNuSegTestData.zip'
    if digest(archive) != ARCHIVE_SHA:
        raise ValueError('Not the inspected official test archive')
    verify_payloads(data, archive)
    images = sorted(data.glob('*.tif'))
    if len(images) != 14 or len(list(data.glob('*.xml'))) != 14:
        raise ValueError('All14 external image/XML pairs required')
    tnbc_manifest = json.loads((tnbc / 'manifest.json').read_text())
    tnbc_rgb = {hashlib.sha256(load_image(tnbc / r['image']).tobytes()).hexdigest()
                for r in tnbc_manifest['records']}
    rows = []
    for p in images:
        image = load_image(p)
        pixel_sha = hashlib.sha256(image.tobytes()).hexdigest()
        if pixel_sha in tnbc_rgb:
            raise ValueError('Exact decoded RGB duplicate with TNBC')
        rows.append(dict(id=p.stem, case_id='-'.join(p.stem.split('-')[:3]), image=str(p),
                         xml=str(p.with_suffix('.xml')), image_sha256=digest(p),
                         xml_sha256=digest(p.with_suffix('.xml')), rgb_sha256=pixel_sha))
    for a, sha in EXPECTED_MODELS.items():
        training = json.loads((model_run / a / 'training.json').read_text())
        if (digest(model_run / a / 'model.pt') != sha or training['threshold'] != .35
                or training['config']['seed'] != 20261116):
            raise ValueError('Not the prespecified user model/threshold')
    out.mkdir(parents=True)
    for folder in ('targets', 'predictions', 'models'):
        (out / folder).mkdir()
    source = Path(__file__).resolve().parents[1] / 'src' / 'pathology_edge'
    shutil.copytree(source, out / 'source' / 'pathology_edge',
                    ignore=shutil.ignore_patterns('__pycache__', '*.so'))
    shutil.copy2(__file__, out / 'runner.py')
    for a in EXPECTED_MODELS:
        shutil.copy2(model_run / a / 'model.pt', out / 'models' / f'{a}.pt')
        shutil.copy2(model_run / a / 'training.json', out / 'models' / f'{a}-training.json')
    protocol = dict(dataset='MoNuSeg2018 official test, all14 annotated ROIs', images=rows,
        archive_sha256=ARCHIVE_SHA, source_url='https://monuseg.grand-challenge.org/Data/',
        license='CC BY-NC-SA 4.0; Kumar et al. MoNuSeg; TCGA source images',
        models=EXPECTED_MODELS, seed=20261116, threshold=.35,
        model_selection='Prespecified uploaded user pair, selected only on TNBC validation; no new external tuning',
        image_count=14, case_count=len({r['case_id'] for r in rows}),
        inference='native1000x1000RGB,128px non-overlap,white pad,existing tissue gate,no stain normalization or resizing',
        rasterization='np.rint(floatXY),OpenCV fillPoly per nucleus,canvas clips outside vertices,binary union; not official MATLAB/AJI parity',
        metrics='image-macro binary foreground Dice;128px internal seams with8px half-width;all/boundary/interior',
        tnbc_manifest_sha256=digest(tnbc / 'manifest.json'), exact_decoded_rgb_duplicates=0,
        patient_independence='Different public datasets; TNBC anonymized slide folders lack patient linkage, so patient-level non-overlap is not provable',
        annotation_scope='14 cropped1000x1000ROIs, not entireWSI', clinical_validation=False,
        source_sha256={p.name:digest(p) for p in sorted((out/'source/pathology_edge').glob('*.py'))},
        runner_sha256=digest(out / 'runner.py'))
    save(out / 'protocol.json', protocol)  # Frozen BEFORE first model prediction.
    env = dict(os.environ, PYTHONPATH=str(out / 'source'), PYTHONDONTWRITEBYTECODE='1')
    with (out / 'worker.log').open('w') as log:
        proc = subprocess.run([sys.executable, str(out / 'runner.py'), '--worker', str(out)],
                              cwd=out, env=env, stdout=log, stderr=subprocess.STDOUT)
    save(out / 'status.json', dict(completed=proc.returncode == 0, returncode=proc.returncode))
    if proc.returncode:
        raise RuntimeError(f'External evaluation failed; retained evidence at {out}')
    try:
        return audit(out)
    except BaseException as exc:
        save(out / 'status.json', dict(completed=False, returncode=proc.returncode,
                                      phase='audit', error=type(exc).__name__, message=str(exc)))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data')
    parser.add_argument('--model-run')
    parser.add_argument('--tnbc')
    parser.add_argument('--output')
    parser.add_argument('--worker')
    parser.add_argument('--audit')
    args = parser.parse_args()
    if args.worker:
        worker(args.worker)
    elif args.audit:
        print(json.dumps(audit(args.audit)))
    else:
        if not all((args.data, args.model_run, args.tnbc, args.output)):
            parser.error('--data --model-run --tnbc --output required')
        print(json.dumps(run(args.data, args.model_run, args.tnbc, args.output)))
