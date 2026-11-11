"""Provided guard; the reserved student model body has separate opt-in tests."""
import pytest
import torch


def guard():
    from pathology_edge.learner_refinement import _validate_logits
    return _validate_logits


@pytest.mark.parametrize('value', [None, [[1.]], torch.ones(1, 2, 4, 4),
                                  torch.ones(1, 1, 0, 4), torch.ones(1, 3, 4),
                                  torch.ones(1, 1, 4, 4, dtype=torch.int64),
                                  torch.full((1, 1, 4, 4), float('nan')),
                                  torch.full((1, 1, 4, 4), float('inf'))])
def test_invalid_logits_rejected(value):
    with pytest.raises(ValueError):
        guard()(value)


def test_guard_preserves_valid_tensor_and_autograd():
    x = torch.randn(2, 1, 7, 11, dtype=torch.float64, requires_grad=True)
    before = x.detach().clone()
    assert guard()(x) is None
    torch.testing.assert_close(x, before)
    x.sum().backward()
    torch.testing.assert_close(x.grad, torch.ones_like(x))
