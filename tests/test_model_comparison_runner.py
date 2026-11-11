"""The runner must fail closed and preserve source/results, including under -O."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

SCRIPT = Path(__file__).parents[1] / 'scripts/run_model_comparison.py'


@pytest.fixture
def runner():
    spec = importlib.util.spec_from_file_location('model_runner', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_require_is_active_when_optimized(tmp_path):
    code = ('import runpy; m=runpy.run_path(' + repr(str(SCRIPT)) + '); '
            'm["require"](False,"intentional invalid input")')
    result = subprocess.run([sys.executable, '-O', '-c', code], capture_output=True, text=True)
    assert result.returncode != 0
    assert 'intentional invalid input' in result.stderr


def test_snapshot_checks_unlisted_source_and_mutated_runner(runner, tmp_path):
    source = tmp_path / 'source/pathology_edge'
    source.mkdir(parents=True)
    (source / '__init__.py').write_text('')
    (tmp_path / 'runner.py').write_text('# runner\n')
    frozen = runner.snapshot_hashes(tmp_path)
    runner.verify_snapshot(tmp_path, frozen)
    (source / 'injected.py').write_text('x=1')
    with pytest.raises(ValueError, match='snapshot'):
        runner.verify_snapshot(tmp_path, frozen)
    (source / 'injected.py').unlink()
    (tmp_path / 'runner.py').write_text('changed')
    with pytest.raises(ValueError, match='snapshot'):
        runner.verify_snapshot(tmp_path, frozen)


def test_failed_worker_keeps_stdout_and_nonzero_exit(runner, tmp_path):
    log = tmp_path / 'train.log'
    with pytest.raises(subprocess.CalledProcessError):
        runner.execute([sys.executable, '-c', 'print("before failure"); raise RuntimeError("failure")'],
                       cwd=tmp_path, env=None, log=log)
    assert 'before failure' in log.read_text()
    assert 'RuntimeError: failure' in log.read_text()


def test_invalid_output_never_overwrites(runner, tmp_path):
    out = tmp_path / 'existing'
    out.mkdir()
    model = out / 'model.pt'
    model.write_bytes(b'original')
    with pytest.raises(FileExistsError):
        runner.run(tmp_path, tmp_path, out)
    assert model.read_bytes() == b'original'


def test_summary_rejects_incomplete_run(runner, tmp_path):
    (tmp_path / 'protocol.json').write_text(json.dumps({}))
    with pytest.raises((ValueError, KeyError, FileNotFoundError)):
        runner.summarize(tmp_path)


@pytest.mark.parametrize('seed,order', [(0, ('tiny_unet', 'small_vit')),
                                      (True, ('tiny_unet', 'small_vit')),
                                      (20261114, ('tiny_unet', 'tiny_unet'))])
def test_run_rejects_invalid_seed_or_order_before_writes(runner, tmp_path, seed, order):
    out = tmp_path/'work'/'new'
    with pytest.raises(ValueError, match='seed|architecture'):
        runner.run(tmp_path, tmp_path/'data', out, seed=seed, architecture_order=order)
    assert not out.exists()


def test_run_freezes_actual_seed_and_order_and_preserves_failure(runner, tmp_path, monkeypatch):
    source = tmp_path/'src/pathology_edge'
    source.mkdir(parents=True)
    (source/'__init__.py').write_text('')
    data = tmp_path/'data'
    data.mkdir()
    (data/'manifest.json').write_text('{}')
    state = dict(commit='abc', status='', hashes={})
    monkeypatch.setattr(runner, 'original_state', lambda repo: state)
    commands = []
    def failed(command, **kwargs):
        commands.append(command)
        raise RuntimeError('worker failed')
    monkeypatch.setattr(runner, 'execute', failed)
    out = tmp_path/'work'/'new'
    order = ('small_vit', 'tiny_unet')
    with pytest.raises(RuntimeError, match='worker failed'):
        runner.run(tmp_path, data, out, seed=20261114, architecture_order=order)
    plan = runner.read(out/'protocol.json')
    assert plan['seed'] == 20261114
    assert plan['architectures'] == list(order)
    assert '20261114' in commands[0] and 'small_vit' in commands[0]
    assert runner.read(out/'status.json')['status'] == 'failed'
    assert runner.read(out/'original-before.json') == runner.read(out/'original-after.json')


def test_worker_cli_passes_explicit_seed(monkeypatch, tmp_path):
    from pathology_edge import model_comparison
    calls = []
    monkeypatch.setattr(model_comparison, 'train_one', lambda *args, **kwargs: calls.append((args, kwargs)))
    monkeypatch.setattr(sys, 'argv', ['model_comparison', '--data', str(tmp_path/'data'),
                                    '--output', str(tmp_path/'run'), '--architecture', 'small_vit',
                                    '--seed', '20261115'])
    model_comparison.main()
    assert calls == [((tmp_path/'data', tmp_path/'run', 'small_vit'), {'seed': 20261115})]


@pytest.mark.parametrize('status,preserved', [('failed', True), ('completed', False), ('running', True)])
def test_summary_cannot_turn_failed_or_changed_run_into_success(runner, tmp_path, status, preserved):
    state = dict(commit='abc', status='', hashes={'file': 'original'})
    (tmp_path / 'original-before.json').write_text(json.dumps(state))
    after = state if preserved else dict(state, hashes={'file': 'modified'})
    (tmp_path / 'original-after.json').write_text(json.dumps(after))
    (tmp_path / 'status.json').write_text(json.dumps(dict(status=status, all_checks_passed=True)))
    (tmp_path / 'protocol.json').write_text(json.dumps(dict(source_commit='abc', source_dirty=False)))
    # No model files exist: state validation must fail before attempting result audits.
    with pytest.raises(ValueError, match='completed|Original'):
        runner.summarize(tmp_path)


@pytest.mark.parametrize('change', ['pixels', 'metric', 'timing', 'mean'])
def test_independent_pixel_audit_detects_tampering(runner, tmp_path, change):
    import numpy as np
    from PIL import Image
    folder = tmp_path / 'run'
    (folder / 'predictions').mkdir(parents=True)
    image = np.ones((256, 256), np.uint8)
    Image.fromarray(image*255).save(tmp_path/'mask.png')
    pred = folder/'predictions/00.npy'
    np.save(pred, image.astype(np.float32))
    metric = lambda pixels: dict(tp=pixels, fp=0, fn=0, pixels=pixels, dice=1., iou=1., precision=1., recall=1.)
    row = dict(id='v', group_id='g', prediction='predictions/00.npy', prediction_sha256=runner.sha(pred),
               metrics=dict(all=metric(65536), boundary=metric(7936), interior=metric(57600)),
               timings_seconds=[1., 2., 3.], median_seconds=2.)
    report = dict(threshold=.5, validation=dict(rows=[row], macro_dice=dict(all=1., boundary=1., interior=1.), median_image_seconds=2.))
    manifest = dict(records=[dict(id='v', group_id='g', split='validation', mask='mask.png')])
    runner.audit_predictions(folder, report, tmp_path, manifest)
    if change == 'pixels':
        np.save(pred, np.zeros((256, 256), np.float32))
        row['prediction_sha256'] = runner.sha(pred)  # metric check, not just file hash
    elif change == 'metric':
        row['metrics']['boundary']['dice'] = .9
    elif change == 'timing':
        row['timings_seconds'][0] = float('nan')
    else:
        report['validation']['macro_dice']['all'] = .9
    with pytest.raises(ValueError):
        runner.audit_predictions(folder, report, tmp_path, manifest)


@pytest.mark.parametrize('seed,order', [
    (20261113, ('small_vit', 'small_vit_refined')),
    (20261116, ('tiny_unet', 'small_vit')),
    (20261116, ('small_vit_refined', 'small_vit_refined')),
])
def test_refinement_design_rejects_other_seed_or_pair_before_writes(runner, tmp_path, seed, order):
    out = tmp_path/'work'/'new'
    with pytest.raises(ValueError, match='seed|architecture'):
        runner.run(tmp_path, tmp_path/'data', out, comparison='refinement',
                   seed=seed, architecture_order=order)
    assert not out.exists()


def test_unimplemented_head_prevents_baseline_training_and_preserves_dirty_source(runner, tmp_path, monkeypatch):
    import shutil
    source = tmp_path/'src/pathology_edge'
    shutil.copytree(SCRIPT.parents[1]/'src/pathology_edge', source,
                    ignore=shutil.ignore_patterns('__pycache__', '*.so'))
    # A deliberately incomplete learner; never supplies the exercise answer.
    (source/'learner_refinement.py').write_text(
        'from torch import nn\n'
        'class LocalResidualHead(nn.Module):\n'
        '    def __init__(self):\n'
        '        raise NotImplementedError("learner head pending")\n')
    data = tmp_path/'data'
    data.mkdir()
    (data/'manifest.json').write_text('{}')
    state = dict(commit='abc', status=' M src/pathology_edge/learner_refinement.py\n',
                 hashes={'src/pathology_edge/learner_refinement.py': runner.sha(source/'learner_refinement.py')})
    monkeypatch.setattr(runner, 'original_state', lambda repo: state)
    out = tmp_path/'work'/'new'
    with pytest.raises(subprocess.CalledProcessError):
        runner.run(tmp_path, data, out, comparison='refinement', seed=20261116)
    assert not (out/'small_vit').exists() and not (out/'small_vit_refined').exists()
    assert 'NotImplementedError: learner head pending' in (out/'refinement-preflight.log').read_text()
    assert runner.read(out/'status.json')['status'] == 'failed'
    assert runner.read(out/'original-before.json') == runner.read(out/'original-after.json') == state
    with pytest.raises(ValueError, match='completed'):
        runner.summarize(out)
    with pytest.raises(FileExistsError):
        runner.run(tmp_path, data, out, comparison='refinement', seed=20261116)
