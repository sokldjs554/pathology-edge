"""Additional head seeds are a new, audited experiment on ten reused images."""
import hashlib
from pathlib import Path
import shutil
import statistics

import pytest
import torch

from test_model_repeats import completed_pair, data, load_script, pair

ARCHITECTURES = ('small_vit', 'small_vit_refined')
SEEDS = (20261116, 20261117, 20261118)
REGIONS = ('all', 'boundary', 'interior')


def initial_hash(seed):
    return hashlib.sha256(str(seed).encode()).hexdigest()


def preflight(seed):
    return dict(seed=seed, all_checks_passed=True,
                parameter_counts={'small_vit': 33632, 'small_vit_refined': 33785},
                initial_backbone_sha256=initial_hash(seed))


def completed_refinement(pair, out, data, seed=20261116, order=ARCHITECTURES, missing_rows=(0, 2)):
    completed_pair(pair, out, data, seed=seed, missing_rows=missing_rows)
    (out/'small_vit').rename(out/'small_vit_refined')
    (out/'tiny_unet').rename(out/'small_vit')
    for architecture, count in zip(ARCHITECTURES, (33632, 33785)):
        path = out/architecture/'training.json'
        report = pair.read(path)
        report.update(architecture=architecture, parameter_count=count,
                      initial_backbone_sha256=initial_hash(seed))
        pair.dump(path, report)
    plan = pair.read(out/'protocol.json')
    plan.update(comparison='refinement', architectures=list(order))
    pair.dump(out/'protocol.json', plan)
    pair.dump(out/'refinement-preflight.json', preflight(seed))
    return out


@pytest.fixture
def repeats():
    path = Path(__file__).parents[1]/'scripts/run_refinement_repeats.py'
    assert path.exists(), 'Additional refinement seeds need an audited repeat runner'
    return load_script('run_refinement_repeats')


def test_additional_predeclared_seeds_preserve_identity_and_rng(pair):
    from pathology_edge.refinement import refinement_preflight
    before = torch.get_rng_state().clone()
    reports = [refinement_preflight(seed) for seed in SEEDS]
    assert torch.equal(torch.get_rng_state(), before)
    assert len({r['initial_backbone_sha256'] for r in reports}) == 3
    assert refinement_preflight() == reports[0]
    for seed in SEEDS:
        pair.validate_design(seed, ARCHITECTURES, 'refinement')
    for seed in (True, 0, 20261115, 20261119):
        with pytest.raises(ValueError, match='seed'):
            refinement_preflight(seed)
        with pytest.raises(ValueError, match='seed'):
            pair.validate_design(seed, ARCHITECTURES, 'refinement')


def prepare(repeats, pair, data, tmp_path, monkeypatch, *, failure=None):
    reference = completed_refinement(pair, tmp_path/'reference', data)
    shutil.copytree(reference/'source', tmp_path/'src')
    state = dict(commit='new', status='', hashes={'tracked': 'original'})
    monkeypatch.setattr(repeats.pair, 'original_state', lambda repo: state)
    monkeypatch.setattr(repeats, 'worker_environment', lambda source, cwd: dict(python='test', torch_threads=4))
    monkeypatch.setattr(repeats, 'seed_preflights', lambda source, cwd: [preflight(seed) for seed in SEEDS])
    calls = []

    def fake_run(repo, data, output, *, seed, architecture_order, source_snapshot, comparison):
        calls.append((seed, architecture_order, comparison))
        if failure:
            raise RuntimeError(failure)
        completed_refinement(pair, output, data, seed, architecture_order,
                             missing_rows={20261116: (0, 2), 20261117: (3, 1), 20261118: (2, 2)}[seed])
        shutil.rmtree(output/'source')
        shutil.copytree(source_snapshot, output/'source')
        shutil.copy2(repeats.pair.__file__, output/'runner.py')
        plan = pair.read(output/'protocol.json')
        plan['snapshot_hashes'] = pair.snapshot_hashes(output)
        pair.dump(output/'protocol.json', plan)
        return pair.summarize(output)

    monkeypatch.setattr(repeats.pair, 'run', fake_run)
    return reference, tmp_path/'work/new-repeats', calls


def test_repeats_train_all_three_pairs_and_keep_reused_images_paired(repeats, pair, data, tmp_path, monkeypatch):
    reference, out, calls = prepare(repeats, pair, data, tmp_path, monkeypatch)
    before = repeats.evidence_hashes(reference)
    summary = repeats.run(tmp_path, data, out, reference=reference, provenance_label='development-reference')
    assert calls == [(20261116, ARCHITECTURES, 'refinement'),
                     (20261117, ARCHITECTURES[::-1], 'refinement'),
                     (20261118, ARCHITECTURES, 'refinement')]
    assert summary['experiment_scope'] == 'new-three-seed-experiment'
    assert summary['reference_included_in_aggregate'] is False
    assert summary['seeds'] == list(SEEDS)
    assert summary['validation_metric_regions_checked'] == 180
    assert summary['unique_validation_images'] == 10
    assert len(summary['per_image_effects']) == 10
    for region in REGIONS:
        deltas = [p['delta_refined_minus_baseline'][region] for p in summary['pairs']]
        aggregate = summary['paired_deltas'][region]
        assert aggregate['values'] == deltas and aggregate['n'] == 3
        assert aggregate['mean'] == statistics.mean(deltas)
        assert aggregate['sample_sd'] == statistics.stdev(deltas)
        assert (aggregate['wins'], aggregate['ties'], aggregate['losses']) == (1, 1, 1)
        for row in summary['per_image_effects']:
            effect = row['paired_deltas'][region]
            assert effect['values'] == deltas and effect['n'] == 3
            assert effect['sample_sd'] == statistics.stdev(deltas)
    assert repeats.evidence_hashes(reference) == before
    relocated = tmp_path/'relocated-data'
    data.rename(relocated)
    moved = tmp_path/'moved-output'
    out.rename(moved)
    shutil.rmtree(reference)
    assert repeats.summarize(moved, data_override=relocated)['per_image_effects'] == summary['per_image_effects']


