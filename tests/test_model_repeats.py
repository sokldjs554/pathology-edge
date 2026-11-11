"""Repeat evidence must come from three complete, scientifically matched pairs."""
import importlib.util
from pathlib import Path
import shutil
import statistics

import numpy as np
from PIL import Image
import pytest

ROOT = Path(__file__).parents[1]
SEEDS = [20261113, 20261114, 20261115]
ARCHITECTURES = ('tiny_unet', 'small_vit')
REGIONS = ('all', 'boundary', 'interior')


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT/'scripts'/f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def pair():
    return load_script('run_model_comparison')


@pytest.fixture
def repeats():
    path = ROOT/'scripts/run_model_repeats.py'
    assert path.exists(), 'The repeat orchestrator is not implemented'
    return load_script('run_model_repeats')


@pytest.fixture
def data(tmp_path, pair):
    root = tmp_path/'data'
    root.mkdir()
    Image.fromarray(np.ones((256, 256), np.uint8)*255).save(root/'pixels.png')
    digest = pair.sha(root/'pixels.png')
    records = [dict(id=f'{split}-{i}', group_id=f'g-{i}', split=split,
                    image='pixels.png', mask='pixels.png', image_sha256=digest, mask_sha256=digest)
               for split, count in [('train', 33), ('validation', 10), ('test', 7)]
               for i in range(count)]
    pair.dump(root/'manifest.json', dict(records=records))
    return root


def completed_pair(pair, out, data, seed=20261113, order=ARCHITECTURES, missing_rows=(0, 2)):
    """Write minimal complete evidence; no model is trained or loaded."""
    source = out/'source/pathology_edge'
    source.mkdir(parents=True)
    for name in ('__init__.py', 'learner_losses.py', 'model_comparison.py'):
        (source/name).write_text('# fixture source\n')
    (out/'runner.py').write_text('# historical runner; never execute\n')
    state = dict(commit='abc', status='', hashes={'example': 'preserved'})
    pair.dump(out/'original-before.json', state)
    pair.dump(out/'original-after.json', state)
    pair.dump(out/'status.json', dict(status='completed', all_checks_passed=True))
    manifest = pair.read(data/'manifest.json')
    config = dict(seed=seed, epochs=16, steps_per_epoch=20, batch_size=8, crop=128,
                  optimizer='Adam', learning_rate=.001, loss='BCE + learner soft Dice', loss_mode='learner_dice',
                  loss_source_sha256=pair.sha(source/'learner_losses.py'),
                  augmentations=['horizontal/vertical flip', '90 degree rotations'],
                  thresholds=[.35, .5, .65], validation_mode='no_overlap', patch_size=128,
                  overlap=0, seam_radius=8, min_component_area=12, torch_threads=4,
                  selection='maximum validation image-macro Dice over epochs and thresholds; first tie',
                  test_used_for_selection=False, pretrained=False, manifest_sha256=pair.sha(data/'manifest.json'))
    boundary = np.zeros((256, 256), bool)
    boundary[120:136, :] = boundary[:, 120:136] = True
    source_hashes = {p.name: pair.sha(p) for p in source.glob('*.py')}
    for architecture, parameters, missing in zip(ARCHITECTURES, (29761, 33632), missing_rows):
        folder = out/architecture
        (folder/'predictions').mkdir(parents=True)
        probability = np.ones((256, 256), np.float32)
        probability[:missing, :] = 0
        metrics = {}
        for region, mask in [('all', np.ones((256, 256), bool)), ('boundary', boundary), ('interior', ~boundary)]:
            tp = int((probability[mask] > .35).sum())
            fn, pixels = int(mask.sum())-tp, int(mask.sum())
            metrics[region] = dict(tp=tp, fp=0, fn=fn, pixels=pixels, dice=2*tp/(2*tp+fn),
                                   iou=tp/(tp+fn), precision=1., recall=tp/(tp+fn))
        rows = []
        for i, item in enumerate(r for r in manifest['records'] if r['split'] == 'validation'):
            prediction = folder/'predictions'/f'{i:02d}.npy'
            np.save(prediction, probability, allow_pickle=False)
            rows.append(dict(id=item['id'], group_id=item['group_id'], prediction=f'predictions/{i:02d}.npy',
                             prediction_sha256=pair.sha(prediction), metrics=metrics,
                             timings_seconds=[1., 2., 3.], median_seconds=2.))
        macros = {r: metrics[r]['dice'] for r in REGIONS}
        history = [dict(epoch=i, train_loss=.5, validation_dice={str(t): macros['all'] for t in [.35, .5, .65]})
                   for i in range(1, 17)]
        (folder/'model.pt').write_bytes(b'opaque fixture checkpoint')
        report = dict(architecture=architecture, parameter_count=parameters, config=config, history=history,
                      train_images=33, validation_images=10, best_validation_dice=macros['all'], best_epoch=1,
                      threshold=.35, test_evaluation_run=False, model_sha256=pair.sha(folder/'model.pt'),
                      seconds=12., peak_process_rss_mib=128., augmentation_trace_sha256=f'trace-{seed}',
                      environment=dict(python='test', torch_threads=4),
                      validation=dict(rows=rows, macro_dice=macros, median_image_seconds=2.))
        for filename, value in [('protocol.json', config), ('source-hashes.json', source_hashes),
                                ('manifest.json', manifest), ('history.json', history), ('training.json', report)]:
            pair.dump(folder/filename, value)
    pair.dump(out/'protocol.json', dict(seed=seed, architectures=list(order), data=str(data),
              source_commit='abc', source_dirty=False, manifest_sha256=config['manifest_sha256'],
              snapshot_hashes=pair.snapshot_hashes(out)))
    return out


