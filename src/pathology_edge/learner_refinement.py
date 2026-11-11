"""STEP_57: local residual head submitted by the user and independently tested."""
import torch
from torch import nn


def _validate_logits(logits: torch.Tensor) -> None:
    """Provided input guard; leave this helper unchanged."""
    if (not isinstance(logits, torch.Tensor) or logits.ndim != 4 or
            logits.shape[1] != 1 or any(size == 0 for size in logits.shape) or
            not logits.is_floating_point() or not torch.isfinite(logits).all()):
        raise ValueError('Expected finite floating nonempty B1HW logits')


class LocalResidualHead(nn.Module):
    """Raw logits -> same-shaped raw logits."""

    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv2d(
            1, 8, kernel_size=3, stride=1,
            padding=1, bias=True
        )
        self.conv2 = nn.Conv2d(
            8, 1, kernel_size=3, stride=1,
            padding=1, bias=True
        )

        nn.init.zeros_(self.conv2.weight)
        nn.init.zeros_(self.conv2.bias)

    def forward(self, logits: torch.Tensor) -> torch.Tensor:
        _validate_logits(logits)
        correction = self.conv2(
            torch.relu(self.conv1(logits))
        )

        return logits + correction
