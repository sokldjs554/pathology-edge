"""STEP_40: user-owned connection from ROI metadata to the accepted transform."""
import numpy as np

from .learner_coordinates import local_to_level0
from .wsi_roi import RoiGeometry


def roi_points_to_level0(points_xy: np.ndarray, geometry: RoiGeometry) -> np.ndarray:
    """Map continuous model-frame edge coordinates; see docs/STEP_40.md.

    Codex provides the type guard. The user derives the x/y resize scales from
    actual read/model dimensions and delegates to their local_to_level0.
    """
    if not isinstance(geometry, RoiGeometry):
        raise ValueError('geometry must be a RoiGeometry')
    # 사용자 작성 범위: 아래 예외를 메타데이터 연결과 반환으로 바꾸세요.
    model_width, model_height = geometry.model_size_wh
    read_width, read_height = geometry.read_size_wh
    model_scale_xy = (model_width / read_width, model_height / read_height)
    return local_to_level0(
        points_xy,
        geometry.origin_level0_xy,
        geometry.level_downsample,
        model_scale_xy,
    )
