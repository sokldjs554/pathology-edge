"""USER STEP 1. Intentionally unfinished. See docs/STEP_01.md.

No production fallback imports this file. Real PNG experiments stay in their
native pixel coordinates. General pyramid/model-scale support is pending.
"""
import numpy as np


def local_to_level0(
    points_xy: np.ndarray,
    origin_level0_xy: tuple[float, float],
    level_downsample: float,
    model_scale_xy: tuple[float, float],
) -> np.ndarray:
    """Map model-input pixel coordinates to level-0 pixel coordinates.

    Implement the contract in docs/STEP_01.md. Preserve the input.
    Return float64 (N, 2). Invalid values/shapes raise ValueError.
    """
    raise NotImplementedError("사용자 작성 예정: docs/STEP_01.md")

