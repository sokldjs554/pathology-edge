"""Saved-pixel error analysis must not invent improvements or select test cases."""
import importlib.util
from pathlib import Path

import numpy as np
import pytest

SCRIPT = Path(__file__).parents[1] / 'scripts/analyze_model_errors.py'


@pytest.fixture
def analysis():
    assert SCRIPT.exists(), 'saved-output analysis is not implemented'
    spec = importlib.util.spec_from_file_location('error_analysis', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_changed_pixels_count_corrections_not_nuclei(analysis):
    target = np.array([[1, 1, 0], [0, 0, 1]], bool)
    cnn = np.array([[1, 0, 1], [0, 0, 1]], bool)
    vit = np.array([[1, 1, 0], [1, 0, 1]], bool)
    counts = analysis.compare_masks(cnn, vit, target)
    assert counts['corrected_pixels'] == 2
    assert counts['worsened_pixels'] == 1
    assert counts['changed_pixels'] == 3
    assert counts['cnn']['fp'] == counts['cnn']['fn'] == 1
    assert counts['vit']['fp'] == 1 and counts['vit']['fn'] == 0
    assert counts['cnn']['dice'] == pytest.approx(2 / 3)
    assert counts['vit']['dice'] == pytest.approx(6 / 7)


def test_selection_has_no_fabricated_direction_and_stable_ties(analysis):
    rows = [dict(id='b', delta_dice=.2), dict(id='a', delta_dice=.2),
            dict(id='c', delta_dice=0)]
    assert analysis.select_cases(rows) == {'improved': 'a', 'worsened': None}
    rows.append(dict(id='d', delta_dice=-.1))
    assert analysis.select_cases(rows)['worsened'] == 'd'


def test_crop_uses_net_pixel_change_and_includes_far_edge(analysis):
    target = np.zeros((10, 11), bool)
    cnn = target.copy()
    vit = target.copy()
    vit[8:, 9:] = True
    assert analysis.select_crop(cnn, vit, target, 'worsened', size=4, step=4) == [7, 6, 11, 10]
    # Equal scores choose topmost then leftmost, with width/height clipped.
    assert analysis.select_crop(cnn, cnn, target, 'improved', size=128) == [0, 0, 11, 10]


@pytest.mark.parametrize('bad', [np.ones((2, 2)), np.zeros((3, 2), bool),
                               np.array([[0, 2], [0, 0]])])
def test_invalid_masks_rejected_before_pixel_accounting(analysis, bad):
    with pytest.raises(ValueError):
        analysis.compare_masks(bad, np.zeros((2, 2), bool), np.zeros((2, 2), bool))


def test_error_colors_have_exact_count_correspondence(analysis):
    target = np.array([[1, 0], [1, 0]], bool)
    pred = np.array([[1, 1], [0, 0]], bool)
    rgb = analysis.error_rgb(pred, target)
    assert rgb.shape == (2, 2, 3)
    assert (rgb[0, 1] == analysis.FP_COLOR).all()
    assert (rgb[1, 0] == analysis.FN_COLOR).all()
    assert (rgb[0, 0] == analysis.TP_COLOR).all()
    assert (rgb[1, 1] == analysis.BG_COLOR).all()


def test_existing_output_not_overwritten_even_without_valid_run(analysis, tmp_path):
    (tmp_path / 'sentinel').write_text('preserve')
    with pytest.raises(FileExistsError):
        analysis.analyze(tmp_path / 'absent', tmp_path / 'data', tmp_path,
                         provenance_label='development-reference')
    assert (tmp_path / 'sentinel').read_text() == 'preserve'


def test_full_saved_output_audit_renders_and_rejects_tampered_pixels(analysis, tmp_path):
    # Reuse the complete evidence fixture, not a mock of the scientific auditor.
    fixture_path = Path(__file__).with_name('test_model_repeats.py')
    spec = importlib.util.spec_from_file_location('pair_fixture', fixture_path)
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    pair = fixture.load_script('run_model_comparison')
    data = fixture.data.__wrapped__(tmp_path, pair)
    run = fixture.completed_pair(pair, tmp_path / 'run', data)
    before = {p: pair.sha(p) for p in run.rglob('*') if p.is_file()}
    report = analysis.analyze(run, data, tmp_path / 'report',
                              provenance_label='development-reference')
    assert report['prediction_audit_regions'] == 60
    assert report['model_inference_run'] is False
    assert len(report['rows']) == 10 and len(report['cases']) == 1
    assert report['cases'][0]['direction'] == 'worsened'
    assert (tmp_path / 'report' / 'worsened-crop.png').is_file()
    assert (tmp_path / 'report' / 'index.html').is_file()
    assert {p: pair.sha(p) for p in before} == before
    prediction = next((run / 'small_vit' / 'predictions').glob('*.npy'))
    np.save(prediction, np.ones((256, 256), np.float32))
    with pytest.raises(ValueError, match='Prediction hash'):
        analysis.analyze(run, data, tmp_path / 'invalid-report',
                         provenance_label='user-codespaces')
    assert not (tmp_path / 'invalid-report').exists()


def test_mutation_during_render_never_leaves_completed_report(analysis, tmp_path, monkeypatch):
    fixture_path = Path(__file__).with_name('test_model_repeats.py')
    spec = importlib.util.spec_from_file_location('pair_fixture', fixture_path)
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    pair = fixture.load_script('run_model_comparison')
    data = fixture.data.__wrapped__(tmp_path, pair)
    run = fixture.completed_pair(pair, tmp_path / 'run', data)
    original_write = analysis._write_html
    def mutate_during_render(out, result):
        original_write(out, result)
        path = next((run / 'small_vit' / 'predictions').glob('*.npy'))
        np.save(path, np.zeros((256, 256), np.float32))
    monkeypatch.setattr(analysis, '_write_html', mutate_during_render)
    output = tmp_path / 'report'
    with pytest.raises(ValueError, match='Inputs changed while rendering'):
        analysis.analyze(run, data, output, provenance_label='development-reference')
    assert not (output / 'index.html').exists()
    assert not (output / 'report.json').exists()
    assert pair.read(output / 'status.json')['status'] == 'failed'
