"""Portable evidence must retain provenance and reject incomplete or unsafe input."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import zipfile

import pytest

SCRIPT = Path(__file__).parents[1] / 'scripts/export_research_evidence.py'
ROOT = SCRIPT.parents[1]


@pytest.fixture
def exporter():
    assert SCRIPT.exists(), 'The standalone evidence exporter is not implemented'
    spec = importlib.util.spec_from_file_location('evidence_exporter', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path, value):
    path.write_text(json.dumps(value))


def update_json(path, mutate):
    value = json.loads(path.read_text())
    mutate(value)
    write_json(path, value)


@pytest.fixture
def runs(tmp_path):
    """Committed report layout with opaque fixtures, requiring no ignored files."""
    cpp = tmp_path / 'cpp-run'
    vit = tmp_path / 'vit-source/work/vit-run'
    for target in (cpp, vit):
        # Build portable fixtures from committed reports; no source is executed.
        committed = 'cpp-review-20261111' if target == cpp else 'cnn-vit-20261113'
        shutil.copytree(ROOT / 'artifacts/experiments' / committed, target)
    cpp_summary = json.loads((cpp / 'summary.json').read_text())
    state = json.loads((cpp / 'original-before.json').read_text())
    frozen = {}
    for original in state['files']:
        if original.startswith(('src/', 'cpp/')) and state['files'][original] is not None:
            target = cpp / 'frozen-source' / original
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b'opaque frozen source; never execute\n')
            frozen[original] = hashlib.sha256(target.read_bytes()).hexdigest()
    state['files'].update(frozen)
    for name in ['original-before.json', 'original-after.json']:
        write_json(cpp / name, state)
    imports = json.loads((cpp / 'imports.json').read_text())
    for item in imports.values():
        relative = Path(item['path']).relative_to(cpp_summary['repository']).as_posix()
        item['sha256'] = frozen[relative]
    write_json(cpp / 'imports.json', imports)
    for row in cpp_summary['rows']:
        row['imports'] = imports
        name = f"round{row['round']}-{row['order']:02d}-{row['size']}-{row['backend']}-{row['threads']}t"
        write_json(cpp / f'{name}.json', row)
        write_json(cpp / f'{name}.stdout.log', {k: v for k, v in row.items() if k not in ('round', 'order')})
    (cpp / 'runner.py').write_text('raise RuntimeError("must never execute")\n')
    cpp_summary['runner_sha256'] = hashlib.sha256((cpp / 'runner.py').read_bytes()).hexdigest()
    write_json(cpp / 'summary.json', cpp_summary)
    plan = json.loads((vit / 'protocol.json').read_text())
    for name in plan['snapshot_hashes']:
        target = vit / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('raise RuntimeError("must never execute")\n')
        plan['snapshot_hashes'][name] = hashlib.sha256(target.read_bytes()).hexdigest()
    write_json(vit / 'protocol.json', plan)
    for architecture in ('tiny_unet', 'small_vit'):
        folder = vit / architecture
        report = json.loads((folder / 'training.json').read_text())
        for row in report['validation']['rows']:
            target = folder / row['prediction']
            target.parent.mkdir(exist_ok=True)
            target.write_bytes(b'opaque saved probability bytes')
            row['prediction_sha256'] = hashlib.sha256(target.read_bytes()).hexdigest()
        report['config']['loss_source_sha256'] = plan['snapshot_hashes']['source/pathology_edge/learner_losses.py']
        write_json(folder / 'training.json', report)
        write_json(folder / 'protocol.json', report['config'])
        write_json(folder / 'source-hashes.json', {Path(k).name: v for k, v in plan['snapshot_hashes'].items() if k.startswith('source/')})
    for name in ('original-before.json', 'original-after.json'):
        shutil.copyfile(vit / name, vit.parent / name)
    return cpp, vit


def test_export_is_portable_allowlisted_read_only_and_verifiable(exporter, runs, tmp_path):
    cpp, vit = runs
    (vit / 'raw-private-image.png').write_bytes(b'do not export')
    original = {p: p.read_bytes() for root in runs for p in root.rglob('*') if p.is_file()}
    output = tmp_path / 'evidence.zip'
    manifest = exporter.export_bundle(cpp, vit, output)
    assert output.with_suffix('.manifest.json').exists()
    assert manifest['original_paths'] == {'cpp': str(cpp), 'vit': str(vit)}
    assert manifest['scientific_audit_performed'] is False
    names = {row['path'] for row in manifest['files']}
    assert 'vit/tiny_unet/predictions/00.npy' in names
    assert 'cpp/round1-01-512-python-1t.json' in names
    assert 'vit/launcher-original-before.json' in names
    assert not any(name.endswith('.png') for name in names)
    assert {p: p.read_bytes() for p in original} == original
    moved = tmp_path / 'relocated.zip'
    output.rename(moved)
    shutil.rmtree(cpp)
    shutil.rmtree(vit.parent)
    assert exporter.verify_bundle(moved) == manifest
    result = subprocess.run([sys.executable, '-I', str(SCRIPT), '--verify', str(moved)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize('path', ['cpp/runner.py', 'cpp/original-after.json', 'cpp/round1-01-512-python-1t.json',
                                'vit/source/pathology_edge/vit.py', 'vit/tiny_unet/predictions/00.npy',
                                'vit/small_vit/history.json'])
def test_missing_artifact_prevents_export(exporter, runs, tmp_path, path):
    prefix, relative = path.split('/', 1)
    (runs[prefix == 'vit'] / relative).unlink()
    with pytest.raises((ValueError, FileNotFoundError)):
        exporter.export_bundle(*runs, tmp_path / 'evidence.zip')
    assert not (tmp_path / 'evidence.zip').exists()


@pytest.mark.parametrize('mutation', ['failed', 'changed_original', 'model', 'prediction', 'snapshot', 'nan_cpp', 'inf_cpp', 'missing_row', 'launcher'])
def test_partial_or_changed_evidence_is_rejected(exporter, runs, tmp_path, mutation):
    cpp, vit = runs
    if mutation == 'failed':
        update_json(vit / 'status.json', lambda d: d.update(status='failed'))
    elif mutation == 'changed_original':
        update_json(cpp / 'original-after.json', lambda d: d.update(commit='changed'))
    elif mutation in ('model', 'prediction', 'snapshot'):
        path = {'model': 'tiny_unet/model.pt', 'prediction': 'tiny_unet/predictions/00.npy',
                'snapshot': 'source/pathology_edge/vit.py'}[mutation]
        (vit / path).write_bytes(b'tampered')
    elif mutation in ('nan_cpp', 'inf_cpp'):
        update_json(cpp / 'summary.json', lambda d: d['rows'][0]['measurements_ms'].__setitem__(0, float('nan') if mutation == 'nan_cpp' else float('inf')))
    elif mutation == 'missing_row':
        update_json(cpp / 'summary.json', lambda d: d['rows'].pop())
    else:
        (vit.parent / 'original-after.json').unlink()
    with pytest.raises((ValueError, FileNotFoundError)):
        exporter.export_bundle(cpp, vit, tmp_path / 'evidence.zip')


def test_export_refuses_overwrite_overlap_and_symlinks(exporter, runs, tmp_path):
    cpp, vit = runs
    output = tmp_path / 'evidence.zip'
    output.write_bytes(b'keep me')
    with pytest.raises(FileExistsError):
        exporter.export_bundle(cpp, vit, output)
    assert output.read_bytes() == b'keep me'
    with pytest.raises(ValueError, match='overlap'):
        exporter.export_bundle(cpp, vit, vit / 'new.zip')
    (vit / 'unlisted-symlink').symlink_to(tmp_path)
    with pytest.raises(ValueError, match='[Ss]ymlink'):
        exporter.export_bundle(cpp, vit, tmp_path / 'new.zip')


def rewrite_zip(source, destination, mutation):
    with zipfile.ZipFile(source) as old, zipfile.ZipFile(destination, 'w') as new:
        for entry in old.infolist():
            data = old.read(entry)
            if entry.filename == 'vit/tiny_unet/model.pt' and mutation == 'tampered':
                data = b'tampered'
            if entry.filename == 'vit/tiny_unet/model.pt' and mutation == 'missing':
                continue
            new.writestr(entry, data)
        if mutation in ('extra', 'traversal', 'symlink', 'duplicate'):
            name = {'extra': 'vit/unlisted.txt', 'traversal': '../escaped.txt',
                    'symlink': 'vit/link', 'duplicate': 'manifest.json'}[mutation]
            info = zipfile.ZipInfo(name)
            if mutation == 'symlink':
                info.create_system = 3
                info.external_attr = (stat.S_IFLNK | 0o777) << 16
            new.writestr(info, b'hostile')


@pytest.mark.parametrize('mutation', ['tampered', 'missing', 'extra', 'traversal', 'symlink', 'duplicate'])
def test_verifier_rejects_unsafe_or_corrupt_archive(exporter, runs, tmp_path, mutation):
    output = tmp_path / 'evidence.zip'
    exporter.export_bundle(*runs, output)
    bad = tmp_path / 'bad.zip'
    if mutation == 'duplicate':
        with pytest.warns(UserWarning, match='Duplicate'):
            rewrite_zip(output, bad, mutation)
    else:
        rewrite_zip(output, bad, mutation)
    with pytest.raises(ValueError):
        exporter.verify_bundle(bad)
    assert not (tmp_path / 'escaped.txt').exists()


def test_expected_model_hash_and_size_limits_are_enforced(exporter, runs, tmp_path, monkeypatch):
    with pytest.raises(ValueError, match='[Mm]odel|[Hh]ash'):
        exporter.export_bundle(*runs, tmp_path / 'wrong.zip', expected_cnn_sha='0' * 64)
    monkeypatch.setattr(exporter, 'MAX_FILE_BYTES', 32)
    with pytest.raises(ValueError, match='[Ss]ize|[Ll]imit'):
        exporter.export_bundle(*runs, tmp_path / 'oversize.zip')


def test_manifest_cannot_allowlist_an_arbitrary_file(exporter, runs, tmp_path):
    output, bad = tmp_path / 'evidence.zip', tmp_path / 'bad.zip'
    exporter.export_bundle(*runs, output)
    with zipfile.ZipFile(output) as old, zipfile.ZipFile(bad, 'w') as new:
        manifest = json.loads(old.read('manifest.json'))
        payload = b'private data'
        manifest['files'].append(dict(path='vit/private-data.png', size=len(payload),
                                      sha256=hashlib.sha256(payload).hexdigest(),
                                      source_path=str(runs[1] / 'private-data.png')))
        for entry in old.infolist():
            new.writestr(entry, json.dumps(manifest).encode() if entry.filename == 'manifest.json' else old.read(entry))
        new.writestr('vit/private-data.png', payload)
    with pytest.raises(ValueError, match='Unallowlisted'):
        exporter.verify_bundle(bad)


def test_sidecar_collision_preserves_existing_file(exporter, runs, tmp_path):
    output = tmp_path / 'evidence.zip'
    sidecar = output.with_suffix('.manifest.json')
    sidecar.write_text('existing manifest')
    with pytest.raises(FileExistsError):
        exporter.export_bundle(*runs, output)
    assert not output.exists()
    assert sidecar.read_text() == 'existing manifest'


def test_verifier_enforces_archive_size_and_expected_hash(exporter, runs, tmp_path, monkeypatch):
    output = tmp_path / 'evidence.zip'
    result = exporter.export_bundle(*runs, output)
    assert exporter.verify_bundle(output, expected_cnn_sha=result['model_sha256']['tiny_unet']) == result
    with pytest.raises(ValueError, match='Model hash'):
        exporter.verify_bundle(output, expected_vit_sha='0' * 64)
    monkeypatch.setattr(exporter, 'MAX_FILE_BYTES', 32)
    with pytest.raises(ValueError, match='size limit'):
        exporter.verify_bundle(output)


def test_source_traversal_and_infinite_exponents_are_rejected(exporter, runs, tmp_path):
    cpp, vit = runs
    summary = cpp / 'summary.json'
    summary.write_text(summary.read_text().replace('0.29207300394773483', '1e999'))
    with pytest.raises(ValueError, match='Nonfinite'):
        exporter.export_bundle(cpp, vit, tmp_path / 'bad.zip')
    with pytest.raises(ValueError, match='Unsafe'):
        exporter.safe_name('vit/../../private.png')


def test_standalone_cli_export_requires_no_project_imports(exporter, runs, tmp_path):
    standalone = tmp_path / 'portable.py'
    shutil.copyfile(SCRIPT, standalone)
    output = tmp_path / 'evidence.zip'
    result = subprocess.run([sys.executable, '-I', str(standalone), '--cpp-run', str(runs[0]),
                             '--vit-run', str(runs[1]), '--output', str(output)],
                            cwd=tmp_path, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['integrity_verified'] is True
    assert exporter.verify_bundle(output)['scientific_audit_performed'] is False
    repeated = subprocess.run([sys.executable, '-I', str(standalone), '--cpp-run', str(runs[0]),
                               '--vit-run', str(runs[1]), '--output', str(output)],
                              cwd=tmp_path, text=True, capture_output=True)
    assert repeated.returncode == 1
    bad = tmp_path / 'wrong-hash.zip'
    mismatched = subprocess.run([sys.executable, '-I', str(standalone), '--cpp-run', str(runs[0]),
                                 '--vit-run', str(runs[1]), '--output', str(bad),
                                 '--expected-cnn-sha', '0' * 64],
                                cwd=tmp_path, text=True, capture_output=True)
    assert mismatched.returncode == 1
    assert 'Model hash differs' in mismatched.stderr
    assert not bad.exists()
