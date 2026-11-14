import numpy as np
import pytest
from pathology_edge.ki67_evaluation import match_points, evaluate_cells, positive_fraction


def test_matching_maximizes_cardinality_before_distance():
    assert match_points([[2, 0], [-2, 0]], [[0, 0], [5, 0]], 3) == [(0, 1), (1, 0)]


def test_one_to_one_and_radius_inclusive():
    assert match_points([[0, 0], [0, 1]], [[0, 0]], 1) == [(0, 0)]
    assert match_points([[6, 0]], [[0, 0]], 6) == [(0, 0)]
    assert match_points([[6.01, 0]], [[0, 0]], 6) == []


def test_wrong_class_costs_both_fp_and_fn():
    r = evaluate_cells([[1, 1], [90, 90]], [1, 0], [[1, 1], [20, 20]], [0, 2])
    assert r['localization'] == {'tp': 1, 'fp': 1, 'fn': 1, 'precision': .5, 'recall': .5, 'f1': .5}
    assert r['matched_accuracy'] == 0
    assert r['classes'][0]['fp'] == 1 and r['classes'][0]['fn'] == 1
    assert r['classes'][1]['fp'] == 1 and r['classes'][2]['fn'] == 1
    assert r['macro_f1'] == 0


def test_empty_predictions_are_misses_and_ratio_undefined():
    r = evaluate_cells(np.empty((0, 2)), [], [[2, 2]], [0])
    assert r['localization']['fn'] == 1
    assert r['matched_accuracy'] is None
    assert positive_fraction([])['fraction'] is None
    assert positive_fraction([2, 3])['tumor_cells'] == 0
    assert positive_fraction([0, 0, 1, 3]) == {'positive_tumor_cells': 2, 'tumor_cells': 3, 'fraction': 2/3}


@pytest.mark.parametrize('points,radius', [([[np.nan, 0]], 6), ([1, 2], 6), ([[1, 2]], 0)])
def test_invalid_points(points, radius):
    with pytest.raises(ValueError):
        match_points(points, [[0, 0]], radius)


@pytest.mark.parametrize('classes', [[4], [.5], [True]])
def test_invalid_classes(classes):
    with pytest.raises(ValueError):
        positive_fraction(classes)
