"""Standalone, read-only review of the installed Python/C++ patch extractors.

Download this file into the original checkout's ignored work/ directory and run
it with the existing Python environment. No installation or build is performed.
"""
import argparse
from datetime import datetime, timezone
import gc
import hashlib
from importlib import machinery, metadata
import json
import math
import os
from pathlib import Path
import platform
import re
import resource
import shutil
import statistics
import subprocess
import sys
import tempfile
from time import perf_counter
import traceback


CASES = [(size, backend, threads) for size in (512, 2048)
         for backend, threads in [('python', 1), ('cpp', 1), ('cpp', 2), ('cpp', 4)]]
REPEATS = 9
TIMING_SCOPE = ('allocation + crop copy + white padding through patches.extract '
                '(including its Python wrapper); no inference, input generation, '
                'grid creation, parity checking, hashing, or disk I/O')
MEMORY_SCOPE = ('absolute worker process peak RSS, including input, imports, '
                'both parity outputs and comparison temporaries; not incremental '
                'extractor memory or inference memory')


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def dump(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')


def git(repo, *args):
    return subprocess.check_output(['git', *args], cwd=repo, text=True).strip()


def original_state(repo):
    """Fingerprint tracked files, including dirty files, and ignored local code."""
    names = set(filter(None, git(repo, 'ls-files', '-z').split('\0')))
    for folder in ('src', 'cpp'):
        names.update(path.relative_to(repo).as_posix() for path in (repo / folder).rglob('*')
                     if path.is_file() and '__pycache__' not in path.parts
                     and (path.suffix in ('.py', '.cpp', '.h', '.hpp', '.so', '.dylib', '.pyd')))
    return dict(commit=git(repo, 'rev-parse', 'HEAD'), status=git(repo, 'status', '--short'),
                files={name: sha256(repo / name) if (repo / name).is_file() else None
                       for name in sorted(names)})


def environment():
    versions = {}
    for name in ('numpy', 'torch', 'pathology-edge'):
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = None
    affinity = sorted(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else None
    cgroup = {}
    for name in ('cpu.max', 'cpuset.cpus.effective', 'cpu/cpu.cfs_quota_us',
                 'cpu/cpu.cfs_period_us'):
        path = Path('/sys/fs/cgroup') / name
        try:
            cgroup[name] = path.read_text().strip()
        except OSError:
            pass
    # Paths are recorded verbatim; a host CPU count need not be the usable quota.
    try:
        cgroup['process_membership'] = Path('/proc/self/cgroup').read_text().strip()
    except OSError:
        pass
    cpu_model = None
    try:
        for line in Path('/proc/cpuinfo').read_text().splitlines():
            if line.startswith('model name'):
                cpu_model = line.split(':', 1)[1].strip()
                break
    except OSError:
        pass
    return dict(platform=platform.platform(), python=sys.version, executable=sys.executable,
                python_optimize=sys.flags.optimize, versions=versions, cpu_model=cpu_model,
                visible_logical_cpus=os.cpu_count(), affinity_cpus=affinity,
                affinity_cpu_count=len(affinity) if affinity is not None else None,
                cgroup=cgroup,
                thread_environment={name: os.environ.get(name) for name in
                                    ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS')})


def check_imports(repo):
    import pathology_edge
    from pathology_edge import _patch_cpp, patches
    expected = repo / 'src/pathology_edge'
    paths = dict(package=Path(pathology_edge.__file__).resolve(),
                 patches=Path(patches.__file__).resolve(), cpp=Path(_patch_cpp.__file__).resolve())
    if (paths['package'] != expected / '__init__.py'
            or paths['patches'] != expected / 'patches.py'
            or paths['cpp'].parent != expected
            or not any(str(paths['cpp']).endswith(suffix) for suffix in machinery.EXTENSION_SUFFIXES)):
        raise ValueError(f'Imports must come from the original repository {expected}: {paths}')
    return {name: dict(path=str(path), sha256=sha256(path)) for name, path in paths.items()}


def measure_case(size, backend, threads):
    import numpy as np
    from pathology_edge.patches import extract, grid
    image = np.random.default_rng(42).integers(0, 256, (size, size, 3), dtype=np.uint8)
    patches = grid(size, size, 128, 64)
    expected = extract(image, patches, 'python', 1)
    actual = extract(image, patches, backend, threads)
    expected_shape = (len(patches), 128, 128, 3)
    # Explicit checks remain active under python -O / PYTHONOPTIMIZE.
    if (expected.dtype != np.uint8 or actual.dtype != np.uint8
            or expected.shape != expected_shape or actual.shape != expected_shape
            or not np.array_equal(expected, actual)):
        raise ValueError(f'Output parity failed for {size}/{backend}/{threads}')
    digest = hashlib.sha256(memoryview(actual).cast('B')).hexdigest()
    del actual, expected
    gc.collect()
    times = []
    for _ in range(REPEATS):
        start = perf_counter()
        output = extract(image, patches, backend, threads)
        times.append((perf_counter() - start) * 1000)
        del output
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    rss_mib = rss / (1024 * 1024 if sys.platform == 'darwin' else 1024)
    return dict(size=size, backend=backend, threads=threads, patch_count=len(patches),
                median_ms=statistics.median(times), measurements_ms=times,
                peak_process_rss_mib=rss_mib, sha256=digest, equal_to_python=True,
                dtype='uint8', output_shape=list(expected_shape), memory_scope=MEMORY_SCOPE)


def positive_finite(value):
    return type(value) in (int, float) and math.isfinite(value) and value > 0


def validate_row(row, case):
    size, backend, threads = case
    if not isinstance(row, dict):
        raise ValueError('Worker result must be a JSON object')
    if (row.get('size'), row.get('backend'), row.get('threads')) != case:
        raise ValueError('Worker result identifies the wrong case')
    times = row.get('measurements_ms')
    if not isinstance(times, list) or len(times) != REPEATS or not all(map(positive_finite, times)):
        raise ValueError(f'Expected {REPEATS} positive finite measurements')
    median = row.get('median_ms')
    if not positive_finite(median) or not math.isclose(median, statistics.median(times), rel_tol=1e-10):
        raise ValueError('Median is nonfinite or inconsistent with measurements')
    if not positive_finite(row.get('peak_process_rss_mib')):
        raise ValueError('Missing or invalid absolute peak RSS')
    count = ((size + 63) // 64) ** 2
    if (row.get('equal_to_python') is not True or row.get('dtype') != 'uint8'
            or row.get('patch_count') != count or row.get('output_shape') != [count, 128, 128, 3]):
        raise ValueError('Missing parity, wrong output shape, dtype, or patch count')
    if not isinstance(row.get('sha256'), str) or not re.fullmatch('[0-9a-f]{64}', row['sha256']):
        raise ValueError('Missing or malformed output digest')


def read_worker_result(path, case):
    def reject_constant(value):
        raise ValueError(f'Nonfinite JSON value: {value}')
    row = json.loads(Path(path).read_text(), parse_constant=reject_constant)
    validate_row(row, case)
    return row


def run_worker(command, repo, env, output, name):
    stdout, stderr = output / f'{name}.stdout.log', output / f'{name}.stderr.log'
    with stdout.open('x') as out, stderr.open('x') as err:
        result = subprocess.run(command, cwd=repo, env=env, stdout=out, stderr=err, timeout=90)
    if result.returncode:
        raise RuntimeError(f'Worker exited {result.returncode}; inspect {stderr} and {stdout}')
    return stdout


def run_cases(repo, output, rounds, rows):
    imports = check_imports(repo)
    dump(output / 'imports.json', imports)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    # Keep installed import routing; never inject another checkout via PYTHONPATH.
    orderings = [CASES, list(reversed(CASES)), CASES[2::4] + CASES[::4] + CASES[3::4] + CASES[1::4]]
    for round_index in range(rounds):
        for sequence, case in enumerate(orderings[round_index], 1):
            size, backend, threads = case
            name = f'round{round_index + 1}-{sequence:02d}-{size}-{backend}-{threads}t'
            print(f'[{name}]', flush=True)
            command = [sys.executable, str(output / 'runner.py'), '--worker', '--repo', str(repo),
                       '--size', str(size), '--backend', backend, '--threads', str(threads)]
            stdout = run_worker(command, repo, env, output, name)
            row = read_worker_result(stdout, case)
            if row.get('imports') != imports:
                raise ValueError(f'Imported paths or source/binary hashes changed: {name}')
            row.update(round=round_index + 1, order=sequence)
            dump(output / f'{name}.json', row)
            rows.append(row)
    if check_imports(repo) != imports:
        raise ValueError('Imported source/binary changed during measurement')


def summarize(rows, rounds):
    expected = {(round_index, *case) for round_index in range(1, rounds + 1) for case in CASES}
    seen, digests = set(), {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('Review contains malformed rows')
        key = (row.get('round'), row.get('size'), row.get('backend'), row.get('threads'))
        if key not in expected or key in seen:
            raise ValueError('Unexpected or duplicate review case')
        validate_row(row, key[1:])
        seen.add(key)
        previous = digests.setdefault(row['size'], row['sha256'])
        if row['sha256'] != previous:
            raise ValueError('Output digest differs between backends or rounds')
    if seen != expected:
        raise ValueError('Review is empty or missing required cases')
    summary = []
    for size, backend, threads in CASES:
        group = [row for row in rows if (row['size'], row['backend'], row['threads']) == (size, backend, threads)]
        timings = [value for row in group for value in row['measurements_ms']]
        baseline = [value for row in rows if row['size'] == size and row['backend'] == 'python'
                    for value in row['measurements_ms']]
        median = statistics.median(timings)
        summary.append(dict(size=size, backend=backend, threads=threads, median_ms=median,
                            speedup_vs_python=statistics.median(baseline) / median,
                            peak_process_rss_mib=max(row['peak_process_rss_mib'] for row in group),
                            round_medians_ms=[row['median_ms'] for row in group]))
    return summary


def execute(repo, output=None, rounds=1):
    repo = Path(repo).resolve()
    if rounds not in (1, 3):
        raise ValueError('Choose one quick round or three order-varied rounds')
    if git(repo, 'rev-parse', '--show-toplevel') != str(repo):
        raise ValueError('Run from the original repository root')
    if subprocess.run(['git', 'check-ignore', '-q', 'work/cpp-review-probe'], cwd=repo).returncode:
        raise ValueError('work/ must be ignored before creating review outputs')
    work = repo / 'work'
    work.mkdir(exist_ok=True)
    if output is None:
        output = Path(tempfile.mkdtemp(prefix='my-cpp-review.', dir=work))
    else:
        output = Path(output).absolute()
        if output.parent.resolve() != work.resolve():
            raise ValueError('Output must be a new direct child of the original work/ directory')
        output.mkdir()  # Never reuse or overwrite even a failed review.
    print(f'RUN_DIR={output}', flush=True)
    report = dict(schema_version=1, run=str(output), repository=str(repo),
                  started_utc=datetime.now(timezone.utc).isoformat(),
                  all_checks_passed=False, original_files_preserved=False,
                  input=dict(seed=42, dtype='uint8', channels='RGB', sizes=[512, 2048],
                             patch_size=128, overlap=64,
                             meaning='Synthetic engineering workload; not pathology accuracy evidence'),
                  rounds=rounds, repeats_per_worker=REPEATS, warmup='one untimed parity call per backend',
                  timing_scope=TIMING_SCOPE, memory_scope=MEMORY_SCOPE,
                  binary_build_provenance='Existing installed extension; not rebuilt. Hashes do not prove which source/compiler built it.',
                  aggregation='median of all 9 or 27 timed calls; raw and per-round medians retained',
                  order_note='round 1 forward; round 2 reversed; round 3 interleaved; not a full Latin square',
                  source_state=None, rows=[])
    before = None
    sys.dont_write_bytecode = True
    try:
        (output / 'RUN.txt').write_text(f'Repository: {repo}\nRun: {output}\n'
                                      f'Result: {output / "summary.json"}\n'
                                      'After a terminal reset, read summary.json and *.stderr.log here.\n')
        shutil.copyfile(__file__, output / 'runner.py')
        report['runner_sha256'] = sha256(output / 'runner.py')
        before = original_state(repo)
        report['source_state'] = dict(commit=before['commit'], status=before['status'])
        dump(output / 'original-before.json', before)
        # Preserve the actual local Python/C++ sources and installed extension.
        for name in before['files']:
            if name.startswith(('src/', 'cpp/')) and (repo / name).is_file():
                dest = output / 'frozen-source' / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(repo / name, dest)
                if sha256(dest) != before['files'][name]:
                    raise ValueError(f'Source changed while freezing: {name}')
        report['environment'] = environment()
        dump(output / 'environment.json', report['environment'])
        run_cases(repo, output, rounds, report['rows'])
        report['comparison'] = summarize(report['rows'], rounds)
        report['all_checks_passed'] = True
    except (Exception, KeyboardInterrupt) as exc:
        report['error'] = f'{type(exc).__name__}: {exc}'
        (output / 'failure.log').write_text(traceback.format_exc())
    finally:
        try:
            after = original_state(repo)
            dump(output / 'original-after.json', after)
            report['original_files_preserved'] = before is not None and before == after
            if before is not None and before != after:
                report['preservation_error'] = 'Checkout changed; inspect original-before.json and original-after.json'
        except Exception as exc:
            report['preservation_error'] = str(exc)
        report['all_checks_passed'] = report['all_checks_passed'] and report['original_files_preserved']
        report['finished_utc'] = datetime.now(timezone.utc).isoformat()
        dump(output / 'summary.json', report)
    return output, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path.cwd())
    parser.add_argument('--output', type=Path, help='Fresh directory directly inside the original work/')
    parser.add_argument('--rounds', type=int, choices=(1, 3), default=1)
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--size', type=int, choices=(512, 2048), help=argparse.SUPPRESS)
    parser.add_argument('--backend', choices=('python', 'cpp'), help=argparse.SUPPRESS)
    parser.add_argument('--threads', type=int, choices=(1, 2, 4), help=argparse.SUPPRESS)
    args = parser.parse_args()
    sys.dont_write_bytecode = True
    if args.worker:
        if (args.size, args.backend, args.threads) not in CASES:
            parser.error('Incomplete or invalid worker case')
        imports = check_imports(args.repo.resolve())
        row = measure_case(args.size, args.backend, args.threads)
        if check_imports(args.repo.resolve()) != imports:
            raise ValueError('Worker source/binary changed during measurement')
        row['imports'] = imports
        print(json.dumps(row, allow_nan=False))
        return 0
    output, report = execute(args.repo, args.output, args.rounds)
    for row in report.get('comparison', []):
        print(f"{row['size']:4d} {row['backend']:6s} {row['threads']}t "
              f"{row['median_ms']:.3f} ms  {row['speedup_vs_python']:.2f}x Python  "
              f"peak RSS {row['peak_process_rss_mib']:.1f} MiB")
    print('SUMMARY ' + json.dumps(dict(all_checks_passed=report['all_checks_passed'],
                                      original_files_preserved=report['original_files_preserved'],
                                      completed_cases=len(report['rows']),
                                      path=str(output / 'summary.json'),
                                      error=report.get('error') or report.get('preservation_error'))))
    return 0 if report['all_checks_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
