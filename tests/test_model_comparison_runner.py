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