def test_pair_accepts_relocated_data_without_rewriting_plan(pair, data, tmp_path):
    run = completed_pair(pair, tmp_path/'pair', data, seed=20261114, order=ARCHITECTURES[::-1])
    original = (run/'protocol.json').read_bytes()
    relocated = tmp_path/'relocated'
    data.rename(relocated)
    summary = pair.summarize(run, data_override=relocated)
    assert summary['seed'] == 20261114
    assert summary['architecture_order'] == list(ARCHITECTURES[::-1])
    assert summary['validation_metric_regions_checked'] == 60
    assert (run/'protocol.json').read_bytes() == original


@pytest.mark.parametrize('mutation', ['seed', 'order', 'source', 'data', 'protocol', 'missing', 'environment'])
def test_pair_rejects_inconsistent_evidence(pair, data, tmp_path, mutation):
    run = completed_pair(pair, tmp_path/'pair', data)
    if mutation == 'seed':
        plan = pair.read(run/'protocol.json'); plan['seed'] += 1; pair.dump(run/'protocol.json', plan)
    elif mutation == 'order':
        plan = pair.read(run/'protocol.json'); plan['architectures'] *= 2; pair.dump(run/'protocol.json', plan)
    elif mutation == 'source':
        (run/'source/pathology_edge/model_comparison.py').write_text('# changed\n')
    elif mutation == 'data':
        (data/'pixels.png').write_bytes(b'changed')
    elif mutation == 'missing':
        (run/'small_vit/training.json').unlink()
    else:
        report = pair.read(run/'small_vit/training.json')
        if mutation == 'protocol':
            report['config']['torch_threads'] = 8
            pair.dump(run/'small_vit/protocol.json', report['config'])
        else:
            report['environment']['python'] = 'different'
        pair.dump(run/'small_vit/training.json', report)
    with pytest.raises((ValueError, FileNotFoundError)):
        pair.summarize(run, data_override=data)


def prepare_repeats(repeats, pair, data, tmp_path, monkeypatch, *, failure=None):
    baseline = completed_pair(pair, tmp_path/'baseline', data)
    state = dict(commit='current', status='', hashes={'tracked': 'original'})
    monkeypatch.setattr(repeats.pair, 'original_state', lambda repo: state)
    monkeypatch.setattr(repeats, 'worker_environment', lambda source, cwd: dict(python='test', torch_threads=4))
    calls = []
    def fake_run(repo, data, output, *, seed, architecture_order, source_snapshot):
        calls.append((seed, architecture_order))
        if failure:
            raise RuntimeError(failure)
        completed_pair(pair, output, data, seed=seed, order=architecture_order,
                       missing_rows={20261114: (3, 1), 20261115: (2, 2)}[seed])
        shutil.copy2(repeats.pair.__file__, output/'runner.py')
        plan = pair.read(output/'protocol.json'); plan['snapshot_hashes'] = pair.snapshot_hashes(output)
        pair.dump(output/'protocol.json', plan)
        return pair.summarize(output)
    monkeypatch.setattr(repeats.pair, 'run', fake_run)
    out = tmp_path/'work'/'repeats'
    return baseline, out, calls


