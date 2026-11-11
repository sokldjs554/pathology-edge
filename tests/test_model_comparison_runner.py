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
