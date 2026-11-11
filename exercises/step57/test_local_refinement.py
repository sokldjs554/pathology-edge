"""Opt-in user exercise: run explicitly after completing LocalResidualHead.

These tests are not part of the default project suite while the body is pending.
"""
import importlib.util
from pathlib import Path

import pytest
import torch
from torch import nn


@pytest.fixture
def head():
    path = Path(__file__).with_name('learner_refinement.py')
    if not path.exists():
        path = Path(__file__).parents[2] / 'src/pathology_edge/learner_refinement.py'
    spec = importlib.util.spec_from_file_location('submitted_refinement', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    torch.manual_seed(17)
    return module.LocalResidualHead()


def test_two_spatial_layers_have_expected_dimensions_and_parameters(head):
    for layer, incoming, outgoing in [(head.conv1, 1, 8), (head.conv2, 8, 1)]:
        assert isinstance(layer, nn.Conv2d)
        assert (layer.in_channels, layer.out_channels) == (incoming, outgoing)
        assert layer.kernel_size == (3, 3) and layer.padding == (1, 1)
        assert layer.stride == layer.dilation == (1, 1) and layer.groups == 1
        assert layer.bias is not None
    assert sum(p.numel() for p in head.parameters()) == 153


def test_last_layer_starts_at_zero_and_preserves_raw_logits(head):
    assert torch.count_nonzero(head.conv2.weight) == 0
    assert torch.count_nonzero(head.conv2.bias) == 0
    logits = torch.linspace(-3, 4, 77).reshape(1, 1, 7, 11)
    torch.testing.assert_close(head(logits), logits, rtol=0, atol=0)


@pytest.mark.parametrize('shape', [(2, 1, 13, 19), (1, 1, 1, 1)])
def test_shape_dtype_device_and_input_are_preserved(head, shape):
    head = head.double()
    logits = torch.randn(shape, dtype=torch.float64)
    original = logits.clone()
    output = head(logits)
    assert output.shape == logits.shape
    assert output.dtype == logits.dtype and output.device == logits.device
    torch.testing.assert_close(logits, original, rtol=0, atol=0)


def test_nonzero_correction_is_added_without_sigmoid(head):
    with torch.no_grad():
        head.conv1.weight.zero_(); head.conv1.bias.fill_(1)
        head.conv2.weight.zero_(); head.conv2.bias.zero_()
        head.conv2.weight[:, :, 1, 1].fill_(1 / 8)
    logits = torch.full((1, 1, 5, 7), 2.)
    torch.testing.assert_close(head(logits), torch.full_like(logits, 3.))


def test_relu_removes_negative_hidden_activation(head):
    with torch.no_grad():
        head.conv1.weight.zero_(); head.conv1.bias.fill_(-1)
        head.conv2.weight.fill_(1); head.conv2.bias.zero_()
    logits = torch.full((1, 1, 5, 7), -2.)
    torch.testing.assert_close(head(logits), logits)


def test_neighbor_pixel_can_change_output(head):
    with torch.no_grad():
        head.conv1.weight.zero_(); head.conv1.bias.zero_()
        head.conv2.weight.zero_(); head.conv2.bias.zero_()
        head.conv1.weight[0, 0, 1, 1] = 1
        head.conv2.weight[0, 0, 1, 2] = 1
    logits = torch.zeros(1, 1, 5, 7)
    logits[0, 0, 2, 3] = 1
    expected = logits.clone()
    expected[0, 0, 2, 2] = 1
    torch.testing.assert_close(head(logits), expected)


def test_gradients_reach_input_and_both_layers_over_two_steps(head):
    logits = torch.ones(2, 1, 7, 11, requires_grad=True)
    # Fix first-layer activations positive so the test does not depend on random ReLU gates.
    with torch.no_grad():
        head.conv1.weight.fill_(.1)
        head.conv1.bias.fill_(.1)
    optimizer = torch.optim.SGD(head.parameters(), lr=.01)
    head(logits).sum().backward()
    torch.testing.assert_close(logits.grad, torch.ones_like(logits))
    assert torch.isfinite(head.conv2.weight.grad).all()
    assert torch.count_nonzero(head.conv2.weight.grad) > 0
    # Zero final weights legitimately block conv1 gradients on the first step.
    assert torch.count_nonzero(head.conv1.weight.grad) == 0
    optimizer.step()
    optimizer.zero_grad()
    head(logits).sum().backward()
    assert torch.isfinite(head.conv1.weight.grad).all()
    assert torch.count_nonzero(head.conv1.weight.grad) > 0


@pytest.mark.parametrize('invalid', [torch.ones(1, 2, 3, 4), torch.ones(1, 3, 4),
                                    torch.ones(1, 1, 0, 4),
                                    torch.ones(1, 1, 3, 4, dtype=torch.int64),
                                    torch.full((1, 1, 3, 4), float('nan'))])
def test_provided_input_guard_remains_active(head, invalid):
    with pytest.raises(ValueError):
        head(invalid)
