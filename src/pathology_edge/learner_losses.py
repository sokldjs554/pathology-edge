"""STEP_35: Codex provides validation; the user implements differentiable Dice."""
import math
from numbers import Real

import torch


def _validate_loss_inputs(logits, target, smooth):
    """Provided infrastructure; keep this separate from the learner calculation."""
    if not isinstance(logits, torch.Tensor) or not isinstance(target, torch.Tensor):
        raise ValueError("logits and target must be torch tensors")
    if logits.ndim != 4 or logits.shape[1] != 1 or logits.numel() == 0:
        raise ValueError("logits must have nonempty shape (N, 1, H, W)")
    if target.shape != logits.shape:
        raise ValueError("target must have the same shape as logits")
    if not logits.is_floating_point() or not target.is_floating_point():
        raise ValueError("logits and target must have floating dtypes")
    if logits.dtype != target.dtype or logits.device != target.device:
        raise ValueError("logits and target must share dtype and device")
    if not torch.isfinite(logits).all() or not torch.isfinite(target).all():
        raise ValueError("logits and target must contain finite values")
    if not torch.all((target == 0) | (target == 1)):
        raise ValueError("target must contain only 0 and 1")
    if isinstance(smooth, bool) or not isinstance(smooth, Real) or not math.isfinite(smooth) or smooth <= 0:
        raise ValueError("smooth must be a finite positive real scalar")


def soft_dice_loss(
    logits: torch.Tensor,
    target: torch.Tensor,
    smooth: float = 1.0,
) -> torch.Tensor:
    """Return scalar image-macro soft Dice loss, preserving autograd. See STEP_35."""
    _validate_loss_inputs(logits, target, smooth)
    probabilities = torch.sigmoid(logits)
    spatial_axes = (1, 2, 3)

    overlap = (probabilities * target).sum(dim=spatial_axes)
    predicted = probabilities.sum(dim=spatial_axes)
    actual = target.sum(dim=spatial_axes)

    dice_per_image = (2 * overlap + smooth) / (predicted + actual + smooth)
    return (1 - dice_per_image).mean()
