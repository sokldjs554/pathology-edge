#!/usr/bin/env python3
"""Run a new three-seed ViT/local-head experiment; never pool previous seed16 runs.

All six arms train from a single exact source snapshot. An optional previous
development or user reference is audited and recorded separately, never reused.
Audits read saved probabilities with the current trusted auditor, without inference.
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

_spec = importlib.util.spec_from_file_location('trusted_refinement_pair',
                                            Path(__file__).with_name('run_model_comparison.py'))
pair = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pair)

SEEDS = (20261116, 20261117, 20261118)
ARCHITECTURES = ('small_vit', 'small_vit_refined')
REGIONS = ('all', 'boundary', 'interior')
PROVENANCE_LABELS = ('development-reference', 'user-supplied')
EXPERIMENT_SCOPE = 'new-three-seed-experiment'


def source_hashes(source):
    files = sorted(source.rglob('*.py'))
    pair.require(not any(p.is_symlink() for p in source.rglob('*')), 'Source symlinks are not allowed')
    return {p.relative_to(source).as_posix(): pair.sha(p) for p in files}


def evidence_hashes(root):
    files = sorted(root.rglob('*'))
    pair.require(not any(p.is_symlink() for p in files), 'Reference symlinks are not allowed')
    return {p.relative_to(root).as_posix(): pair.sha(p) for p in files if p.is_file()}


def snapshot_hashes(out):
    result = {'source/'+name: digest for name, digest in source_hashes(out/'source').items()}
    result.update({name: pair.sha(out/name) for name in ('repeat-runner.py', 'pair-runner.py')})
    return result


def worker_probe(source, cwd, code):
    env = dict(os.environ, PYTHONPATH=str(source), PYTHONDONTWRITEBYTECODE='1')
    env.pop('PYTHONOPTIMIZE', None)
    return json.loads(subprocess.check_output([sys.executable, '-c', code], cwd=cwd, env=env, text=True))


def worker_environment(source, cwd):
    return worker_probe(source, cwd,
        'import json, torch; from pathology_edge.experiment import environment; '
        'torch.set_num_threads(4); print(json.dumps(environment(), allow_nan=False))')


def seed_preflights(source, cwd):
    """Check all seeds before any training starts, using the frozen worker source."""
    return worker_probe(source, cwd,
        'import json, torch; from pathology_edge.refinement import refinement_preflight; '
        'torch.set_num_threads(4); '
        f'print(json.dumps([refinement_preflight(s) for s in {SEEDS!r}], allow_nan=False))')


def schedule():
    return [dict(seed=seed, path=f'pairs/{seed}',
                 architecture_order=list(ARCHITECTURES if i % 2 == 0 else ARCHITECTURES[::-1]))
            for i, seed in enumerate(SEEDS)]


def moments(values):
    return dict(values=values, mean=statistics.mean(values), sample_sd=statistics.stdev(values), n=len(values))


def effects(values):
    return dict(**moments(values), wins=sum(v > 0 for v in values),
                ties=sum(v == 0 for v in values), losses=sum(v < 0 for v in values))


def image_effects(folder):
    """Use per-image values only after the pair's independent pixel audit passes."""
    baseline, refined = [pair.read(folder/name/'training.json')['validation']['rows'] for name in ARCHITECTURES]
    pair.require([(r['id'], r['group_id']) for r in baseline] ==
                 [(r['id'], r['group_id']) for r in refined], 'Paired validation image IDs/groups differ')
    return [dict(id=a['id'], group_id=a['group_id'],
                 baseline_dice={r: a['metrics'][r]['dice'] for r in REGIONS},
                 refined_dice={r: b['metrics'][r]['dice'] for r in REGIONS},
                 delta_refined_minus_baseline={r: b['metrics'][r]['dice']-a['metrics'][r]['dice'] for r in REGIONS})
            for a, b in zip(baseline, refined)]


def validate_preflights(reports):
    pair.require([r['seed'] for r in reports] == list(SEEDS), 'Preflight seeds differ')
    for report in reports:
        initial = report['initial_backbone_sha256']
        pair.require(report['all_checks_passed'] is True and
                     report['parameter_counts'] == {'small_vit': 33632, 'small_vit_refined': 33785},
                     'Refinement preflight controls differ')
        pair.require(isinstance(initial, str) and len(initial) == 64 and
                     all(c in '0123456789abcdef' for c in initial), 'Invalid initial backbone hash')
    pair.require(len({r['initial_backbone_sha256'] for r in reports}) == 3,
                 'Independent seeds must have distinct initial backbones')