def test_repeats_reuses_baseline_and_aggregates_all_six_arms(repeats, pair, data, tmp_path, monkeypatch):
    baseline, out, calls = prepare_repeats(repeats, pair, data, tmp_path, monkeypatch)
    baseline_bytes = (baseline/'protocol.json').read_bytes()
    summary = repeats.run(tmp_path, data, out, baseline=baseline, provenance_label='development-reference')
    assert calls == [(20261114, ARCHITECTURES[::-1]), (20261115, ARCHITECTURES)]
    assert summary['seeds'] == SEEDS and len(summary['rows']) == 6
    assert summary['validation_metric_regions_checked'] == 180
    assert summary['provenance_label'] == 'development-reference'
    for region in REGIONS:
        deltas = [p['delta_vit_minus_cnn'][region] for p in summary['pairs']]
        aggregate = summary['paired_deltas'][region]
        assert aggregate['values'] == deltas
        assert aggregate['mean'] == statistics.mean(deltas)
        assert aggregate['sample_sd'] == statistics.stdev(deltas)
        assert (aggregate['wins'], aggregate['ties'], aggregate['losses']) == (1, 1, 1)
        for architecture in ARCHITECTURES:
            values = [r['validation_dice'][region] for r in summary['rows'] if r['architecture'] == architecture]
            assert summary['architectures'][architecture][region]['sample_sd'] == statistics.stdev(values)
    assert (baseline/'protocol.json').read_bytes() == baseline_bytes
    # Whole repeat bundle and data relocate independently; no historic path is rewritten.
    relocated = tmp_path/'relocated-data'; data.rename(relocated)
    moved = tmp_path/'moved-repeats'; out.rename(moved)
    assert repeats.summarize(moved, data_override=relocated)['paired_deltas'] == summary['paired_deltas']


@pytest.mark.parametrize('change', ['duplicate_seed', 'environment', 'source', 'protocol', 'failed', 'missing_pair', 'snapshot'])
def test_repeat_summary_refuses_mismatched_or_incomplete_pairs(repeats, pair, data, tmp_path, monkeypatch, change):
    baseline, out, _ = prepare_repeats(repeats, pair, data, tmp_path, monkeypatch)
    repeats.run(tmp_path, data, out, baseline=baseline, provenance_label='development-reference')
    run = out/'pairs'/'20261114'
    if change == 'duplicate_seed':
        plan = pair.read(out/'protocol.json'); plan['seeds'][1] = SEEDS[0]; pair.dump(out/'protocol.json', plan)
    elif change == 'failed':
        pair.dump(run/'status.json', dict(status='failed', all_checks_passed=True))
    elif change == 'missing_pair':
        shutil.rmtree(run)
    elif change == 'snapshot':
        (out/'pair-runner.py').write_text('# tampered\n')
    elif change == 'source':
        target = run/'source/pathology_edge/model_comparison.py'; target.write_text('# different source\n')
        plan = pair.read(run/'protocol.json'); plan['snapshot_hashes'] = pair.snapshot_hashes(run)
        pair.dump(run/'protocol.json', plan)
        for architecture in ARCHITECTURES:
            hashes = pair.read(run/architecture/'source-hashes.json'); hashes[target.name] = pair.sha(target)
            pair.dump(run/architecture/'source-hashes.json', hashes)
    else:
        for architecture in ARCHITECTURES:
            path = run/architecture/'training.json'; report = pair.read(path)
            if change == 'environment':
                report['environment']['python'] = 'different'
            else:
                report['config']['augmentations'] = ['different']
                pair.dump(run/architecture/'protocol.json', report['config'])
            pair.dump(path, report)
    with pytest.raises((ValueError, FileNotFoundError)):
        repeats.summarize(out)


def test_repeat_failure_stays_failed_and_existing_output_is_preserved(repeats, pair, data, tmp_path, monkeypatch):
    baseline, out, _ = prepare_repeats(repeats, pair, data, tmp_path, monkeypatch, failure='worker failed')
    with pytest.raises(RuntimeError, match='worker failed'):
        repeats.run(tmp_path, data, out, baseline=baseline, provenance_label='development-reference')
    assert pair.read(out/'status.json')['status'] == 'failed'
    assert pair.read(out/'protocol.json')['seeds'] == SEEDS
    assert pair.read(out/'original-before.json') == pair.read(out/'original-after.json')
    assert (out/'pairs/20261113/tiny_unet/model.pt').exists()
    with pytest.raises(ValueError, match='completed'):
        repeats.summarize(out)
    with pytest.raises(FileExistsError):
        repeats.run(tmp_path, data, out, baseline=baseline, provenance_label='development-reference')


def test_repeat_environment_preflight_rejects_before_training(repeats, pair, data, tmp_path, monkeypatch):
    baseline, out, calls = prepare_repeats(repeats, pair, data, tmp_path, monkeypatch)
    monkeypatch.setattr(repeats, 'worker_environment', lambda source, cwd: dict(python='other', torch_threads=4))
    with pytest.raises(ValueError, match='environment'):
        repeats.run(tmp_path, data, out, baseline=baseline, provenance_label='development-reference')
    assert not calls
    assert pair.read(out/'status.json')['status'] == 'failed'
