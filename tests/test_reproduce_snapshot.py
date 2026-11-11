"""Protect original edits and reject incomplete reproduction evidence."""
import importlib.util
import json
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]


def runner():
    path = ROOT / 'scripts/reproduce_snapshot.py'
    assert path.is_file(), 'Snapshot reproduction helper has not been implemented'
    spec = importlib.util.spec_from_file_location('reproduce_snapshot', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def repo(tmp_path):
    repo = tmp_path / 'repo'
    repo.mkdir()
    subprocess.run(['git', 'init', '-q', str(repo)], check=True)
    (repo / 'src/pathology_edge').mkdir(parents=True)
    user_file = repo / 'src/pathology_edge/learner_wsi.py'
    user_file.write_text('original = 1\n')
    (repo / '.gitignore').write_text('work/\n')
    subprocess.run(['git', 'add', '.'], cwd=repo, check=True)
    subprocess.run(['git', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                    'commit', '-qm', 'fixture'], cwd=repo, check=True)
    user_file.write_text('user_implementation = 2\n')
    return repo


def test_failed_execution_keeps_user_edits_and_failure_log(repo, monkeypatch):
    module = runner()
    before = module.original_state(repo)
    def failure(source, output):
        (output / 'build.log').write_text('compiler failure\n')
        raise RuntimeError('fixture compiler failure')
    monkeypatch.setattr(module, 'reproduce', failure)
    output, report = module.execute(repo)
    assert report['all_checks_passed'] is False
    assert report['original_files_preserved'] is True
    assert 'fixture compiler failure' in report['error']
    assert module.original_state(repo) == before
    assert (output / 'original-source/pathology_edge/learner_wsi.py').read_bytes() == (
        repo / 'src/pathology_edge/learner_wsi.py').read_bytes()
    assert (output / 'build.log').read_text() == 'compiler failure\n'
    assert json.loads((output / 'summary.json').read_text()) == report


def test_changed_original_cannot_be_reported_as_success(repo, monkeypatch):
    module = runner()
    def damage(source, output):
        (source / 'src/pathology_edge/learner_wsi.py').write_text('changed\n')
        return {'checks': 'fixture'}
    monkeypatch.setattr(module, 'reproduce', damage)
    _, report = module.execute(repo)
    assert report['all_checks_passed'] is False
    assert report['original_files_preserved'] is False


@pytest.mark.parametrize('tests,skipped,failures,errors', [
    (191, 1, 0, 0), (191, 0, 1, 0), (191, 0, 0, 1), (190, 0, 0, 0), (0, 0, 0, 0)])
def test_incomplete_or_skipped_suite_is_rejected(tmp_path, tests, skipped, failures, errors):
    module = runner()
    xml = tmp_path / 'tests.xml'
    xml.write_text(f'<testsuites><testsuite tests="{tests}" skipped="{skipped}" '
                   f'failures="{failures}" errors="{errors}"/></testsuites>')
    with pytest.raises(ValueError, match='191'):
        module.check_suite(xml)


def test_complete_suite_has_exact_counts(tmp_path):
    module = runner()
    xml = tmp_path / 'tests.xml'
    xml.write_text('<testsuites><testsuite tests="191" skipped="0" failures="0" errors="0"/></testsuites>')
    assert module.check_suite(xml) == dict(tests=191, skipped=0, failures=0, errors=0)


def test_stage_failure_keeps_subprocess_output(tmp_path):
    import os
    import sys
    module = runner()
    with pytest.raises(RuntimeError, match='failure.log'):
        module.stage('failure', [sys.executable, '-c', 'print("specific error"); raise SystemExit(3)'],
                     tmp_path, os.environ.copy(), tmp_path)
    assert 'specific error' in (tmp_path / 'failure.log').read_text()


def test_optimized_parent_cannot_disable_child_validation(tmp_path, monkeypatch):
    import subprocess
    import sys
    module = runner()
    monkeypatch.setenv('PYTHONOPTIMIZE', '1')
    assert hasattr(module, 'verification_environment'), 'Child validation environment is not isolated'
    env = module.verification_environment(tmp_path / 'source', tmp_path)
    result = subprocess.run([sys.executable, '-c', 'assert False, "validation active"'],
                            env=env, capture_output=True, text=True)
    assert result.returncode != 0
    assert 'validation active' in result.stderr
