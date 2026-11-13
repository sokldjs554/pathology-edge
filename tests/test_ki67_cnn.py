import inspect
import numpy as np
import pytest
import torch
from pathology_edge.ki67_cnn import cell_crops, CellClassifier, classify_centers, predict_image


def test_crop_center_order_and_white_padding():
    rgb = np.zeros((40, 50, 3), np.uint8)
    rgb[0, 0] = [20, 30, 40]
    rgb[10, 20] = [60, 70, 80]
    crops = cell_crops(rgb, [[0, 0], [20, 10]])
    assert crops.shape == (2, 48, 48, 3)
    assert crops[0, 24, 24].tolist() == [20, 30, 40]
    assert crops[1, 24, 24].tolist() == [60, 70, 80]
    assert (crops[0, :24] == 255).all()
    assert cell_crops(rgb, np.empty((0, 2))).shape == (0, 48, 48, 3)


@pytest.mark.parametrize('points', [[[50, 0]], [[-.1, 0]], [[1.5, 2]]])
def test_invalid_centers(points):
    with pytest.raises(ValueError):
        cell_crops(np.zeros((40, 50, 3), np.uint8), points)


def test_model_shape_and_gradient():
    torch.manual_seed(1)
    model = CellClassifier()
    logits = model(torch.rand(3, 3, 48, 48))
    assert logits.shape == (3, 4)
    torch.nn.functional.cross_entropy(logits, torch.tensor([0, 1, 2])).backward()
    assert all(p.grad is not None and torch.isfinite(p.grad).all() for p in model.parameters())
    assert any(torch.count_nonzero(p.grad) for p in model.parameters())


def test_inference_is_image_only_and_empty_is_valid():
    assert list(inspect.signature(predict_image).parameters) == ['rgb', 'detector', 'classifier']
    model = CellClassifier()
    rgb = np.full((48, 48, 3), 255, np.uint8)
    result = predict_image(rgb, {}, model)
    assert result['points_xy'].shape == (0, 2)
    assert result['positive_fraction']['fraction'] is None
    probabilities = classify_centers(rgb, [[10, 10], [30, 30]], model)
    assert probabilities.shape == (2, 4)
    np.testing.assert_allclose(probabilities.sum(axis=1), 1, atol=1e-6)


def test_wrong_model_rejected_even_with_no_centers():
    with pytest.raises(ValueError):
        classify_centers(np.zeros((32, 32, 3), np.uint8), np.empty((0, 2)), {})
