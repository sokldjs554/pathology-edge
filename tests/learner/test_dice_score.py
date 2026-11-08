"""Codex-provided acceptance tests for the reviewed user Dice implementation."""
import numpy as np
import pytest

from pathology_edge.learner_metrics import dice_score

# STEP 4 was submitted and reviewed; include these tests in the default suite.


def test_known_overlap_and_input_preservation():
    prediction = np.array([[1, 1], [0, 0]], dtype=np.uint8)
    target = np.array([[1, 0], [1, 0]], dtype=np.uint8)
    before_p, before_t = prediction.copy(), target.copy()
    result = dice_score(prediction, target)
    assert type(result) is float
    assert result == pytest.approx(0.5)
    np.testing.assert_array_equal(prediction, before_p)
    np.testing.assert_array_equal(target, before_t)


def test_region_selects_evaluation_pixels_and_preserves_region():
    prediction = np.array([[1, 1], [0, 0]], dtype=np.float64)
    target = np.array([[1, 0], [1, 0]], dtype=np.float32)
    region = np.array([[True, True], [False, False]])
    before = region.copy()
    assert dice_score(prediction, target, region) == pytest.approx(2 / 3)
    np.testing.assert_array_equal(region, before)


@pytest.mark.parametrize("prediction,target,expected", [
    ([[1, 0], [0, 1]], [[1, 0], [0, 1]], 1.0),
    ([[1, 0], [0, 0]], [[0, 1], [0, 0]], 0.0),
    ([[0, 0], [0, 0]], [[0, 0], [0, 0]], 1.0),
    ([[1, 0], [0, 0]], [[0, 0], [0, 0]], 0.0),
    ([[0, 0], [0, 0]], [[1, 0], [0, 0]], 0.0),
])
def test_foreground_agreement_cases(prediction, target, expected):
    result = dice_score(np.asarray(prediction, dtype=bool),
                        np.asarray(target, dtype=bool))
    assert type(result) is float
    assert result == pytest.approx(expected)


def test_read_only_uint8_masks_do_not_overflow_counts():
    prediction = np.ones((32, 32), dtype=np.uint8)
    target = prediction.copy()
    prediction.flags.writeable = False
    target.flags.writeable = False
    assert dice_score(prediction, target) == pytest.approx(1.0)


@pytest.mark.parametrize("prediction,target,region", [
    (np.zeros((2, 3)), np.zeros((2, 2)), None),
    (np.zeros(2), np.zeros(2), None),
    (np.zeros((0, 2)), np.zeros((0, 2)), None),
    (np.full((2, 2), 0.25), np.zeros((2, 2)), None),
    (np.zeros((2, 2)), np.full((2, 2), 2), None),
    (np.array([[0., 0.], [0., np.nan]]), np.zeros((2, 2)),
     np.array([[True, True], [False, False]])),
    (np.zeros((2, 2)), np.full((2, 2), np.inf), None),
    (np.full((2, 2), 1j), np.zeros((2, 2)), None),
    (np.array([["1", "0"], ["0", "0"]]), np.zeros((2, 2)), None),
    (np.zeros((2, 2)), np.zeros((2, 2)), np.ones((1, 2), dtype=bool)),
    (np.zeros((2, 2)), np.zeros((2, 2)), np.ones((2, 2), dtype=np.uint8)),
    (np.zeros((2, 2)), np.zeros((2, 2)), np.zeros((2, 2), dtype=bool)),
])
def test_invalid_inputs_raise_value_error(prediction, target, region):
    with pytest.raises(ValueError):
        dice_score(prediction, target, region)
