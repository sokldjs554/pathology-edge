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
    raise NotImplementedError('사용자 작성 예정: docs/STEP_40.md')
