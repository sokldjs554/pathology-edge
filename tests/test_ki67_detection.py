import numpy as np
import pytest
from pathology_edge.ki67_detection import detect_centers, select_peaks


def test_blank_has_no_candidates():
    result = detect_centers(np.full((32, 32, 3), 255, np.uint8))
    assert result['points_xy'].shape == (0, 2)
    assert result['scores'].shape == (0,)


def test_two_dark_centers_are_found():
    yy, xx = np.mgrid[:40, :48]
    od = sum(np.exp(-((xx-x)**2+(yy-y)**2)/8) for x, y in [(10, 13), (35, 27)])
    rgb = np.repeat((255*np.exp(-od))[..., None], 3, axis=2).astype(np.uint8)
    found = detect_centers(rgb, {'min_response': .1, 'min_distance': 6})
    assert set(map(tuple, found['points_xy'])) == {(10, 13), (35, 27)}


def test_peak_ties_and_border_are_deterministic():
    response = np.zeros((12, 12))
    response[0, 0] = response[0, 3] = response[9, 9] = 1
    points, scores = select_peaks(response, .1, 4)
    assert points.tolist() == [[0, 0], [9, 9]]
    assert scores.tolist() == [1, 1]
    assert len(select_peaks(response, .1, 3)[0]) == 3


@pytest.mark.parametrize('config', [{'min_response': 0}, {'min_distance': -1}, {'min_response': float('nan')}, {'unknown': 1}])
def test_invalid_config(config):
    with pytest.raises(ValueError):
        detect_centers(np.zeros((8, 8, 3), np.uint8), config)


@pytest.mark.parametrize('rgb', [np.zeros((8, 8)), np.zeros((8, 8, 3)), np.zeros((0, 8, 3), np.uint8)])
def test_invalid_image(rgb):
    with pytest.raises(ValueError):
        detect_centers(rgb)
