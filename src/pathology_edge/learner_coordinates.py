"""User-submitted STEP 1 implementation. See docs/STEP_01.md.

Codex reviewed and tested the submitted function without changing its algorithm.
The stored PNG/WSI experiments still use their existing native-coordinate path;
integration with a general pyramid/model-scale adapter remains separate work.
"""
import numpy as np


def local_to_level0(
    points_xy: np.ndarray,
    origin_level0_xy: tuple[float, float],
    level_downsample: float,
    model_scale_xy: tuple[float, float],
) -> np.ndarray:
    """모델 입력 좌표를 원본 슬라이드의 level-0 좌표로 변환합니다."""
    arrays = []

    for name, value in (
        ("points_xy", points_xy),
        ("origin_level0_xy", origin_level0_xy),
        ("level_downsample", level_downsample),
        ("model_scale_xy", model_scale_xy),
    ):
        try:
            array = np.asarray(value)

            # 정수·실수만 허용합니다.
            if array.dtype.kind not in "iuf":
                raise ValueError(f"{name} must contain real numbers.")

            array = array.astype(np.float64, copy=False)

        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError(f"{name} must contain real numbers.") from exc

        if not np.isfinite(array).all():
            raise ValueError(f"{name} must contain only finite values.")

        arrays.append(array)

    points, origin, downsample, scale = arrays

    if points.ndim != 2 or points.shape[1] != 2:
        raise ValueError("points_xy must have shape (N, 2).")

    if origin.shape != (2,):
        raise ValueError("origin_level0_xy must have shape (2,).")

    if downsample.ndim != 0 or downsample <= 0:
        raise ValueError("level_downsample must be a positive scalar.")

    if scale.shape != (2,) or np.any(scale <= 0):
        raise ValueError("model_scale_xy must have shape (2,) and be positive.")

    return origin + (points / scale) * downsample