def _audit_results(output, *, data_override=None):
    out = Path(output).resolve()
    plan = pair.read(out/'protocol.json')
    pair.require(plan['seeds'] == list(SEEDS) and plan['pairs'] == schedule(), 'Predeclared seeds/order changed')
    pair.require(plan['provenance_label'] in PROVENANCE_LABELS, 'Unknown provenance label')
    pair.require(plan['experiment_scope'] == EXPERIMENT_SCOPE and
                 plan['reference_included_in_aggregate'] is False, 'Previous reference must not be pooled')
    pair.require(snapshot_hashes(out) == plan['snapshot_hashes'], 'Frozen repeat source snapshot changed')
    pair.require(source_hashes(out/'source') == plan['effective_source_hashes'], 'Effective source differs')
    for name, digest in plan['reference_artifact_hashes'].items():
        pair.require(name in ('reference-summary.json', 'reference-protocol.json', 'reference-evidence.json') and
                     pair.sha(out/name) == digest, 'Recorded reference evidence changed')
    data = Path(data_override if data_override is not None else plan['data']).resolve()
    pair.require(pair.sha(data/'manifest.json') == plan['manifest_sha256'], 'Input manifest changed')
    preflights = pair.read(out/'refinement-preflights.json')
    pair.require(pair.sha(out/'refinement-preflights.json') == plan['preflights_sha256'], 'Seed preflights changed')
    validate_preflights(preflights)
    pairs, rows, images = [], [], []
    for item, preflight in zip(plan['pairs'], preflights):
        folder = out/item['path']
        pair.require(pair.sha(folder/'runner.py') == plan['snapshot_hashes']['pair-runner.py'],
                     'Pair orchestration source differs')
        report = pair.summarize(folder, data_override=data)
        pair_plan = pair.read(folder/'protocol.json')
        pair_source = {k.removeprefix('source/'): v for k, v in pair_plan['snapshot_hashes'].items()
                       if k.startswith('source/')}
        pair.require(report.get('comparison') == 'refinement' and report['seed'] == item['seed'],
                     'Pair design/seed differs')
        pair.require(report['architecture_order'] == item['architecture_order'], 'Pair architecture order differs')
        pair.require(pair_source == plan['effective_source_hashes'], 'Effective source differs between pairs')
        pair.require(report['environment'] == plan['environment'], 'Worker environment differs between pairs')
        pair.require(pair_plan['manifest_sha256'] == plan['manifest_sha256'], 'Dataset differs between pairs')
        pair.require(report['initial_backbone_sha256'] == preflight['initial_backbone_sha256'],
                     'Initial backbone differs from frozen seed preflight')
        pair.require(report['validation_metric_regions_checked'] == 60, 'Incomplete per-pair validation audit')
        pairs.append(report)
        rows.extend(dict(seed=item['seed'], architecture_order=item['architecture_order'], **row) for row in report['rows'])
        images.append(image_effects(folder))
    ids = [(row['id'], row['group_id']) for row in images[0]]
    pair.require(len(ids) == len(set(ids)) == 10 and
                 all([(r['id'], r['group_id']) for r in image_rows] == ids for image_rows in images),
                 'Expected the same ten validation images in every seed')
    per_image = [dict(id=image_id, group_id=group_id,
                      seed_rows=[dict(seed=seed, **image_rows[i]) for seed, image_rows in zip(SEEDS, images)],
                      paired_deltas={r: effects([image_rows[i]['delta_refined_minus_baseline'][r]
                                                for image_rows in images]) for r in REGIONS})
                 for i, (image_id, group_id) in enumerate(ids)]
    architectures = {name: {region: moments([row['validation_dice'][region] for row in rows
                                             if row['architecture'] == name]) for region in REGIONS}
                     for name in ARCHITECTURES}
    deltas = {region: effects([report['delta_refined_minus_baseline'][region] for report in pairs])
              for region in REGIONS}
    return dict(run=str(out), all_checks_passed=True, experiment_scope=EXPERIMENT_SCOPE, seeds=list(SEEDS),
                provenance_label=plan['provenance_label'], reference_included_in_aggregate=False,
                reference=plan['reference'], rows=rows, pairs=pairs, architectures=architectures,
                paired_deltas=deltas, per_image_effects=per_image, environment=plan['environment'],
                manifest_sha256=plan['manifest_sha256'], effective_source_hashes=plan['effective_source_hashes'],
                validation_metric_regions_checked=180, unique_validation_images=10,
                validation_groups=len({group for _, group in ids}), test_evaluation_run=False,
                tie_definition='Exact zero refined-minus-baseline Dice delta; no tolerance or rounding.',
                limitation='Three paired seeds describe seed variation on the same ten previously used validation '
                           'images from two groups. Epoch and threshold are selected on those images. The 30 '
                           'image-seed observations are repeated measurements, not 30 independent images. '
                           'Mean, sample SD and win counts are descriptive; no significance or general superiority '
                           'claim. Per-image effects also summarize the three seeds on each reused image. '
                           'All, boundary and interior Dice are image-macro measures. Timing and whole-process '
                           'peak RSS are descriptive. No independent test, external or clinical validation. '
                           'Prior development-reference and user-supplied seed16 results are never pooled.')


def summarize(output, *, data_override=None):
    """Read-only re-audit; neither archived code nor checkpoints are executed."""
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


