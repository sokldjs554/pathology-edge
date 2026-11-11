"""Reject misleading benchmark evidence and protect the user's existing checkout."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/benchmark_cpp_review.py'


def runner():
    assert SCRIPT.is_file(), 'Standalone C++ review runner is not implemented'
    spec = importlib.util.spec_from_file_location('benchmark_cpp_review', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def repo(tmp_path):
    path = tmp_path / 'repo'
    (path / 'src/pathology_edge').mkdir(parents=True)
    (path / 'artifacts').mkdir()
    (path / '.gitignore').write_text('work/\n')
    (path / 'src/pathology_edge/learner_wsi.py').write_text('exercise = None\n')
    (path / 'artifacts/benchmark.json').write_text('{"existing": true}\n')
    subprocess.run(['git', 'init', '-q', str(path)], check=True)
    subprocess.run(['git', 'add', '.'], cwd=path, check=True)
    subprocess.run(['git', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                    'commit', '-qm', 'fixture'], cwd=path, check=True)
    (path / 'src/pathology_edge/learner_wsi.py').write_text('my_solution = 42\n')
    return path


@pytest.mark.parametrize('optimized', [False, True])
def test_parity_mismatch_stops_worker_even_with_python_optimization(optimized):
    runner()
    # Mutate a real extractor's result, then exercise the real timing worker.
    code = '''
import importlib.util
import sys
from pathology_edge import patches
spec = importlib.util.spec_from_file_location('review', sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
original = patches.extract
def corrupted(image, patches, backend='python', threads=1):
    result = original(image, patches, 'python', 1)
    if backend == 'cpp':
        result[0, 0, 0, 0] ^= 1
    return result
patches.extract = corrupted
module.measure_case(128, 'cpp', 1)
'''
    env = dict(os.environ, PYTHONPATH=str(ROOT / 'src'))
    command = [sys.executable] + (['-O'] if optimized else [])
    result = subprocess.run(command + ['-c', code, str(SCRIPT)], env=env,
                            capture_output=True, text=True)
    assert result.returncode != 0
    assert 'parity' in result.stderr.lower()


def valid_row():
    return dict(size=512, backend='cpp', threads=2, patch_count=64,
                measurements_ms=[1.0] * 9, median_ms=1.0,
                peak_process_rss_mib=128.0, sha256='a' * 64,
                equal_to_python=True, dtype='uint8', output_shape=[64, 128, 128, 3])


@pytest.mark.parametrize('change', [
    {'measurements_ms': []}, {'measurements_ms': [1.0] * 8},
    {'measurements_ms': [float('nan')] * 9}, {'median_ms': float('inf')},
    {'peak_process_rss_mib': -1}, {'equal_to_python': False},
    {'threads': 4}, {'patch_count': 0}, {'sha256': 'not-a-digest'},
    {'output_shape': [64, 127, 128, 3]}, {'dtype': 'float32'},
])
def test_incomplete_nonfinite_or_wrong_case_result_is_rejected(change):
    module = runner()
    row = valid_row()
    row.update(change)
    with pytest.raises(ValueError):
        module.validate_row(row, (512, 'cpp', 2))


@pytest.mark.parametrize('payload', ['', '[]', '{}', 'null', '{"median_ms": NaN}', 'not json'])
def test_malformed_worker_output_cannot_be_reported_as_success(tmp_path, payload):
    module = runner()
    stdout = tmp_path / 'worker.stdout.log'
    stdout.write_text(payload)
    with pytest.raises(ValueError):
        module.read_worker_result(stdout, (512, 'cpp', 2))
    assert stdout.read_text() == payload


def test_valid_result_and_complete_review_are_accepted():
    module = runner()
    module.validate_row(valid_row(), (512, 'cpp', 2))
    rows = []
    for size in (512, 2048):
        for backend, threads in [('python', 1), ('cpp', 1), ('cpp', 2), ('cpp', 4)]:
            row = valid_row()
            row.update(size=size, backend=backend, threads=threads, round=1,
                       patch_count=64 if size == 512 else 1024,
                       output_shape=[64 if size == 512 else 1024, 128, 128, 3])
            rows.append(row)
    summary = module.summarize(rows, rounds=1)
    assert len(summary) == 8
    assert all(row['speedup_vs_python'] == 1.0 for row in summary)
    for invalid in ([], rows[:-1], rows + [copy.deepcopy(rows[0])]):
        with pytest.raises(ValueError):
            module.summarize(invalid, rounds=1)
    rows[-1]['sha256'] = 'b' * 64
    with pytest.raises(ValueError, match='digest'):
        module.summarize(rows, rounds=1)


def test_failed_review_preserves_user_source_existing_artifact_and_logs(repo, monkeypatch):
    module = runner()
    learner = repo / 'src/pathology_edge/learner_wsi.py'
    artifact = repo / 'artifacts/benchmark.json'
    before = (learner.read_bytes(), artifact.read_bytes())
    def fail(_repo, output, _rounds, _rows):
        (output / 'worker.stderr.log').write_text('specific worker failure\n')
        raise RuntimeError('specific worker failure')
    monkeypatch.setattr(module, 'run_cases', fail)
    output, report = module.execute(repo)
    assert report['all_checks_passed'] is False
    assert report['original_files_preserved'] is True
    assert 'specific worker failure' in report['error']
    assert (learner.read_bytes(), artifact.read_bytes()) == before
    assert (output / 'worker.stderr.log').read_text() == 'specific worker failure\n'
    assert json.loads((output / 'summary.json').read_text()) == report
    assert (output / 'RUN.txt').is_file()


def test_source_change_during_review_forces_failure(repo, monkeypatch):
    module = runner()
    def damage(_repo, _output, _rounds, _rows):
        (repo / 'src/pathology_edge/learner_wsi.py').write_text('unexpected change\n')
        raise RuntimeError('interrupted')
    monkeypatch.setattr(module, 'run_cases', damage)
    _, report = module.execute(repo)
    assert report['all_checks_passed'] is False
    assert report['original_files_preserved'] is False


def test_new_runs_are_fresh_and_explicit_rerun_never_overwrites(repo, monkeypatch):
    module = runner()
    def fail(*_args):
        raise RuntimeError('stop before expensive measurement')
    monkeypatch.setattr(module, 'run_cases', fail)
    first, _ = module.execute(repo)
    second, _ = module.execute(repo)
    assert first != second
    assert first.parent == second.parent == repo / 'work'
    saved = (first / 'summary.json').read_bytes()
    with pytest.raises(FileExistsError):
        module.execute(repo, output=first)
    assert (first / 'summary.json').read_bytes() == saved


def test_failed_worker_keeps_stdout_stderr_and_nonzero_exit(tmp_path):
    module = runner()
    command = [sys.executable, '-c',
               'import sys; print("before failure"); print("worker broken", file=sys.stderr); sys.exit(7)']
    with pytest.raises(RuntimeError, match='7'):
        module.run_worker(command, tmp_path, os.environ.copy(), tmp_path, 'failure')
    assert 'before failure' in (tmp_path / 'failure.stdout.log').read_text()
    assert 'worker broken' in (tmp_path / 'failure.stderr.log').read_text()


def test_downloaded_runner_rejects_an_import_from_another_checkout(repo):
    runner()
    # The copied runner has no adjacent project helpers; it must remain standalone.
    downloaded = repo / 'work/download/benchmark_cpp_review.py'
    downloaded.parent.mkdir(parents=True)
    downloaded.write_bytes(SCRIPT.read_bytes())
    env = dict(os.environ, PYTHONPATH=str(ROOT / 'src'))
    result = subprocess.run([sys.executable, '-O', str(downloaded), '--repo', str(repo)],
                            cwd=repo, env=env, capture_output=True, text=True)
    assert result.returncode == 1
    runs = list((repo / 'work').glob('my-cpp-review.*'))
    assert len(runs) == 1
    report = json.loads((runs[0] / 'summary.json').read_text())
    assert report['all_checks_passed'] is False
    assert report['original_files_preserved'] is True
    assert 'Imports must come from the original repository' in report['error']
    assert (runs[0] / 'failure.log').is_file()
    assert (repo / 'src/pathology_edge/learner_wsi.py').read_text() == 'my_solution = 42\n'


def test_ignored_compiled_binary_is_frozen_and_changes_are_detected(repo, monkeypatch):
    module = runner()
    with (repo / '.gitignore').open('a') as stream:
        stream.write('*.so\n')
    binary = repo / 'src/pathology_edge/_patch_cpp.fixture.so'
    binary.write_bytes(b'original compiled extension')
    def replace_binary(_repo, _output, _rounds, _rows):
        binary.write_bytes(b'replaced compiled extension')
        raise RuntimeError('binary changed')
    monkeypatch.setattr(module, 'run_cases', replace_binary)
    output, report = module.execute(repo)
    assert report['original_files_preserved'] is False
    assert report['all_checks_passed'] is False
    assert (output / 'frozen-source/src/pathology_edge/_patch_cpp.fixture.so').read_bytes() == (
        b'original compiled extension')
