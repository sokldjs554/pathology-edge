"""User exercise contracts: opt in with --run-learner; no answer implementation."""
import pytest
import torch

pytestmark = pytest.mark.learner


@pytest.mark.parametrize("dtype", [torch.float32, torch.float64])
def test_hand_calculated_loss_and_scalar_tensor(dtype):
    from pathology_edge.learner_losses import soft_dice_loss
    x = torch.zeros((1, 1, 2, 2), dtype=dtype)
    y = torch.tensor([[[[1., 0.], [1., 0.]]]], dtype=dtype)
    value = soft_dice_loss(x, y)
    assert isinstance(value, torch.Tensor) and value.ndim == 0
    assert value.dtype == x.dtype and value.device == x.device
    assert value.item() == pytest.approx(0.4)


def test_empty_foreground_still_penalizes_predicted_probability():
    from pathology_edge.learner_losses import soft_dice_loss
    x = torch.zeros(1, 1, 2, 2)
    assert soft_dice_loss(x, torch.zeros_like(x)).item() == pytest.approx(2 / 3)


def test_batch_averages_per_image_not_pooled_pixels():
    from pathology_edge.learner_losses import soft_dice_loss
    x = torch.zeros(2, 1, 2, 2)
    y = torch.zeros_like(x)
    y[0] = 1
    # Image losses are 2/7 and 2/3, averaging to 10/21.
    assert soft_dice_loss(x, y).item() == pytest.approx(10 / 21)


def test_nondefault_smoothing():
    from pathology_edge.learner_losses import soft_dice_loss
    x = torch.zeros(1, 1, 2, 2)
    y = torch.tensor([[[[1., 0.], [1., 0.]]]])
    assert soft_dice_loss(x, y, smooth=2.0).item() == pytest.approx(1 / 3)


def test_extreme_correct_logits_remain_finite():
    from pathology_edge.learner_losses import soft_dice_loss
    x = torch.tensor([[[[-1000., 1000.]]]], requires_grad=True)
    y = torch.tensor([[[[0., 1.]]]])
    loss = soft_dice_loss(x, y)
    assert torch.isfinite(loss) and loss.item() == pytest.approx(0.0)
    loss.backward()
    assert torch.isfinite(x.grad).all()


def test_backward_moves_foreground_and_background_in_correct_directions():
    from pathology_edge.learner_losses import soft_dice_loss
    x = torch.zeros(1, 1, 2, 2, requires_grad=True)
    y = torch.tensor([[[[1., 0.], [1., 0.]]]])
    soft_dice_loss(x, y).backward()
    assert torch.isfinite(x.grad).all()
    assert (x.grad[y == 1] < 0).all()
    assert (x.grad[y == 0] > 0).all()


def test_gradcheck():
    from pathology_edge.learner_losses import soft_dice_loss
    x = torch.tensor([[[[-.7, .2], [1.1, -.3]]]], dtype=torch.float64, requires_grad=True)
    y = torch.tensor([[[[1., 0.], [1., 0.]]]], dtype=torch.float64)
    assert torch.autograd.gradcheck(lambda z: soft_dice_loss(z, y), (x,))