def run(repo, data, output, *, reference=None, provenance_label):
    """Freeze the protocol and all seeds first; always train three fresh pairs."""
    repo, data, out = Path(repo).resolve(), Path(data).resolve(), Path(output).resolve()
    if out.exists():
        raise FileExistsError(out)
    pair.require(out.is_relative_to(repo/'work'), 'Output must be a fresh directory under repository work/')
    pair.require(not data.is_relative_to(out) and not out.is_relative_to(data), 'Output/data overlap')
    pair.require(provenance_label in PROVENANCE_LABELS, 'Explicit provenance label required')
    reference_path = Path(reference).resolve() if reference is not None else None
    reference_report, reference_hashes = None, None
    if reference_path is not None:
        pair.require(not out.is_relative_to(reference_path) and not reference_path.is_relative_to(out),
                     'Output/reference overlap')
        reference_hashes = evidence_hashes(reference_path)
        reference_report = pair.summarize(reference_path, data_override=data)
        pair.require(reference_report.get('comparison') == 'refinement' and reference_report['seed'] == SEEDS[0],
                     'Expected an original seed20261116 refinement reference')
    before = pair.original_state(repo)
    out.mkdir(parents=True)
    print(f'RUN_DIR={out}', flush=True)
    pair.dump(out/'original-before.json', before)
    pair.dump(out/'status.json', dict(status='preparing'))
    try:
        source_hashes(repo/'src')  # reject symlinks before copying source
        for path in sorted((repo/'src/pathology_edge').glob('*.py')):
            target = out/'source/pathology_edge'/path.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
        shutil.copy2(__file__, out/'repeat-runner.py')
        shutil.copy2(pair.__file__, out/'pair-runner.py')
        reference_artifacts = {}
        if reference_path is not None:
            pair.dump(out/'reference-summary.json', reference_report)
            shutil.copy2(reference_path/'protocol.json', out/'reference-protocol.json')
            pair.dump(out/'reference-evidence.json', reference_hashes)
            reference_artifacts = {name: pair.sha(out/name) for name in
                                   ('reference-summary.json', 'reference-protocol.json', 'reference-evidence.json')}
        environment = worker_environment(out/'source', out)
        preflights = seed_preflights(out/'source', out)
        validate_preflights(preflights)
        pair.dump(out/'refinement-preflights.json', preflights)
        plan = dict(seeds=list(SEEDS), pairs=schedule(), experiment_scope=EXPERIMENT_SCOPE,
                    reference_included_in_aggregate=False,
                    reference=str(reference_path) if reference_path else None,
                    reference_artifact_hashes=reference_artifacts,
                    provenance_label=provenance_label, data=str(data), source_commit=before['commit'],
                    source_dirty=bool(before['status']), manifest_sha256=pair.sha(data/'manifest.json'),
                    effective_source_hashes=source_hashes(out/'source'), snapshot_hashes=snapshot_hashes(out),
                    environment=environment, preflights_sha256=pair.sha(out/'refinement-preflights.json'),
                    source_policy='Exact current checkout Python source for all six newly trained arms. '
                                  'Only seed and architecture execution order vary. Previous runs are contextual '
                                  'references only, including previous results with seed20261116.')
        pair.dump(out/'protocol.json', plan)
        for item in plan['pairs']:
            pair.require(snapshot_hashes(out) == plan['snapshot_hashes'], 'Frozen repeat source snapshot changed')
            pair.require(pair.sha(__file__) == plan['snapshot_hashes']['repeat-runner.py'] and
                         pair.sha(pair.__file__) == plan['snapshot_hashes']['pair-runner.py'],
                         'Current orchestration source changed during repeat run')
            pair.dump(out/'status.json', dict(status='running', seed=item['seed'],
                                             architecture_order=item['architecture_order']))
            pair.run(repo, data, out/item['path'], seed=item['seed'], comparison='refinement',
                     architecture_order=tuple(item['architecture_order']), source_snapshot=out/'source')
        result = _audit_results(out)
        after = pair.original_state(repo)
        pair.dump(out/'original-after.json', after)
        pair.require(before == after, 'Original files or Git state changed during repeat experiment')
        if reference_path is not None:
            pair.require(evidence_hashes(reference_path) == reference_hashes, 'Original reference evidence changed')
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
    parser.add_argument('--reference', type=Path, help='Original seed16 pair, recorded separately and never pooled')
    parser.add_argument('--provenance-label', choices=PROVENANCE_LABELS)
    parser.add_argument('--summarize', type=Path, help='Read-only audit of all three new pairs')
    parser.add_argument('--data-override', type=Path, help='Relocated dataset for a saved-output audit')
    args = parser.parse_args()
    if args.summarize:
        print(json.dumps(summarize(args.summarize, data_override=args.data_override), ensure_ascii=False))
    else:
        if args.provenance_label is None:
            parser.error('--provenance-label is required for training')
        run(args.repo, args.data, args.output or args.repo/'work'/f'my-refinement-repeats.{uuid.uuid4().hex[:12]}',
            reference=args.reference, provenance_label=args.provenance_label)


if __name__ == '__main__':
    main()
