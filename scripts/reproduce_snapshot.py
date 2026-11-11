"""STEP_45: verify a pinned checkout using existing packages, without reinstalling.

Run from the user's original repository. Writes only to a fresh work directory.
The checkout contains reviewed code; the original uncommitted file is backed up
and preserved, not substituted into the pinned revision being tested.
"""
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

SOURCE_COMMIT = '9c55480fc721d23160016e1c472b9bdcc8f8eb21'
REMOTE = 'https://github.com/sokldjs554/pathology-edge.git'
EXPECTED_TESTS = 191


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def git(repo, *args):
    return subprocess.check_output(['git', *args], cwd=repo, text=True).strip()


def original_state(repo):
    tracked = git(repo, 'ls-files', '-z').split('\0')
    names = set(filter(None, tracked))
    names.update(p.relative_to(repo).as_posix() for p in (repo / 'src').rglob('*.py'))
    return dict(commit=git(repo, 'rev-parse', 'HEAD'), status=git(repo, 'status', '--short'),
                files={name: sha(repo / name) if (repo / name).is_file() else None
                       for name in sorted(names)})


def stage(name, command, cwd, env, output):
    path = output / f'{name}.log'
    print(f'[{name}]', flush=True)
    with path.open('x') as stream:
        result = subprocess.run(command, cwd=cwd, env=env, stdout=stream,
                                stderr=subprocess.STDOUT, text=True)
    tail = path.read_text(errors='replace').splitlines()[-12:]
    if tail:
        print('\n'.join(tail), flush=True)
    if result.returncode:
        raise RuntimeError(f'{name} exited {result.returncode}; log: {path}')


def check_suite(path):
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == 'testsuite' else list(root.iter('testsuite'))
    counts = {key: sum(int(s.get(key, 0)) for s in suites)
              for key in ('tests', 'skipped', 'failures', 'errors')}
    if counts != dict(tests=EXPECTED_TESTS, skipped=0, failures=0, errors=0):
        raise ValueError(f'Expected {EXPECTED_TESTS} tests with no skips/failures/errors: {counts}')
    return counts


def verification_environment(source, output):
    env = os.environ.copy()
    # Caller options must not skip tests or strip static validation assertions.
    env.pop('PYTEST_ADDOPTS', None)
    env.pop('PYTHONOPTIMIZE', None)
    env['PYTHONPATH'] = str(source / 'src')
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    env['CC'], env['CXX'] = 'gcc', 'g++'
    env['PIP_CACHE_DIR'] = str(output / 'pip-cache')
    env['PIP_DISABLE_PIP_VERSION_CHECK'] = '1'
    env['TMPDIR'] = str(output / 'tmp')
    return env


