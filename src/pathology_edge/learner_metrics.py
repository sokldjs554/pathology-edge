"""USER STEP 4. Independent Dice calculation; see docs/STEP_04.md.

The production experiment still uses metrics.binary_metrics. This exercise
does not replace it or change any stored experiment results.
"""
from __future__ import annotations

import numpy as np


def dice_score(
    prediction: np.ndarray,
    target: np.ndarray,
    region: np.ndarray | None = None,
) -> float:
    """Compute foreground Dice on valid binary HW masks in the selected region.

    Follow the input validation and empty-foreground policy in docs/STEP_04.md.
    Preserve all inputs and return a Python float. Invalid inputs raise ValueError.
    """
    raise NotImplementedError("사용자 작성 예정: docs/STEP_04.md")
