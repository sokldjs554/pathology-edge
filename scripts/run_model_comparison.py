#!/usr/bin/env python3
"""Freeze source, train a fixed CNN/ViT pair, and independently audit validation outputs.

No installation, test inference, demo export, or writes to existing experiments.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import uuid

ARCHITECTURES = ('tiny_unet', 'small_vit')
SEED = 20261113


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, payload):
    Path(path).write_text(json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False)+'\n')


def read(path):
    return json.loads(Path(path).read_text())


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True)


def original_state(repo):
    names = set(git(repo, 'ls-files', '-z').split('\0')) - {''}
    names.update(p.relative_to(repo).as_posix() for p in (repo/'src').rglob('*.py'))
    return dict(commit=git(repo, 'rev-parse', 'HEAD').strip(),
                status=git(repo, 'status', '--short'),
                hashes={name: sha(repo/name) if (repo/name).is_file() else None for name in sorted(names)})


def snapshot_hashes(out):
    files = sorted((out/'source').rglob('*.py')) + [out/'runner.py']
    return {p.relative_to(out).as_posix(): sha(p) for p in files}


def verify_snapshot(out, frozen):
    require(snapshot_hashes(out) == frozen, 'Frozen source snapshot changed')


def execute(command, *, cwd, env, log):
    with log.open('w') as handle:
        process = subprocess.Popen(command, cwd=cwd, env=env, text=True,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        try:
            for line in process.stdout:
                handle.write(line)
                handle.flush()
                print(line, end='', flush=True)
            code = process.wait()
            if code:
                raise subprocess.CalledProcessError(code, command)
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait()


def finite(value, *, upper=None):
    require(type(value) in (float, int) and math.isfinite(value) and value >= 0,
            'Invalid nonnegative measurement')
    require(upper is None or value <= upper, 'Measurement exceeds range')
    return value


def audit_predictions(folder, report, data, manifest):
    """Recount pixels independently; no model import or inference."""
    import numpy as np
    from PIL import Image
    rows = [r for r in manifest['records'] if r['split'] == 'validation']
    saved = report['validation']['rows']
    require([r['id'] for r in saved] == [r['id'] for r in rows], 'Validation IDs/order differ')
    for row, measured in zip(rows, saved):
        require(measured['group_id'] == row['group_id'], 'Validation group differs')
        prediction_path = (folder/measured['prediction']).resolve()
        require(prediction_path.is_relative_to(folder.resolve()/'predictions'), 'Invalid prediction path')
        require(sha(prediction_path) == measured['prediction_sha256'], 'Prediction hash mismatch')
        probability = np.load(prediction_path, allow_pickle=False)
        with Image.open(data/row['mask']) as image:
            target = np.asarray(image.convert('L')) > 0
        require(probability.shape == target.shape and probability.ndim == 2 and
                np.isfinite(probability).all() and ((probability >= 0) & (probability <= 1)).all(),
                'Invalid validation probability')
        prediction = probability >= report['threshold']
        # Independent seam construction: 8px each side of every internal 128px seam.
        boundary = np.zeros(target.shape, bool)
        for y in range(128, target.shape[0], 128):
            boundary[max(0, y-8):min(target.shape[0], y+8), :] = True
        for x in range(128, target.shape[1], 128):
            boundary[:, max(0, x-8):min(target.shape[1], x+8)] = True
        for name, region in [('all', np.ones(target.shape, bool)), ('boundary', boundary), ('interior', ~boundary)]:
            p, t = prediction[region], target[region]
            tp, fp, fn = int((p & t).sum()), int((p & ~t).sum()), int((~p & t).sum())
            expected = dict(tp=tp, fp=fp, fn=fn, pixels=int(region.sum()),
                            dice=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 1.,
                            iou=tp/(tp+fp+fn) if tp+fp+fn else 1.,
                            precision=tp/(tp+fp) if tp+fp else 0., recall=tp/(tp+fn) if tp+fn else 0.)
            require(measured['metrics'][name] == expected, 'Stored validation metrics differ from pixels')
        times = [finite(t) for t in measured['timings_seconds']]
        require(len(times) == 3 and statistics.median(times) == measured['median_seconds'], 'Invalid timing summary')
    for region in ('all', 'boundary', 'interior'):
        expected = statistics.mean(r['metrics'][region]['dice'] for r in saved)
        require(math.isclose(expected, report['validation']['macro_dice'][region], abs_tol=1e-12), 'Invalid macro Dice')
    require(statistics.median(r['median_seconds'] for r in saved) == report['validation']['median_image_seconds'],
            'Invalid aggregate timing')


def _audit_results(output):
    out = Path(output).resolve()
    plan = read(out/'protocol.json')
    verify_snapshot(out, plan['snapshot_hashes'])
    data = Path(plan['data'])
    require(sha(data/'manifest.json') == plan['manifest_sha256'], 'Input manifest changed')
    manifest = read(data/'manifest.json')
    for row in manifest['records']:
        for field in ('image', 'mask'):
            require(sha(data/row[field]) == row[field+'_sha256'], 'Dataset file changed')
    counts = {s: sum(r['split'] == s for r in manifest['records']) for s in ('train', 'validation', 'test')}
    require(counts == {'train': 33, 'validation': 10, 'test': 7}, 'Expected frozen TNBC 33/10/7 split')
    reports, rows = [], []
    source = {Path(k).name: v for k, v in plan['snapshot_hashes'].items() if k.startswith('source/pathology_edge/')}
    for architecture, parameters in zip(ARCHITECTURES, (29761, 33632)):
        folder = out/architecture
        report = read(folder/'training.json')
        config = report['config']
        require(report['architecture'] == architecture and report['parameter_count'] == parameters, 'Wrong architecture/parameter count')
        require(config == read(folder/'protocol.json') and config['seed'] == SEED and
                config['epochs'] == 16 and config['steps_per_epoch'] == 20 and config['batch_size'] == 8 and
                config['crop'] == 128 and config['optimizer'] == 'Adam' and config['learning_rate'] == .001 and
                config['loss_mode'] == 'learner_dice' and config['loss_source_sha256'] == source['learner_losses.py'] and
                config['validation_mode'] == 'no_overlap' and config['pretrained'] is False and
                config['test_used_for_selection'] is False and config['thresholds'] == [.35, .5, .65] and
                config['manifest_sha256'] == plan['manifest_sha256'], 'Fixed protocol changed')
        require(report['test_evaluation_run'] is False and not (folder/'evaluation.json').exists() and
                not (folder/'evaluation_lock.json').exists(), 'Unexpected test evaluation')
        require(report['train_images'] == 33 and report['validation_images'] == 10, 'Wrong image counts')
        require(read(folder/'source-hashes.json') == source, 'Worker used different source')
        require(sha(folder/'model.pt') == report['model_sha256'], 'Model hash mismatch')
        require(read(folder/'manifest.json') == manifest, 'Worker manifest differs')
        history = report['history']
        require(history == read(folder/'history.json') and [h['epoch'] for h in history] == list(range(1, 17)), 'Incomplete epoch history')
        choices = []
        for h in history:
            finite(h['train_loss'])
            require(set(h['validation_dice']) == {'0.35', '0.5', '0.65'}, 'Wrong thresholds')
            for threshold in config['thresholds']:
                choices.append((finite(h['validation_dice'][str(threshold)], upper=1), h['epoch'], threshold))
        best = max(choices, key=lambda choice: choice[0])
        require(best == (report['best_validation_dice'], report['best_epoch'], report['threshold']), 'Best selection differs')
        audit_predictions(folder, report, data, manifest)
        require(math.isclose(best[0], report['validation']['macro_dice']['all'], abs_tol=1e-12), 'Selected checkpoint differs')
        rows.append(dict(architecture=architecture, parameter_count=parameters, best_epoch=best[1], threshold=best[2],
                         validation_dice=report['validation']['macro_dice'], training_seconds=finite(report['seconds']),
                         median_pipeline_seconds=finite(report['validation']['median_image_seconds']),
                         peak_process_rss_mib=finite(report['peak_process_rss_mib']), model_sha256=report['model_sha256']))
        reports.append(report)
    require(reports[0]['config'] == reports[1]['config'], 'Controls differ between models')
    require(reports[0]['environment'] == reports[1]['environment'], 'Environments differ')
    require(reports[0]['augmentation_trace_sha256'] == reports[1]['augmentation_trace_sha256'], 'Crop/augmentation sequences differ')
    a, b = rows
    return dict(run=str(out), all_checks_passed=True, seed=SEED, rows=rows, image_counts=counts,
                validation_groups=len({r['group_id'] for r in manifest['records'] if r['split'] == 'validation'}),
                delta_vit_minus_cnn={k: b['validation_dice'][k]-a['validation_dice'][k] for k in ('all', 'boundary', 'interior')},
                environment=reports[0]['environment'], test_evaluation_run=False,
                validation_metric_regions_checked=60,
                limitation='One fixed seed on the same previously used validation set; epoch/threshold selected there. '
                           'From-scratch small segmentation adaptation, not pretrained ViT or an official paper reproduction. '
                           'Parameter counts differ; training/pipeline times and absolute whole-worker RSS are descriptive. '
                           'No independent test, external data or clinical validation; no claim that ViTs in general are better/worse.')


def summarize(output):
    """Audit a completed attempt; never turn a failed run into overall success."""
    out = Path(output).resolve()
    status = read(out/'status.json')
    require(status.get('status') == 'completed' and status.get('all_checks_passed') is True,
            'Expected a completed successful run; failed/partial attempts remain failed')
    before, after = read(out/'original-before.json'), read(out/'original-after.json')
    plan = read(out/'protocol.json')
    require(before == after and before['commit'] == plan['source_commit'] and
            bool(before['status']) == plan['source_dirty'], 'Original preservation evidence differs')
    result = _audit_results(out)
    result['original_files_preserved'] = True
    return result


def run(repo, data, output):
    repo, data, out = Path(repo).resolve(), Path(data).resolve(), Path(output).resolve()
    if out.exists():
        raise FileExistsError(out)
    require(out.is_relative_to(repo/'work'), 'Output must be a fresh directory under repository work/')
    require(not data.is_relative_to(out) and not out.is_relative_to(data), 'Output/data overlap')
    before = original_state(repo)
    out.mkdir(parents=True)
    print(f'RUN_DIR={out}', flush=True)
    (out/'RUN.txt').write_text(str(out)+'\n')
    dump(out/'original-before.json', before)
    try:
        for path in sorted((repo/'src/pathology_edge').glob('*.py')):
            target = out/'source/pathology_edge'/path.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
        shutil.copy2(__file__, out/'runner.py')
        plan = dict(seed=SEED, architectures=list(ARCHITECTURES), data=str(data),
                    source_commit=before['commit'], source_dirty=bool(before['status']),
                    manifest_sha256=sha(data/'manifest.json'), snapshot_hashes=snapshot_hashes(out))
        dump(out/'protocol.json', plan)
        env = dict(os.environ, PYTHONPATH=str(out/'source'), PYTHONDONTWRITEBYTECODE='1')
        env.pop('PYTHONOPTIMIZE', None)
        for architecture in ARCHITECTURES:
            verify_snapshot(out, plan['snapshot_hashes'])
            dump(out/'status.json', dict(status='running', architecture=architecture))
            execute([sys.executable, '-u', '-m', 'pathology_edge.model_comparison', '--data', str(data),
                     '--output', str(out/architecture), '--architecture', architecture],
                    cwd=out, env=env, log=out/f'{architecture}.log')
        result = _audit_results(out)
        after = original_state(repo)
        dump(out/'original-after.json', after)
        require(after == before, 'Original files or Git state changed during experiment')
        result['original_files_preserved'] = True
        dump(out/'summary.json', result)
        dump(out/'status.json', dict(status='completed', all_checks_passed=True))
        print('SUMMARY '+json.dumps(result, ensure_ascii=False), flush=True)
        return result
    except BaseException as exc:
        try:
            dump(out/'original-after.json', original_state(repo))
        except OSError:
            pass
        dump(out/'status.json', dict(status='failed', error=type(exc).__name__, message=str(exc)))
        print(f'Failure; partial outputs preserved: {out}', file=sys.stderr, flush=True)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path.cwd())
    parser.add_argument('--data', type=Path, default=Path('data'))
    parser.add_argument('--output', type=Path)
    parser.add_argument('--summarize', type=Path, help='Audit saved predictions without training, inference or writes')
    args = parser.parse_args()
    if args.summarize:
        print(json.dumps(summarize(args.summarize), ensure_ascii=False))
    else:
        run(args.repo, args.data, args.output or args.repo/'work'/f'my-cnn-vit.{uuid.uuid4().hex[:12]}')


if __name__ == '__main__':
    main()
