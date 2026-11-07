import numpy as np
import pytest
from pathology_edge.learner_coordinates import local_to_level0

pytestmark = pytest.mark.learner


def test_known_example_and_no_mutation():
    a = np.array([[10, 20], [0, 0]], dtype=np.int32)
    before = a.copy()
    b = local_to_level0(a, (1000, 2000), 4, (0.5, 0.25))
    np.testing.assert_allclose(b, [[1080, 2320], [1000, 2000]])
    assert b.dtype == np.float64
    np.testing.assert_array_equal(a, before)


def test_empty():
    assert local_to_level0(np.empty((0, 2)), (0, 0), 1, (1, 1)).shape == (0, 2)


def test_fractional_origin_and_subpixel():
    np.testing.assert_allclose(
        local_to_level0(np.array([[0.25, 1.5]]), (0.5, 1.25), 1.5, (1, 0.5)),
        [[0.875, 5.75]],
    )


@pytest.mark.parametrize("points,origin,downsample,scale", [
    (np.zeros((2, 3)), (0, 0), 1, (1, 1)),
    (np.zeros((2,)), (0, 0), 1, (1, 1)),
    (np.array([[np.nan, 0]]), (0, 0), 1, (1, 1)),
    (np.zeros((1, 2)), (0,), 1, (1, 1)),
    (np.zeros((1, 2)), (0, float('inf')), 1, (1, 1)),
    (np.zeros((1, 2)), (0, 0), 0, (1, 1)),
    (np.zeros((1, 2)), (0, 0), 1, (0, 1)),
    (np.zeros((1, 2)), (0, 0), float('inf'), (1, 1)),
    (np.zeros((1, 2)), (0, 0), 1, (-1, 1)),
])
def test_invalid(points, origin, downsample, scale):
    with pytest.raises(ValueError):
        local_to_level0(points, origin, downsample, scale)

