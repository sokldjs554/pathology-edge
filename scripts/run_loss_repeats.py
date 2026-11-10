"""STEP_42: freeze and run three paired seeds; summarize complete runs read-only.

Run from the existing repository root. No Git update, source edit, held-out
evaluation, automatic retry or best-seed selection is performed.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
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

SEEDS = (20261110, 20261111, 20261112)
MODES = ('bce_only', 'learner_dice')
LABELS = dict(bce_only='BCE only', learner_dice='BCE + learner soft Dice')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def planned_runs():
    return [dict(seed=seed, mode=mode, directory=f'runs/{seed}/{mode}')
            for i, seed in enumerate(SEEDS)
            for mode in (MODES[::-1] if i == 1 else MODES)]


def freeze(repo, data, output):
    repo, data, output = Path(repo).resolve(), Path(data).resolve(), Path(output).resolve()
    if output.exists():
        raise FileExistsError(f'Existing output is preserved: {output}')
    require(not output.is_relative_to(repo / 'src'), 'Output cannot be inside source')
    require(not output.is_relative_to(data), 'Output cannot be inside input data')
    manifest = load(data / 'manifest.json')
    require(Counter(r['split'] for r in manifest['records']) ==
            {'train': 33, 'validation': 10, 'test': 7}, 'Expected TNBC split 33/10/7')
    reference = load(repo / 'artifacts/protocol.json')
    controls = {k: v for k, v in reference.items()
                if k not in ('seed', 'loss', 'loss_mode', 'loss_source_sha256')}
    require(controls['epochs'] == 16 and controls['steps_per_epoch'] == 20 and
            controls['thresholds'] == [.35, .5, .65] and
            controls['test_used_for_selection'] is False, 'Reference training protocol changed')
    controls['manifest_sha256'] = sha(data / 'manifest.json')
    source = repo / 'src/pathology_edge'
    files = sorted(source.rglob('*.py'))
    require((source / 'learner_losses.py') in files, 'Missing learner loss source')
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip()
    status = subprocess.check_output(['git', 'status', '--short'], cwd=repo, text=True)
    diff = subprocess.check_output(['git', 'diff', 'HEAD', '--', 'src/pathology_edge'], cwd=repo, text=True)
    output.mkdir(parents=True)
    for path in files:
        dest = output / 'source/pathology_edge' / path.relative_to(source)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, dest)
    shutil.copyfile(data / 'manifest.json', output / 'manifest.json')
    shutil.copyfile(Path(__file__), output / 'runner.py')
    (output / 'source-commit.txt').write_text(commit + '\n')
    (output / 'source-status.txt').write_text(status)
    (output / 'source.diff').write_text(diff)
    plan = dict(schema_version=1, created_utc=datetime.now(timezone.utc).isoformat(),
                seeds=list(SEEDS), runs=planned_runs(), reference_controls=controls,
                data_path=str(data), source_commit=commit,
                source_sha256={p.relative_to(source).as_posix(): sha(output / 'source/pathology_edge' / p.relative_to(source))
                               for p in files}, runner_sha256=sha(output / 'runner.py'),
                source_import_root=str(output / 'source'),
                selection_scope='Same previously used validation set; no new held-out evaluation',
                time_scope='Existing train() total: epochs/validation/checkpoint writes/classical validation; excludes process startup/data loading',
                test_evaluation_run=False)
    dump(output / 'repeat-protocol.json', plan)
    return plan


def check_snapshot(output, plan):
    source = output / 'source/pathology_edge'
    require({p.relative_to(source).as_posix() for p in source.rglob('*.py')} ==
            set(plan['source_sha256']), 'Source file set changed')
    for name, digest in plan['source_sha256'].items():
        require(sha(source / name) == digest, f'Source changed: {name}')
    require(sha(output / 'runner.py') == plan['runner_sha256'], 'Archived runner changed')
    require(sha(output / 'manifest.json') == plan['reference_controls']['manifest_sha256'],
            'Frozen manifest changed')


def number(value, name, *, upper=None):
    require(type(value) in (int, float) and math.isfinite(value) and value >= 0,
            f'Invalid numeric value: {name}')
    require(upper is None or value <= upper, f'Out-of-range value: {name}')
    return value


def summarize(output):
    output = Path(output).resolve()
    plan = load(output / 'repeat-protocol.json')
    require(plan['seeds'] == list(SEEDS) and plan['runs'] == planned_runs(), 'Expected all fixed seed pairs')
    check_snapshot(output, plan)
    require({p.name for p in (output / 'runs').iterdir()} == {str(s) for s in SEEDS}, 'Unexpected seed folders')
    for seed in SEEDS:
        require({p.name for p in (output / 'runs' / str(seed)).iterdir()} == set(MODES), 'Expected exactly two arms')
    rows, environments = [], []
    for entry in plan['runs']:
        folder = output / entry['directory']
        report, config = load(folder / 'training.json'), load(folder / 'protocol.json')
        expected = dict(plan['reference_controls'], seed=entry['seed'],
                        loss_mode=entry['mode'], loss=LABELS[entry['mode']])
        if entry['mode'] == 'learner_dice':
            expected['loss_source_sha256'] = plan['source_sha256']['learner_losses.py']
        require(report['config'] == config == expected, f'Controls differ: {entry["directory"]}')
        require((report['train_images'], report['validation_images'], report['parameter_count']) ==
                (33, 10, 29761), 'Unexpected sample/model counts')
        require(sha(folder / 'manifest.json') == expected['manifest_sha256'], 'Run manifest changed')
        require(sha(folder / 'model.pt') == report['model_sha256'], 'Model hash mismatch')
        require(not (folder / 'evaluation.json').exists() and not (folder / 'evaluation_lock.json').exists(),
                'Unexpected held-out evaluation')
        history = report['history']
        require([h['epoch'] for h in history] == list(range(1, 17)), 'Expected all 16 epochs')
        choices = []
        for h in history:
            number(h['train_loss'], 'train_loss')
            require(set(h['validation_dice']) == {'0.35', '0.5', '0.65'}, 'Wrong threshold scores')
            for threshold in expected['thresholds']:
                score = number(h['validation_dice'][str(threshold)], 'validation Dice', upper=1)
                choices.append((score, h['epoch'], threshold))
        best = max(choices, key=lambda row: row[0])
        require(best == (report['best_validation_dice'], report['best_epoch'], report['threshold']),
                'Best epoch/threshold selection differs from history')
        environments.append(report['environment'])
        rows.append(dict(seed=entry['seed'], mode=entry['mode'], best_epoch=report['best_epoch'],
                         threshold=report['threshold'], validation_dice=best[0],
                         seconds=number(report['seconds'], 'training seconds'),
                         model_sha256=report['model_sha256']))
    require(all(e == environments[0] for e in environments), 'Run environments differ')
    arms = {}
    for mode in MODES:
        values = [r for r in rows if r['mode'] == mode]
        arms[mode] = dict(dice_mean=statistics.mean(r['validation_dice'] for r in values),
                          dice_sample_sd=statistics.stdev(r['validation_dice'] for r in values),
                          seconds_mean=statistics.mean(r['seconds'] for r in values),
                          seconds_sample_sd=statistics.stdev(r['seconds'] for r in values))
    pairs = []
    for seed in SEEDS:
        a, b = [next(r for r in rows if r['seed'] == seed and r['mode'] == mode) for mode in MODES]
        pairs.append(dict(seed=seed, delta_dice=b['validation_dice'] - a['validation_dice'],
                          delta_seconds=b['seconds'] - a['seconds']))
    delta = [p['delta_dice'] for p in pairs]
    return dict(run=str(output), seeds=list(SEEDS), all_checks_passed=True, runs=rows,
                arms=arms, pairs=pairs,
                paired_delta=dict(mean=statistics.mean(delta), sample_sd=statistics.stdev(delta),
                                  wins_ties_losses=[sum(d > 0 for d in delta), sum(d == 0 for d in delta), sum(d < 0 for d in delta)]),
                environment=environments[0], test_evaluation_run=False,
                limitation='Three paired seeds on the same previously used validation set; selected epoch/threshold scores, not independent test or clinical evidence. Training times are descriptive, not a controlled speed benchmark.')


def execute_training(command, *, cwd, env, log):
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


def run(repo, data, output):
    repo, data, output = Path(repo).resolve(), Path(data).resolve(), Path(output).resolve()
    plan = freeze(repo, data, output)
    (repo / 'work').mkdir(exist_ok=True)
    (repo / 'work/step42-repeat-run-path.txt').write_text(str(output) + '\n')
    env = dict(os.environ, PYTHONPATH=str(output / 'source'), PYTHONDONTWRITEBYTECODE='1')
    print(f'Run: {output}', flush=True)
    try:
        for index, entry in enumerate(plan['runs'], 1):
            check_snapshot(output, plan)
            require(sha(data / 'manifest.json') == plan['reference_controls']['manifest_sha256'], 'Input manifest changed')
            folder = output / entry['directory']
            folder.mkdir(parents=True)
            dump(output / 'status.json', dict(status='running', run_number=index, **entry))
            print(f'[{index}/6] seed={entry["seed"]} loss={entry["mode"]}', flush=True)
            command = [sys.executable, '-u', '-m', 'pathology_edge.cli', 'train',
                       '--data', str(data), '--output', str(folder), '--seed', str(entry['seed']),
                       '--epochs', '16', '--steps', '20', '--loss', entry['mode']]
            execute_training(command, cwd=output, env=env, log=folder / 'train.log')
        result = summarize(output)
        dump(output / 'summary.json', result)
        dump(output / 'status.json', dict(status='completed', runs=6, all_checks_passed=True))
        print('SUMMARY', flush=True)
        print(json.dumps(result, ensure_ascii=False, allow_nan=False), flush=True)
        return result
    except BaseException as exc:
        dump(output / 'status.json', dict(status='failed', error=type(exc).__name__, message=str(exc)))
        print(f'Failed; partial output preserved: {output}', file=sys.stderr, flush=True)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=Path('data'))
    parser.add_argument('--output', type=Path)
    parser.add_argument('--summarize', type=Path, help='Read and audit an existing run without training or writes')
    args = parser.parse_args()
    if args.summarize is not None:
        print(json.dumps(summarize(args.summarize), ensure_ascii=False, allow_nan=False))
    else:
        repo = Path.cwd()
        output = args.output or repo / 'work' / f'my-loss-repeats.{uuid.uuid4().hex[:12]}'
        run(repo, args.data, output)


if __name__ == '__main__':
    main()