def reproduce(repo, output):
    source = output / 'source'
    source.mkdir()
    (output / 'tmp').mkdir()
    env = verification_environment(source, output)
    py = sys.executable
    stage('git-init', ['git', 'init', '-q'], source, env, output)
    stage('fetch', ['git', 'fetch', '-q', '--no-tags', '--depth', '1', REMOTE, SOURCE_COMMIT],
          source, env, output)
    stage('checkout', ['git', 'checkout', '-q', '--detach', 'FETCH_HEAD'], source, env, output)
    if git(source, 'rev-parse', 'HEAD') != SOURCE_COMMIT or git(source, 'status', '--short'):
        raise ValueError('Pinned checkout identity or clean state differs')
    versions = {}
    for line in (source / 'requirements-lock.txt').read_text().splitlines():
        if not line or line.startswith('#'):
            continue
        name, expected = line.split('==', 1)
        actual = metadata.version(name)
        versions[name] = dict(expected=expected, actual=actual)
    dump(output / 'dependency-versions.json', versions)
    mismatches = {k: v for k, v in versions.items() if v['expected'] != v['actual']}
    if mismatches:
        raise ValueError(f'Installed versions differ; no packages changed: {mismatches}')
    stage('pip-check', [py, '-m', 'pip', 'check'], source, env, output)
    stage('compiler', ['g++', '--version'], source, env, output)
    stage('cpp-build', [py, 'setup.py', 'build_ext', '--inplace'], source, env, output)
    import_check = '''import json, sys
from pathlib import Path
import pathology_edge
from pathology_edge import _patch_cpp
expected = Path(sys.argv[1]).resolve() / "src/pathology_edge"
package = Path(pathology_edge.__file__).resolve()
cpp = Path(_patch_cpp.__file__).resolve()
if package != expected / "__init__.py" or cpp.parent != expected:
    raise RuntimeError(f"Wrong import source: {package}; {cpp}")
print(json.dumps({"package":str(package), "cpp":str(cpp), "snapshot_imports":True}))
'''
    stage('snapshot-imports', [py, '-c', import_check, str(source)], source, env, output)
    stage('pytest', [py, '-m', 'pytest', '-q', '--junitxml', str(output / 'pytest.xml'),
                    '--basetemp', str(output / 'pytest-tmp')], source, env, output)
    counts = check_suite(output / 'pytest.xml')
    stage('dice-audit', [py, 'scripts/audit_dice.py', '--output', str(output / 'dice-audit.json')],
          source, env, output)
    audit = json.loads((output / 'dice-audit.json').read_text())
    if not (audit['dice_checks'] == 42 and audit['mean_checks'] == 6
            and audit['model_inference_run'] is False and audit['training_run'] is False):
        raise ValueError('Stored Dice audit scope differs')
    stage('static-demo', [py, 'scripts/validate_demo.py'], source, env, output)
    # Compiled extensions/caches are ignored; any tracked content change is unexpected.
    if git(source, 'status', '--short', '--untracked-files=no'):
        raise ValueError('Tracked snapshot files changed during checks')
    return dict(tests=counts, dice_checks=42, mean_checks=6, snapshot_imports=True,
                locked_packages_match=True, pip_check=True, cpp_rebuilt=True,
                static_demo_check=True)


def execute(repo):
    repo = Path(repo).resolve()
    if git(repo, 'rev-parse', '--show-toplevel') != str(repo):
        raise ValueError('Run from the repository root')
    if not (repo / 'src/pathology_edge/learner_wsi.py').is_file():
        raise ValueError('Expected PathologyEdge source is missing')
    if subprocess.run(['git', 'check-ignore', '-q', 'work/reproduction-probe'], cwd=repo).returncode:
        raise ValueError('work/ must be ignored before creating verification outputs')
    before = original_state(repo)
    (repo / 'work').mkdir(exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix='my-ubuntu-repro.', dir=repo / 'work'))
    print(f'Run: {output}', flush=True)
    report = dict(run=str(output), source_commit=SOURCE_COMMIT, original_commit=before['commit'],
                  scope='Pinned source reproduction using existing Ubuntu/Linux packages; not a Docker build',
                  all_checks_passed=False, original_files_preserved=False,
                  docker_build_run=False, new_dataset_experiment_run=False,
                  unit_tests_may_run_synthetic_model_operations=True,
                  environment=dict(platform=platform.platform(), python=sys.version,
                                   executable=sys.executable, parent_python_optimize=sys.flags.optimize))
    try:
        dump(output / 'original-before.json', before)
        shutil.copyfile(__file__, output / 'runner.py')
        for path in (repo / 'src').rglob('*.py'):
            dest = output / 'original-source' / path.relative_to(repo / 'src')
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, dest)
        dump(output / 'environment.json', report['environment'])
        if shutil.disk_usage(output).free < 2 * 1024**3:
            raise ValueError('Less than 2 GiB free; preserve this report and free space before retrying')
        report['checks'] = reproduce(repo, output)
        report['all_checks_passed'] = True
    except Exception as exc:
        report['error'] = f'{type(exc).__name__}: {exc}'
    finally:
        try:
            after = original_state(repo)
            dump(output / 'original-after.json', after)
            report['original_files_preserved'] = before == after
            if before != after:
                report['error'] = 'Original checkout changed during verification; inspect before/after records'
        except Exception as exc:
            report['preservation_check_error'] = str(exc)
        report['all_checks_passed'] = report['all_checks_passed'] and report['original_files_preserved']
        dump(output / 'summary.json', report)
    return output, report


def main():
    _, report = execute(Path.cwd())
    print('SUMMARY', flush=True)
    print(json.dumps(report, ensure_ascii=False), flush=True)
    return 0 if report['all_checks_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
