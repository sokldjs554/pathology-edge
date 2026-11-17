"""Explicit categorical grid normalization for an already verified common ROI.

This module does not establish registration or recover historical subpixel
annotations. The caller must first verify source/target identity and level-0
extent. Accept only an at-most-one-pixel axis difference; use RGB as the fixed
target grid. Half-pixel nearest-neighbor sampling copies complete label tuples.
"""
from dataclasses import dataclass
import numpy as np
from scipy.ndimage import zoom


def _size_wh(value):
    try:
        w, h = value
    except (TypeError, ValueError) as exc:
        raise ValueError('Expected width/height pair') from exc
    if any(isinstance(n, (bool, np.bool_)) or not isinstance(n, (int, np.integer))
           or not 0 < n < 2**31 for n in (w, h)):
        raise ValueError('Positive integer width/height required')
    return int(w), int(h)


@dataclass(frozen=True)
class AnnotationGrid:
    source_wh: tuple[int, int]
    target_wh: tuple[int, int]

    def __post_init__(self):
        source, target = _size_wh(self.source_wh), _size_wh(self.target_wh)
        if any(abs(a-b) > 1 for a, b in zip(source, target)):
            raise ValueError('Axis mismatch exceeds the verified one-pixel scope')
        object.__setattr__(self, 'source_wh', source)
        object.__setattr__(self, 'target_wh', target)

    @property
    def is_identity(self):
        return self.source_wh == self.target_wh

    def indices_xy(self):
        """Match the pinned SciPy order0/grid-mode convention, including float ties."""
        return tuple(zoom(np.arange(src, dtype=np.int64), dst/src,
                          order=0, grid_mode=True, prefilter=False, mode='nearest')
                     for src, dst in zip(self.source_wh, self.target_wh))

    def resample(self, array):
        """Sample HW or HWC categorical data, preserving dtype and channel tuples."""
        if (not isinstance(array, np.ndarray) or array.ndim not in (2, 3)
                or array.dtype.kind not in 'biu' or not array.size
                or array.shape[:2] != self.source_wh[::-1]):
            raise ValueError('Aligned nonempty integer/bool HW or HWC array required')
        x, y = self.indices_xy()
        return array[y[:, None], x[None, :]].copy()

    def _map_edges(self, points_xy, source, target):
        points = np.asarray(points_xy)
        if (points.ndim != 2 or points.shape[1] != 2 or points.dtype.kind not in 'iuf'
                or not np.isfinite(points).all()):
            raise ValueError('Finite real (N, 2) edge-coordinate points required')
        return points.astype(np.float64) / np.asarray(source) * np.asarray(target)

    def to_target_edges(self, points_xy):
        """Continuous edges: (0,0)..(source W,H) -> (0,0)..(target W,H)."""
        return self._map_edges(points_xy, self.source_wh, self.target_wh)

    def to_source_edges(self, points_xy):
        return self._map_edges(points_xy, self.target_wh, self.source_wh)

    def metadata(self):
        return dict(source_wh=list(self.source_wh), target_wh=list(self.target_wh),
                    identity=self.is_identity,
                    edge_scale_xy=[b/a for a,b in zip(self.source_wh,self.target_wh)],
                    sampling='SciPy zoom(order=0, grid_mode=True, prefilter=False, mode=nearest) on source indices',
                    interpolation='nearest; complete categorical tuples; no anti-aliasing',
                    prerequisite='Same ROI and level0 extent verified by caller')
