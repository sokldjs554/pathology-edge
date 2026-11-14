"""User-submitted STEP 4 Dice implementation; see docs/STEP_04.md.

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
    # 평가 영역 밖을 포함해 전체 입력을 검사합니다.
    for name, mask in (("prediction", prediction), ("target", target)):
        if not isinstance(mask, np.ndarray):
            raise ValueError(f"{name} must be a NumPy array.")

        if mask.ndim != 2 or mask.size == 0:
            raise ValueError(f"{name} must be a non-empty 2D array.")

        if mask.dtype.kind not in "biuf":
            raise ValueError(
                f"{name} must have a bool, integer, or real dtype."
            )

        if not np.all((mask == 0) | (mask == 1)):
            raise ValueError(f"{name} must contain only 0 and 1.")

    if prediction.shape != target.shape:
        raise ValueError(
            "prediction and target must have the same shape."
        )

    if region is None:
        pred_values, target_values = prediction, target
    else:
        if not isinstance(region, np.ndarray):
            raise ValueError("region must be a NumPy array.")

        if region.dtype.kind != "b" or region.shape != prediction.shape:
            raise ValueError(
                "region must be a bool array with the same shape as the masks."
            )

        if not np.any(region):
            raise ValueError("region must select at least one pixel.")

        pred_values, target_values = prediction[region], target[region]

    pred_count = int(np.count_nonzero(pred_values))
    target_count = int(np.count_nonzero(target_values))
    total = pred_count + target_count

    if total == 0:
        return 1.0

    intersection = int(
        np.count_nonzero(np.logical_and(pred_values, target_values))
    )
    return float(2 * intersection / total)
