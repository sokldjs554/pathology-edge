#!/usr/bin/env python3
"""Export existing C++/CNN/ViT evidence without executing snapshots or loading models.

Standalone Python 3.11+ standard-library helper: copy this file into ignored work/.
Creates a fresh ZIP and sibling .manifest.json; --verify reads without extracting.
Integrity/completeness checks are not an independent pixel or model science audit.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import statistics
import sys
import zipfile

MAX_FILE_BYTES = 128 * 1024 * 1024
MAX_TOTAL_BYTES = 512 * 1024 * 1024
MAX_JSON_BYTES = 8 * 1024 * 1024
MAX_FILES = 2048
ARCHITECTURES = ('tiny_unet', 'small_vit')
CASES = [(size, backend, threads) for size in (512, 2048)
         for backend, threads in [('python', 1), ('cpp', 1), ('cpp', 2), ('cpp', 4)]]
SCOPE = ('SHA256 integrity, allowlisted completeness and recorded provenance consistency; '
         'no model loading, code execution, inference, dataset access or independent pixel audit. '
         'An unsigned manifest does not authenticate who produced the evidence.')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def safe_name(name):
    require(isinstance(name, str) and bool(name) and '\\' not in name and ':' not in name
            and '\x00' not in name, 'Unsafe archive path')
    path = PurePosixPath(name)
    require(not path.is_absolute() and all(p not in ('', '.', '..') for p in name.split('/')),
            f'Unsafe archive path: {name}')
    return name


def digest(value):
    require(isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None,
            'Malformed SHA256 hash')
    return value


def load_json(data):
    require(len(data) <= MAX_JSON_BYTES, 'JSON size limit exceeded')

    def number(value):
        result = float(value)
        require(math.isfinite(result), 'Nonfinite JSON measurement')
        return result

    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, f'Duplicate JSON key: {key}')
            result[key] = value
        return result

    return json.loads(data, parse_float=number, parse_constant=number, object_pairs_hook=pairs)


def no_symlinks(path):
    path = Path(os.path.abspath(path))
    for item in (path, *path.parents):
        require(not item.is_symlink(), f'Symlink forbidden: {item}')
    return path


def hash_stream(stream):
    result, size = hashlib.sha256(), 0
    while chunk := stream.read(1024 * 1024):
        size += len(chunk)
        require(size <= MAX_FILE_BYTES, 'File size limit exceeded')
        result.update(chunk)
    return result.hexdigest(), size


def positive(value):
    return type(value) in (int, float) and math.isfinite(value) and value > 0


def audit_evidence(read, add, names, expected_cnn_sha=None, expected_vit_sha=None):
    """Check stored evidence consistency; never import or execute bundled code."""
    cpp = read('cpp/summary.json')
    require(cpp.get('all_checks_passed') is True and cpp.get('original_files_preserved') is True,
            'C++ run is failed, partial, or changed')
    before = read('cpp/original-before.json')
    require(before == read('cpp/original-after.json'), 'Original C++ state changed')
    require(cpp['source_state'] == {key: before[key] for key in ('commit', 'status')},
            'C++ source state differs')
    require(read('cpp/environment.json') == cpp['environment'], 'C++ environment differs')
    add('cpp/runner.py', cpp['runner_sha256'])
    frozen = {safe_name(key): digest(value) for key, value in before['files'].items()
              if key.startswith(('src/', 'cpp/')) and value is not None}
    require(bool(frozen), 'Missing frozen C++ sources')
    for key, value in frozen.items():
        require(PurePosixPath(key).suffix in ('.py', '.cpp', '.h', '.hpp', '.so', '.pyd', '.dylib'),
                'Non-source file in C++ snapshot')
        add('cpp/frozen-source/' + key, value)
    require({name for name in names if name.startswith('cpp/frozen-source/')} ==
            {'cpp/frozen-source/' + key for key in frozen}, 'Unlisted C++ frozen source')
    imports = read('cpp/imports.json')
    require(set(imports) == {'package', 'patches', 'cpp'}, 'Missing C++ imported source provenance')
    repository = PurePosixPath(cpp['repository'])
    require(repository.is_absolute(), 'Expected original absolute repository path')
    for item in imports.values():
        try:
            relative = PurePosixPath(item['path']).relative_to(repository).as_posix()
        except ValueError as exc:
            raise ValueError('Imported source outside original repository') from exc
        require(frozen.get(relative) == digest(item['sha256']), 'Imported source hash differs')
    rounds = cpp['rounds']
    require(type(rounds) is int and rounds in (1, 3) and cpp['repeats_per_worker'] == 9,
            'Unexpected C++ rounds/repeats')
    expected = {(r, *case) for r in range(1, rounds + 1) for case in CASES}
    seen, orders, output_hashes = set(), set(), {}
    for row in cpp['rows']:
        key = (row['round'], row['size'], row['backend'], row['threads'])
        require(key in expected and key not in seen, 'Unexpected or duplicate C++ case')
        seen.add(key)
        order = (row['round'], row['order'])
        require(type(row['order']) is int and 1 <= row['order'] <= 8 and order not in orders,
                'Invalid C++ ordering')
        orders.add(order)
        times = row['measurements_ms']
        require(isinstance(times, list) and len(times) == 9 and all(positive(t) for t in times),
                'Expected nine positive finite C++ timings')
        require(positive(row['median_ms']) and
                math.isclose(statistics.median(times), row['median_ms'], rel_tol=1e-10)
                and positive(row['peak_process_rss_mib']), 'Invalid C++ timing/RSS')
        count = ((row['size'] + 63) // 64) ** 2
        require(row['equal_to_python'] is True and row['dtype'] == 'uint8' and
                row['patch_count'] == count and row['output_shape'] == [count, 128, 128, 3],
                'Missing C++ parity evidence')
        value = digest(row['sha256'])
        require(output_hashes.setdefault(row['size'], value) == value, 'C++ output digests differ')
        require(row['imports'] == imports, 'C++ worker imports differ')
        stem = f"cpp/round{row['round']}-{row['order']:02d}-{row['size']}-{row['backend']}-{row['threads']}t"
        require(read(stem + '.json') == row, 'C++ worker result differs from summary')
        require(read(stem + '.stdout.log') == {k: v for k, v in row.items() if k not in ('round', 'order')},
                'C++ worker stdout differs')
        add(stem + '.stderr.log')
    require(seen == expected, 'Missing C++ timing cases')

    status = read('vit/status.json')
    summary, plan = read('vit/summary.json'), read('vit/protocol.json')
    require(status.get('status') == 'completed' and status.get('all_checks_passed') is True
            and summary.get('all_checks_passed') is True and summary.get('original_files_preserved') is True,
            'Expected completed successful ViT run')
    before = read('vit/original-before.json')
    require(before == read('vit/original-after.json') and before['commit'] == plan['source_commit']
            and bool(before['status']) == plan['source_dirty'], 'Original ViT preservation differs')
    launcher = [f'vit/launcher-original-{stage}.json' for stage in ('before', 'after')]
    if any(name in names for name in launcher):
        require(read(launcher[0]) == read(launcher[1]), 'Launcher original preservation differs')
    frozen = plan['snapshot_hashes']
    require('runner.py' in frozen and len(frozen) > 1, 'Missing ViT source snapshot')
    for key, value in frozen.items():
        safe_name(key)
        require(key == 'runner.py' or re.fullmatch(r'source/pathology_edge/[A-Za-z_][A-Za-z_0-9]*\.py', key),
                'Unallowlisted ViT source path')
        add('vit/' + key, value)
    require({name for name in names if name.startswith('vit/source/')} ==
            {'vit/' + key for key in frozen if key.startswith('source/')}, 'Unlisted ViT snapshot source')
    source = {PurePosixPath(key).name: value for key, value in frozen.items() if key.startswith('source/')}
    require(set(plan['architectures']) == set(ARCHITECTURES) and len(plan['architectures']) == 2,
            'Expected CNN and ViT pair')
    summary_rows = summary['rows']
    require(len(summary_rows) == 2 and {r['architecture'] for r in summary_rows} == set(ARCHITECTURES),
            'Missing ViT summary model rows')
    reports, manifests, model_hashes = [], [], {}
    for architecture, submitted in zip(ARCHITECTURES, (expected_cnn_sha, expected_vit_sha)):
        prefix = 'vit/' + architecture + '/'
        report = read(prefix + 'training.json')
        config = read(prefix + 'protocol.json')
        history = read(prefix + 'history.json')
        manifest = read(prefix + 'manifest.json')
        add(prefix + 'manifest.json', plan['manifest_sha256'])
        require(report['architecture'] == architecture and report['config'] == config,
                'Model protocol differs')
        require(config['seed'] == plan['seed'] == summary['seed'] and config['epochs'] == 16
                and config['manifest_sha256'] == plan['manifest_sha256'], 'Model protocol incomplete')
        require(read(prefix + 'source-hashes.json') == source and
                config['loss_source_sha256'] == source['learner_losses.py'], 'Model source hashes differ')
        require(history == report['history'] and [h['epoch'] for h in history] == list(range(1, 17)),
                'Incomplete training history')
        require(report['test_evaluation_run'] is False and summary['test_evaluation_run'] is False
                and prefix + 'evaluation.json' not in names and prefix + 'evaluation_lock.json' not in names,
                'Unexpected test evaluation')
        model_hash = add(prefix + 'model.pt', report['model_sha256'])
        require(submitted is None or model_hash == digest(submitted), 'Model hash differs from submitted hash')
        saved_summary = next(row for row in summary_rows if row['architecture'] == architecture)
        require(saved_summary['model_sha256'] == model_hash, 'Summary model hash differs')
        model_hashes[architecture] = model_hash
        rows = [row for row in manifest['records'] if row['split'] == 'validation']
        counts = {split: sum(row['split'] == split for row in manifest['records'])
                  for split in ('train', 'validation', 'test')}
        require(counts == {'train': 33, 'validation': 10, 'test': 7}, 'Incomplete data manifest')
        saved = report['validation']['rows']
        require([r['id'] for r in rows] == [r['id'] for r in saved], 'Incomplete validation predictions')
        predictions = set()
        for row, prediction in zip(rows, saved):
            name = safe_name(prediction['prediction'])
            require(re.fullmatch(r'predictions/[0-9]{2}\.npy', name) is not None
                    and name not in predictions and prediction['group_id'] == row['group_id'],
                    'Invalid prediction path or group')
            predictions.add(name)
            add(prefix + name, prediction['prediction_sha256'])
        require({name for name in names if name.startswith(prefix + 'predictions/')} ==
                {prefix + name for name in predictions}, 'Unlisted saved probability')
        add('vit/' + architecture + '.log')
        reports.append(report)
        manifests.append(manifest)
    require(reports[0]['config'] == reports[1]['config'] and manifests[0] == manifests[1],
            'Paired model controls differ')
    require(reports[0]['environment'] == reports[1]['environment'] == summary['environment'],
            'Paired model environments differ')
    for prefix in ('cpp/', 'vit/'):
        if prefix + 'RUN.txt' in names:
            add(prefix + 'RUN.txt')
    return model_hashes


def source_files(cpp_run, vit_run):
    paths, roots = {}, {}
    for prefix, raw in [('cpp', cpp_run), ('vit', vit_run)]:
        root = no_symlinks(raw)
        require(root.is_dir(), f'Missing run directory: {root}')
        roots[prefix] = root
        for directory, dirs, files in os.walk(root, followlinks=False):
            for name in dirs + files:
                path = Path(directory) / name
                require(not path.is_symlink(), f'Symlink forbidden: {path}')
            for name in files:
                path = Path(directory) / name
                require(stat.S_ISREG(path.stat().st_mode), f'Nonregular input: {path}')
                paths[prefix + '/' + path.relative_to(root).as_posix()] = path
                require(len(paths) <= MAX_FILES, 'Input file count limit exceeded')
    for stage in ('before', 'after'):
        path = roots['vit'].parent / f'original-{stage}.json'
        no_symlinks(path)
        if path.exists():
            paths[f'vit/launcher-original-{stage}.json'] = path
    return paths, roots


def export_bundle(cpp_run, vit_run, output, *, expected_cnn_sha=None, expected_vit_sha=None):
    """Create output.zip plus output.manifest.json exclusively; return the manifest."""
    output = no_symlinks(output)
    require(output.suffix == '.zip', 'Output must have .zip suffix')
    sidecar = output.with_suffix('.manifest.json')
    no_symlinks(sidecar)
    for destination in (output, sidecar):
        if destination.exists():
            raise FileExistsError(destination)
    paths, roots = source_files(cpp_run, vit_run)
    for root in roots.values():
        require(not output.is_relative_to(root) and not sidecar.is_relative_to(root), 'Output/run overlap')
    require(not roots['cpp'].is_relative_to(roots['vit']) and not roots['vit'].is_relative_to(roots['cpp']),
            'Input run overlap')
    records = {}

    def add(name, expected=None):
        safe_name(name)
        require(name in paths, f'Missing required artifact: {name}')
        if name not in records:
            path = paths[name]
            no_symlinks(path)
            require(stat.S_ISREG(path.stat().st_mode), f'Nonregular artifact: {path}')
            require(path.stat().st_size <= MAX_FILE_BYTES, 'File size limit exceeded')
            with path.open('rb') as handle:
                value, size = hash_stream(handle)
            records[name] = dict(path=name, source_path=str(path), size=size, sha256=value)
        record = records[name]
        require(expected is None or record['sha256'] == digest(expected), f'Hash mismatch: {name}')
        return record['sha256']

    def read(name):
        add(name)
        require(records[name]['size'] <= MAX_JSON_BYTES, 'JSON size limit exceeded')
        data = paths[name].read_bytes()
        require(hashlib.sha256(data).hexdigest() == records[name]['sha256'], 'Input changed while reading')
        return load_json(data)

    try:
        models = audit_evidence(read, add, set(paths), expected_cnn_sha, expected_vit_sha)
    except (KeyError, TypeError, IndexError) as exc:
        raise ValueError(f'Malformed or incomplete evidence: {exc}') from exc
    require(sum(row['size'] for row in records.values()) <= MAX_TOTAL_BYTES, 'Total size limit exceeded')
    manifest = dict(schema_version=1, created_utc=datetime.now(timezone.utc).isoformat(),
                    original_paths={key: str(value) for key, value in roots.items()},
                    model_sha256=models, scientific_audit_performed=False, verification_scope=SCOPE,
                    launcher_original_state_included='vit/launcher-original-before.json' in records,
                    files=[records[key] for key in sorted(records)])
    payload = (json.dumps(manifest, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode()
    require(len(payload) <= MAX_JSON_BYTES, 'Manifest size limit exceeded')
    created = []
    try:
        with output.open('xb') as raw:
            created.append(output)
            with zipfile.ZipFile(raw, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
                for name, record in sorted(records.items()):
                    no_symlinks(paths[name])
                    with paths[name].open('rb') as source, archive.open(name, 'w') as target:
                        value, size = hashlib.sha256(), 0
                        while chunk := source.read(1024 * 1024):
                            size += len(chunk)
                            require(size <= record['size'], 'Input grew during export')
                            value.update(chunk)
                            target.write(chunk)
                    require(size == record['size'] and value.hexdigest() == record['sha256'],
                            'Input changed during export')
                archive.writestr('manifest.json', payload)
        verify_bundle(output, expected_cnn_sha=expected_cnn_sha, expected_vit_sha=expected_vit_sha)
        with sidecar.open('xb') as handle:
            created.append(sidecar)
            handle.write(payload)
    except BaseException:
        for path in reversed(created):
            path.unlink()
        raise
    return manifest


def verify_bundle(bundle, *, expected_cnn_sha=None, expected_vit_sha=None):
    """Verify in place without extraction or reading any recorded original path."""
    path = no_symlinks(bundle)
    require(path.stat().st_size <= MAX_TOTAL_BYTES + MAX_JSON_BYTES, 'Archive size limit exceeded')
    try:
        with zipfile.ZipFile(path) as archive:
            entries = archive.infolist()
            require(len(entries) <= MAX_FILES + 1, 'Archive file count limit exceeded')
            names = set()
            for entry in entries:
                name = safe_name(entry.filename)
                require(name not in names, 'Duplicate archive entry')
                names.add(name)
                mode = entry.external_attr >> 16
                require(stat.S_IFMT(mode) in (0, stat.S_IFREG) and not entry.is_dir(),
                        'Symlink or nonregular archive entry')
                require(not entry.flag_bits & 1 and entry.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED),
                        'Encrypted or unsupported archive entry')
                require(entry.file_size <= MAX_FILE_BYTES, 'Archive file size limit exceeded')
            require(sum(entry.file_size for entry in entries) <= MAX_TOTAL_BYTES + MAX_JSON_BYTES,
                    'Archive total size limit exceeded')
            require('manifest.json' in names, 'Missing archive manifest')
            require(archive.getinfo('manifest.json').file_size <= MAX_JSON_BYTES, 'Manifest size limit exceeded')
            manifest = load_json(archive.read('manifest.json'))
            require(manifest['schema_version'] == 1 and manifest['scientific_audit_performed'] is False
                    and manifest['verification_scope'] == SCOPE, 'Unsupported verification scope/schema')
            records = {}
            for row in manifest['files']:
                name = safe_name(row['path'])
                require(name not in records and name in names and name != 'manifest.json', 'Invalid manifest entry')
                require(type(row['size']) is int and row['size'] == archive.getinfo(name).file_size,
                        'Manifest file size mismatch')
                digest(row['sha256'])
                records[name] = row
            require(set(records) == names - {'manifest.json'}, 'Unlisted or missing archive entry')
            checked = set()

            def add(name, expected=None):
                require(name in records, f'Missing required artifact: {name}')
                record = records[name]
                if name not in checked:
                    with archive.open(name) as source:
                        value, size = hash_stream(source)
                    require(value == record['sha256'] and size == record['size'], f'Hash mismatch: {name}')
                    prefix, relative = name.split('/', 1)
                    root = PurePosixPath(manifest['original_paths'][prefix])
                    require(root.is_absolute(), 'Missing original absolute path')
                    if relative.startswith('launcher-original-'):
                        original = root.parent / relative.removeprefix('launcher-')
                    else:
                        original = root / relative
                    require(record['source_path'] == str(original), 'Original artifact path mismatch')
                    checked.add(name)
                require(expected is None or record['sha256'] == digest(expected), f'Hash mismatch: {name}')
                return record['sha256']

            def read(name):
                add(name)
                require(records[name]['size'] <= MAX_JSON_BYTES, 'JSON size limit exceeded')
                return load_json(archive.read(name))

            models = audit_evidence(read, add, set(records), expected_cnn_sha, expected_vit_sha)
            require(checked == set(records), 'Unallowlisted archive entry')
            require(models == manifest['model_sha256'], 'Manifest model hashes differ')
            require(manifest['launcher_original_state_included'] == ('vit/launcher-original-before.json' in records),
                    'Launcher provenance declaration differs')
            return manifest
    except (zipfile.BadZipFile, KeyError, TypeError, IndexError, RuntimeError) as exc:
        raise ValueError(f'Invalid evidence archive: {exc}') from exc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cpp-run', type=Path)
    parser.add_argument('--vit-run', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--verify', type=Path)
    parser.add_argument('--expected-cnn-sha')
    parser.add_argument('--expected-vit-sha')
    args = parser.parse_args()
    expected = dict(expected_cnn_sha=args.expected_cnn_sha, expected_vit_sha=args.expected_vit_sha)
    try:
        if args.verify:
            if any((args.cpp_run, args.vit_run, args.output)):
                parser.error('--verify cannot be combined with export arguments')
            result = verify_bundle(args.verify, **expected)
        else:
            if not all((args.cpp_run, args.vit_run, args.output)):
                parser.error('export requires --cpp-run, --vit-run and --output')
            result = export_bundle(args.cpp_run, args.vit_run, args.output, **expected)
        print(json.dumps(dict(integrity_verified=True, scientific_audit_performed=False,
                              files=len(result['files']), model_sha256=result['model_sha256'],
                              bundle=str(args.verify or args.output)), allow_nan=False))
        return 0
    except (OSError, ValueError) as exc:
        print(f'Evidence rejected: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
