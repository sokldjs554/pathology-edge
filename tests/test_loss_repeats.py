"""Prevent partial/cherry-picked summaries and preserve failed repeat experiments."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]


def runner():
    spec = importlib.util.spec_from_file_location('loss_repeats', ROOT / 'scripts/run_loss_repeats.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write(path, value):
    path.write_text(json.dumps(value))


def dataset(tmp_path):
    data = tmp_path / 'data'
    data.mkdir()
    write(data / 'manifest.json', {'records': [dict(id=str(i), split=split)
          for i, split in enumerate(['train'] * 33 + ['validation'] * 10 + ['test'] * 7)]})
    return data


@pytest.fixture
def complete(tmp_path):
    module = runner()
    out = tmp_path / 'out'
    plan = module.freeze(source_repo(tmp_path), dataset(tmp_path), out)
    scores = {(20261110, 'bce_only'): .4, (20261110, 'learner_dice'): .5,
              (20261111, 'bce_only'): .5, (20261111, 'learner_dice'): .48,
              (20261112, 'bce_only'): .6, (20261112, 'learner_dice'): .6}
    for entry in plan['runs']:
        folder = out / entry['directory']
        folder.mkdir(parents=True)
        mode, seed = entry['mode'], entry['seed']
        config = dict(plan['reference_controls'], seed=seed, loss_mode=mode,
                      loss='BCE only' if mode == 'bce_only' else 'BCE + learner soft Dice')
        if mode == 'learner_dice':
            config['loss_source_sha256'] = plan['source_sha256']['learner_losses.py']
        score = scores[seed, mode]
        history = [dict(epoch=e, train_loss=.7,
                        validation_dice={'0.35': score, '0.5': score, '0.65': score - .1})
                   for e in range(1, 17)]
        model = (str(seed) + mode).encode()
        (folder / 'model.pt').write_bytes(model)
        (folder / 'manifest.json').write_bytes((out / 'manifest.json').read_bytes())
        write(folder / 'protocol.json', config)
        write(folder / 'training.json', dict(config=config, history=history,
              best_epoch=1, threshold=.35, best_validation_dice=score,
              seconds=10 if mode == 'bce_only' else 12,
              model_sha256=hashlib.sha256(model).hexdigest(),
              environment={'fixture': True}, train_images=33, validation_images=10,
              parameter_count=29761))
    return module, out, plan


def test_all_pairs_keep_negative_and_zero_deltas_and_sample_sd(complete):
    module, out, _ = complete
    result = module.summarize(out)
    assert len(result['runs']) == 6
    assert [p['delta_dice'] for p in result['pairs']] == pytest.approx([.1, -.02, 0])
    assert result['paired_delta']['mean'] == pytest.approx(.02666666666666667)
    assert result['paired_delta']['sample_sd'] == pytest.approx(.06429100507328637)
    assert result['paired_delta']['wins_ties_losses'] == [1, 1, 1]
    assert result['arms']['bce_only']['dice_mean'] == pytest.approx(.5)
    assert result['arms']['bce_only']['dice_sample_sd'] == pytest.approx(.1)
    assert result['arms']['learner_dice']['seconds_mean'] == 12
    assert result['test_evaluation_run'] is False


@pytest.mark.parametrize('damage', ['missing', 'model', 'manifest', 'source', 'environment',
                                  'config', 'selection', 'nan', 'score_range', 'epochs', 'extra'])
def test_incomplete_or_inconsistent_records_are_not_averaged(complete, damage):
    module, out, plan = complete
    folder = out / plan['runs'][-1]['directory']
    path = folder / 'training.json'
    report = json.loads(path.read_text())
    if damage == 'missing':
        path.unlink()
    elif damage in ('model', 'manifest'):
        (folder / ('model.pt' if damage == 'model' else 'manifest.json')).write_bytes(b'changed')
    elif damage == 'source':
        (out / 'source/pathology_edge/learner_losses.py').write_text('changed')
    elif damage == 'extra':
        (out / 'runs/extra').mkdir()
    else:
        if damage == 'environment': report['environment'] = {'different': True}
        if damage == 'config': report['config']['learning_rate'] = .2
        if damage == 'selection': report['best_epoch'] = 2  # same score, wrong first tie
        if damage == 'nan': report['history'][2]['validation_dice']['0.5'] = float('nan')
        if damage == 'score_range': report['history'][2]['validation_dice']['0.5'] = 1.1
        if damage == 'epochs': report['history'].pop()
        write(path, report)
    with pytest.raises((ValueError, FileNotFoundError)):
        module.summarize(out)
    assert not (out / 'summary.json').exists()


def test_existing_output_is_never_overwritten(tmp_path):
    module = runner()
    out = tmp_path / 'out'
    out.mkdir()
    original = out / 'model.pt'
    original.write_bytes(b'keep me')
    with pytest.raises(FileExistsError):
        module.freeze(ROOT, dataset(tmp_path), out)
    assert original.read_bytes() == b'keep me'


def source_repo(tmp_path):
    repo = tmp_path / 'repo'
    shutil.copytree(ROOT / 'src', repo / 'src', ignore=shutil.ignore_patterns('__pycache__', '*.so'))
    (repo / 'artifacts').mkdir()
    shutil.copyfile(ROOT / 'artifacts/protocol.json', repo / 'artifacts/protocol.json')
    subprocess.run(['git', 'init', '-q', str(repo)], check=True)
    subprocess.run(['git', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                    'commit', '-qm', 'fixture', '--allow-empty'], cwd=repo, check=True)
    return repo


def test_failure_preserves_snapshot_and_records_no_summary(tmp_path, monkeypatch):
    module = runner()
    repo = source_repo(tmp_path)
    out = tmp_path / 'out'
    data = dataset(tmp_path)
    before = (repo / 'src/pathology_edge/learner_losses.py').read_bytes()
    def fail_training(*args, **kwargs):
        raise subprocess.CalledProcessError(9, ['fixture failed train'])
    # Replace only the costly training subprocess; real freezing/status handling remains.
    monkeypatch.setattr(module, 'execute_training', fail_training)
    with pytest.raises(subprocess.CalledProcessError):
        module.run(repo, data, out)
    assert (out / 'source/pathology_edge/learner_losses.py').read_bytes() == before
    assert (repo / 'src/pathology_edge/learner_losses.py').read_bytes() == before
    assert json.loads((out / 'status.json').read_text())['status'] == 'failed'
    assert not (out / 'summary.json').exists()


def test_snapshot_copy_failure_replaces_stale_run_pointer(tmp_path, monkeypatch, capsys):
    module = runner()
    repo = source_repo(tmp_path)
    data, out = dataset(tmp_path), tmp_path / 'new-run'
    (repo / 'work').mkdir()
    pointer = repo / 'work/step42-repeat-run-path.txt'
    pointer.write_text('/older/completed/run\n')
    before = (repo / 'src/pathology_edge/learner_losses.py').read_bytes()
    def fail_copy(*args, **kwargs):
        raise OSError('fixture copy failure')
    monkeypatch.setattr(module.shutil, 'copyfile', fail_copy)
    with pytest.raises(OSError, match='fixture copy failure'):
        module.run(repo, data, out)
    assert pointer.read_text().strip() == str(out)
    assert json.loads((out / 'status.json').read_text())['status'] == 'failed'
    assert str(out) in capsys.readouterr().err
    assert not (out / 'summary.json').exists()
    assert (repo / 'src/pathology_edge/learner_losses.py').read_bytes() == before


def test_cli_summary_is_read_only(complete):
    _, out, _ = complete
    before = {str(p): p.read_bytes() for p in out.rglob('*') if p.is_file()}
    import sys
    completed = subprocess.run([sys.executable, str(ROOT / 'scripts/run_loss_repeats.py'),
                                '--summarize', str(out)], text=True, capture_output=True)
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)['paired_delta']['wins_ties_losses'] == [1, 1, 1]
    assert before == {str(p): p.read_bytes() for p in out.rglob('*') if p.is_file()}
