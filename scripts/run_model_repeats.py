#!/usr/bin/env python3
"""Run three predeclared CNN/ViT seed pairs with identical frozen source and environment.

An optional complete baseline is copied without modifying it. Its exact frozen Python
source is used for additional training; no source equivalence heuristic is applied.
Saved-output audits use this checkout's auditor and never execute archived runners.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import uuid

_spec = importlib.util.spec_from_file_location('trusted_model_pair', Path(__file__).with_name('run_model_comparison.py'))
pair = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pair)

SEEDS = (20261113, 20261114, 20261115)
REGIONS = ('all', 'boundary', 'interior')
PROVENANCE_LABELS = ('development-reference', 'user-supplied')


def source_hashes(source):
    return {p.relative_to(source).as_posix(): pair.sha(p) for p in sorted(source.rglob('*.py'))}


def evidence_hashes(root):
    files = sorted(root.rglob('*'))
    pair.require(not any(p.is_symlink() for p in files), 'Symlinks are not allowed in baseline evidence')
    return {p.relative_to(root).as_posix(): pair.sha(p) for p in files if p.is_file()}


def snapshot_hashes(out):
    result = {'source/'+name: digest for name, digest in source_hashes(out/'source').items()}
    result.update({name: pair.sha(out/name) for name in ('repeat-runner.py', 'pair-runner.py')})
    return result


def worker_environment(source, cwd):
    """Read the actual worker fingerprint in a fresh process before training."""
    env = dict(os.environ, PYTHONPATH=str(source), PYTHONDONTWRITEBYTECODE='1')
    env.pop('PYTHONOPTIMIZE', None)
    code = ('import json, torch; from pathology_edge.experiment import environment; '
            'torch.set_num_threads(4); print(json.dumps(environment(), allow_nan=False))')
    return json.loads(subprocess.check_output([sys.executable, '-c', code], cwd=cwd, env=env, text=True))


def schedule(reused_baseline):
    return [dict(seed=seed, path=f'pairs/{seed}',
                 architecture_order=list(pair.ARCHITECTURES if i % 2 == 0 else pair.ARCHITECTURES[::-1]),
                 reused_baseline=bool(reused_baseline and i == 0))
            for i, seed in enumerate(SEEDS)]


def moments(values):
    return dict(values=values, mean=statistics.mean(values), sample_sd=statistics.stdev(values), n=len(values))


def _audit_results(output, *, data_override=None):
    out = Path(output).resolve()
    plan = pair.read(out/'protocol.json')
    pair.require(plan['seeds'] == list(SEEDS), 'Predeclared seeds changed or duplicated')
    pair.require(plan['provenance_label'] in PROVENANCE_LABELS, 'Unknown provenance label')
    pair.require(type(plan['reused_baseline']) is bool and
                 plan['pairs'] == schedule(plan['reused_baseline']), 'Predeclared pair order changed')
    pair.require(snapshot_hashes(out) == plan['snapshot_hashes'], 'Frozen repeat source snapshot changed')
    pair.require(source_hashes(out/'source') == plan['effective_source_hashes'], 'Effective source differs')
    data = Path(data_override if data_override is not None else plan['data']).resolve()
    pair.require(pair.sha(data/'manifest.json') == plan['manifest_sha256'], 'Input manifest changed')
    pairs, rows = [], []
    for item in plan['pairs']:
        folder = out/item['path']
        if item['reused_baseline']:
            pair.require(evidence_hashes(folder) == plan['baseline_evidence_hashes'], 'Copied baseline evidence changed')
        else:
            pair.require(pair.sha(folder/'runner.py') == plan['snapshot_hashes']['pair-runner.py'],
                         'Pair orchestration source differs')
        report = pair.summarize(folder, data_override=data)
        pair_plan = pair.read(folder/'protocol.json')
        pair_source = {k.removeprefix('source/'): v for k, v in pair_plan['snapshot_hashes'].items()
                       if k.startswith('source/')}
        pair.require(report['seed'] == item['seed'], 'Pair seed differs from predeclared seed')
        pair.require(report['architecture_order'] == item['architecture_order'], 'Pair architecture order differs')
        pair.require(pair_source == plan['effective_source_hashes'], 'Effective source differs between pairs')
        pair.require(report['environment'] == plan['environment'], 'Worker environment differs between pairs')
        pair.require(pair_plan['manifest_sha256'] == plan['manifest_sha256'], 'Dataset differs between pairs')
        pair.require(report['validation_metric_regions_checked'] == 60, 'Incomplete per-pair validation audit')
        pairs.append(report)
        rows.extend(dict(seed=item['seed'], architecture_order=item['architecture_order'],
                         reused_baseline=item['reused_baseline'], **row) for row in report['rows'])
    pair.require(len(rows) == 6, 'Expected six audited architecture rows')
    architectures = {name: {region: moments([row['validation_dice'][region] for row in rows
                                             if row['architecture'] == name]) for region in REGIONS}
                     for name in pair.ARCHITECTURES}
    deltas = {}
    for region in REGIONS:
        values = [report['delta_vit_minus_cnn'][region] for report in pairs]
        deltas[region] = dict(**moments(values), wins=sum(v > 0 for v in values),
                             ties=sum(v == 0 for v in values), losses=sum(v < 0 for v in values))
    return dict(run=str(out), all_checks_passed=True, seeds=list(SEEDS),
                provenance_label=plan['provenance_label'], rows=rows, pairs=pairs,
                architectures=architectures, paired_deltas=deltas, environment=plan['environment'],
                manifest_sha256=plan['manifest_sha256'], effective_source_hashes=plan['effective_source_hashes'],
                validation_metric_regions_checked=180, test_evaluation_run=False,
                tie_definition='Exact zero ViT-minus-CNN image-macro Dice delta; no tolerance or rounding.',
                limitation='Three predeclared paired seeds on the same previously used validation set; '
                           'epoch and threshold are selected there. Mean and sample SD describe seed variation; '
                           'three seeds do not establish general superiority. All, boundary and interior Dice '
                           'are image-macro measures. Training/pipeline time and whole-process peak RSS are '
                           'descriptive, with reused baseline timing measured earlier. Small from-scratch models '
                           'have different parameter counts. No independent test, external or clinical validation. '
                           'Development-reference and user-supplied runs must remain separate.')


def summarize(output, *, data_override=None):
    """Reaudit every saved probability; never execute saved code or rewrite evidence."""
    out = Path(output).resolve()
    status = pair.read(out/'status.json')
    pair.require(status.get('status') == 'completed' and status.get('all_checks_passed') is True,
                 'Expected a completed successful repeat run; failed/partial attempts remain failed')
    before, after = pair.read(out/'original-before.json'), pair.read(out/'original-after.json')
    plan = pair.read(out/'protocol.json')
    pair.require(before == after and before['commit'] == plan['source_commit'] and
                 bool(before['status']) == plan['source_dirty'], 'Original preservation evidence differs')
    result = _audit_results(out, data_override=data_override)
    result['original_files_preserved'] = True
    return result


def run(repo, data, output, *, baseline=None, provenance_label):
    """Freeze all three seeds, then train only missing pairs into fresh directories."""
    repo, data, out = Path(repo).resolve(), Path(data).resolve(), Path(output).resolve()
    if out.exists():
        raise FileExistsError(out)
    pair.require(out.is_relative_to(repo/'work'), 'Output must be a fresh directory under repository work/')
    pair.require(not data.is_relative_to(out) and not out.is_relative_to(data), 'Output/data overlap')
    pair.require(provenance_label in PROVENANCE_LABELS, 'Explicit development-reference or user-supplied provenance required')
    baseline_path = Path(baseline).resolve() if baseline is not None else None
    baseline_report, baseline_hashes = None, None
    if baseline_path is not None:
        pair.require(not out.is_relative_to(baseline_path) and not baseline_path.is_relative_to(out), 'Output/baseline overlap')
        baseline_hashes = evidence_hashes(baseline_path)
        baseline_report = pair.summarize(baseline_path, data_override=data)
        pair.require(baseline_report['seed'] == SEEDS[0] and
                     baseline_report['architecture_order'] == list(pair.ARCHITECTURES),
                     'Baseline seed/order differs from the predeclared first pair')
    before = pair.original_state(repo)
    out.mkdir(parents=True)
    print(f'RUN_DIR={out}', flush=True)
    pair.dump(out/'original-before.json', before)
    pair.dump(out/'status.json', dict(status='preparing'))
    try:
        source = baseline_path/'source' if baseline_path is not None else repo/'src'
        for path in sorted((source/'pathology_edge').glob('*.py')):
            pair.require(not path.is_symlink(), 'Source symlinks are not allowed')
            target = out/'source/pathology_edge'/path.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
        shutil.copy2(__file__, out/'repeat-runner.py')
        shutil.copy2(pair.__file__, out/'pair-runner.py')
        environment = worker_environment(out/'source', out)
        plan = dict(seeds=list(SEEDS), pairs=schedule(baseline_path is not None),
                    reused_baseline=baseline_path is not None, baseline=str(baseline_path) if baseline_path else None,
                    baseline_evidence_hashes=baseline_hashes, provenance_label=provenance_label, data=str(data),
                    source_commit=before['commit'], source_dirty=bool(before['status']),
                    manifest_sha256=pair.sha(data/'manifest.json'), effective_source_hashes=source_hashes(out/'source'),
                    snapshot_hashes=snapshot_hashes(out), environment=environment,
                    source_policy='Exact baseline frozen Python source when reused; otherwise exact checkout source. '
                                  'Only seed and architecture execution order vary. Current orchestration is frozen separately.')
        pair.dump(out/'protocol.json', plan)
        if baseline_report is not None:
            pair.require(environment == baseline_report['environment'], 'Current worker environment differs from baseline environment')
            baseline_plan = pair.read(baseline_path/'protocol.json')
            baseline_source = {k.removeprefix('source/'): v for k, v in baseline_plan['snapshot_hashes'].items()
                               if k.startswith('source/')}
            pair.require(plan['effective_source_hashes'] == baseline_source, 'Baseline effective source changed during freeze')
            shutil.copytree(baseline_path, out/'pairs'/str(SEEDS[0]))
            pair.require(evidence_hashes(baseline_path) == baseline_hashes ==
                         evidence_hashes(out/'pairs'/str(SEEDS[0])), 'Baseline evidence changed during copy')
        for item in plan['pairs']:
            pair.require(snapshot_hashes(out) == plan['snapshot_hashes'], 'Frozen repeat source snapshot changed')
            pair.require(pair.sha(__file__) == plan['snapshot_hashes']['repeat-runner.py'] and
                         pair.sha(pair.__file__) == plan['snapshot_hashes']['pair-runner.py'],
                         'Current orchestration source changed during repeat run')
            if item['reused_baseline']:
                continue
            pair.dump(out/'status.json', dict(status='running', seed=item['seed'],
                                             architecture_order=item['architecture_order']))
            pair.run(repo, data, out/item['path'], seed=item['seed'],
                     architecture_order=tuple(item['architecture_order']), source_snapshot=out/'source')
        result = _audit_results(out)
        after = pair.original_state(repo)
        pair.dump(out/'original-after.json', after)
        pair.require(before == after, 'Original files or Git state changed during repeat experiment')
        if baseline_path is not None:
            pair.require(evidence_hashes(baseline_path) == baseline_hashes, 'Original baseline evidence changed during experiment')
        result['original_files_preserved'] = True
        pair.dump(out/'summary.json', result)
        pair.dump(out/'status.json', dict(status='completed', all_checks_passed=True))
        print('SUMMARY '+json.dumps(result, ensure_ascii=False), flush=True)
        return result
    except BaseException as exc:
        try:
            pair.dump(out/'original-after.json', pair.original_state(repo))
        except OSError:
            pass
        pair.dump(out/'status.json', dict(status='failed', error=type(exc).__name__, message=str(exc)))
        print(f'Failure; partial outputs preserved: {out}', file=sys.stderr, flush=True)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path.cwd())
    parser.add_argument('--data', type=Path, default=Path('data'))
    parser.add_argument('--output', type=Path)
    parser.add_argument('--baseline', type=Path, help='Complete original seed pair with source and raw probabilities')
    parser.add_argument('--provenance-label', choices=PROVENANCE_LABELS)
    parser.add_argument('--summarize', type=Path, help='Read-only audit of all saved pairs')
    parser.add_argument('--data-override', type=Path, help='Relocated dataset for a read-only audit')
    args = parser.parse_args()
    if args.summarize:
        print(json.dumps(summarize(args.summarize, data_override=args.data_override), ensure_ascii=False))
    else:
        if args.provenance_label is None:
            parser.error('--provenance-label is required for training')
        run(args.repo, args.data, args.output or args.repo/'work'/f'my-cnn-vit-repeats.{uuid.uuid4().hex[:12]}',
            baseline=args.baseline, provenance_label=args.provenance_label)


if __name__ == '__main__':
    main()
