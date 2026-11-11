"""STEP_57: user-owned local residual head. Training waits for these bodies."""
import torch
from torch import nn


def _validate_logits(logits: torch.Tensor) -> None:
    """Provided input guard; leave this helper unchanged."""
    if (not isinstance(logits, torch.Tensor) or logits.ndim != 4 or
            logits.shape[1] != 1 or any(size == 0 for size in logits.shape) or
            not logits.is_floating_point() or not torch.isfinite(logits).all()):
        raise ValueError('Expected finite floating nonempty B1HW logits')


class LocalResidualHead(nn.Module):
    """Raw logits -> same-shaped raw logits; requirements in docs/STEP_57.md."""

    def __init__(self):
        super().__init__()
        # User: define conv1/conv2 and zero-initialize conv2 weight and bias.
        raise NotImplementedError('사용자 작성 예정: docs/STEP_57.md (__init__)')

    def forward(self, logits: torch.Tensor) -> torch.Tensor:
        _validate_logits(logits)
        # User: local nonlinear correction plus the original logits.
        raise NotImplementedError('사용자 작성 예정: docs/STEP_57.md (forward)')