@pytest.mark.parametrize('change', ['duplicate_seed', 'order', 'source', 'model', 'trace',
                                  'initial', 'environment', 'probability', 'partial', 'reference'])
def test_audits_refuse_mismatched_evidence(repeats, pair, data, tmp_path, monkeypatch, change):
    reference, out, _ = prepare(repeats, pair, data, tmp_path, monkeypatch)
    repeats.run(tmp_path, data, out, reference=reference, provenance_label='development-reference')
    folder = out/'pairs/20261117'
    if change in ('duplicate_seed', 'order'):
        plan = pair.read(out/'protocol.json')
        if change == 'duplicate_seed':
            plan['seeds'][1] = 20261116
        else:
            plan['pairs'][1]['architecture_order'].reverse()
        pair.dump(out/'protocol.json', plan)
    elif change == 'source':
        (folder/'source/pathology_edge/model_comparison.py').write_text('# changed\n')
    elif change == 'model':
        (folder/'small_vit/model.pt').write_bytes(b'changed')
    elif change == 'probability':
        import numpy as np
        target = folder/'small_vit/predictions/00.npy'
        np.save(target, np.zeros((256, 256), np.float32))
        path = folder/'small_vit/training.json'
        report = pair.read(path)
        report['validation']['rows'][0]['prediction_sha256'] = pair.sha(target)
        pair.dump(path, report)
    elif change == 'partial':
        pair.dump(folder/'status.json', dict(status='failed', all_checks_passed=True))
    elif change == 'reference':
        (out/'reference-summary.json').write_text('{}')
    else:
        for architecture in ARCHITECTURES:
            path = folder/architecture/'training.json'
            report = pair.read(path)
            if change == 'trace':
                if architecture == 'small_vit':
                    report['augmentation_trace_sha256'] = 'different'
            elif change == 'initial':
                report['initial_backbone_sha256'] = 'b'*64
            else:
                report['environment']['python'] = 'different'
            pair.dump(path, report)
    with pytest.raises((ValueError, FileNotFoundError)):
        repeats.summarize(out)


def test_failed_run_remains_failed_and_never_overwrites(repeats, pair, data, tmp_path, monkeypatch):
    reference, out, _ = prepare(repeats, pair, data, tmp_path, monkeypatch, failure='worker failed')
    before = repeats.evidence_hashes(reference)
    with pytest.raises(RuntimeError, match='worker failed'):
        repeats.run(tmp_path, data, out, reference=reference, provenance_label='development-reference')
    assert pair.read(out/'status.json')['status'] == 'failed'
    assert pair.read(out/'protocol.json')['seeds'] == list(SEEDS)
    assert pair.read(out/'original-before.json') == pair.read(out/'original-after.json')
    assert repeats.evidence_hashes(reference) == before
    with pytest.raises(ValueError, match='completed'):
        repeats.summarize(out)
    with pytest.raises(FileExistsError):
        repeats.run(tmp_path, data, out, reference=reference, provenance_label='development-reference')


def test_each_image_keeps_its_own_effect_instead_of_the_macro_effect(repeats, pair, data, tmp_path, monkeypatch):
    """One different saved image must affect only that image's paired summary."""
    import numpy as np
    reference, out, _ = prepare(repeats, pair, data, tmp_path, monkeypatch)
    original = repeats.run(tmp_path, data, out, reference=reference, provenance_label='development-reference')
    folder = out/'pairs/20261117/small_vit_refined'
    report = pair.read(folder/'training.json')
    first = report['validation']['rows'][0]
    np.save(folder/first['prediction'], np.zeros((256, 256), np.float32))
    first['prediction_sha256'] = pair.sha(folder/first['prediction'])
    for metric in first['metrics'].values():
        metric.update(tp=0, fp=0, fn=metric['pixels'], dice=0., iou=0., precision=0., recall=0.)
    report['validation']['macro_dice'] = {
        region: statistics.mean(row['metrics'][region]['dice'] for row in report['validation']['rows'])
        for region in REGIONS}
    macro = report['validation']['macro_dice']['all']
    report['best_validation_dice'] = macro
    for epoch in report['history']:
        epoch['validation_dice'] = {str(threshold): macro for threshold in (.35, .5, .65)}
    pair.dump(folder/'training.json', report)
    pair.dump(folder/'history.json', report['history'])
    audited = repeats.summarize(out)
    for region in REGIONS:
        changed = audited['per_image_effects'][0]
        assert changed['paired_deltas'][region]['values'][1] == -changed['seed_rows'][1]['baseline_dice'][region]
        assert changed['paired_deltas'][region]['values'][1] != audited['paired_deltas'][region]['values'][1]
    assert audited['per_image_effects'][1:] == original['per_image_effects'][1:]
