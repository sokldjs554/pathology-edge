"""WSI ROI reading/resize metadata, independent of inference and public exports.

Origins use level-0 pixels; read sizes use the selected OpenSlide level. Geometry
describes continuous pixel-edge coordinates. It does not silently convert model
pixel-center indices, run a model, or establish clinical accuracy.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from numbers import Integral, Real

import numpy as np
from PIL import Image


def _pair(value, name, *, allow_zero=False):
    try:
        result = tuple(value)
        if len(result) != 2 or any(isinstance(v, (bool, np.bool_)) or
                                   not isinstance(v, Integral) for v in result):
            raise ValueError
        result = tuple(int(v) for v in result)
        if any(v < (0 if allow_zero else 1) or not math.isfinite(v) for v in result):
            raise ValueError
        return result
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f'{name} must be a pair of {"nonnegative" if allow_zero else "positive"} integers') from exc


def _level(value):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Integral) or value < 0:
        raise ValueError('level must be a nonnegative integer')
    return int(value)


def _downsample(value):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        raise ValueError('level_downsample must be finite and positive')
    try:
        result = float(value)
    except (ValueError, OverflowError) as exc:
        raise ValueError('level_downsample must be finite and positive') from exc
    if not math.isfinite(result) or result <= 0:
        raise ValueError('level_downsample must be finite and positive')
    return result


@dataclass(frozen=True)
class RoiGeometry:
    origin_level0_xy: tuple[int, int]
    level: int
    level_downsample: float
    read_size_wh: tuple[int, int]
    model_size_wh: tuple[int, int]
    slide_size_level0_wh: tuple[int, int]

    def __post_init__(self):
        for name in ('origin_level0_xy', 'read_size_wh', 'model_size_wh', 'slide_size_level0_wh'):
            object.__setattr__(self, name, _pair(getattr(self, name), name,
                                               allow_zero=name == 'origin_level0_xy'))
        object.__setattr__(self, 'level', _level(self.level))
        object.__setattr__(self, 'level_downsample', _downsample(self.level_downsample))
        for origin, size, limit in zip(self.origin_level0_xy, self.read_size_wh,
                                       self.slide_size_level0_wh):
            if origin >= limit or size > (limit - origin) / self.level_downsample:
                raise ValueError('The complete read footprint must fit inside the slide')


@dataclass(frozen=True)
class RoiRead:
    image: np.ndarray
    valid_mask: np.ndarray
    geometry: RoiGeometry
    requested_size_wh: tuple[int, int]


def read_roi(slide, origin_level0_xy, level, read_size_wh, model_size_wh=None):
    """Read with a caller-owned OpenSlide handle; clip before deriving resize scale.

    The right/bottom crop keeps only complete selected-level pixel footprints.
    RGB is white-composited and optionally resized bilinearly. ``valid_mask``
    is a nearest-neighbor sample of the source alpha==255 mask, not a promise
    that every interpolation-kernel contributor is opaque. No handle is closed.
    """
    origin = _pair(origin_level0_xy, 'origin_level0_xy', allow_zero=True)
    requested = _pair(read_size_wh, 'read_size_wh')
    model_size = None if model_size_wh is None else _pair(model_size_wh, 'model_size_wh')
    level = _level(level)
    if level >= len(slide.level_downsamples):
        raise ValueError('level is not present in this slide')
    downsample = _downsample(slide.level_downsamples[level])
    dimensions = _pair(slide.dimensions, 'slide_size_level0_wh')
    if any(o >= limit for o, limit in zip(origin, dimensions)):
        raise ValueError('origin must be inside the slide')
    actual_size = tuple(min(size, math.floor((limit-o)/downsample))
                        for size, o, limit in zip(requested, origin, dimensions))
    if min(actual_size) <= 0:
        raise ValueError('No complete selected-level pixel fits at this origin')
    geometry = RoiGeometry(origin, level, downsample, actual_size,
                           actual_size if model_size is None else model_size, dimensions)
    region = slide.read_region(origin, level, actual_size)
    if not isinstance(region, Image.Image) or region.size != actual_size:
        raise ValueError('Reader image size differs from the requested clipped size')
    rgba = region.convert('RGBA')
    mask = Image.fromarray(np.asarray(rgba)[..., 3] == 255)
    rgb = Image.alpha_composite(Image.new('RGBA', rgba.size, 'white'), rgba).convert('RGB')
    if geometry.model_size_wh != actual_size:
        rgb = rgb.resize(geometry.model_size_wh, Image.Resampling.BILINEAR)
        mask = mask.resize(geometry.model_size_wh, Image.Resampling.NEAREST)
    return RoiRead(np.asarray(rgb).copy(), np.asarray(mask, dtype=bool).copy(),
                   geometry, requested)


def roi_patch_manifest(geometry: RoiGeometry, mode: str):
    """Map valid model-frame patch rectangles through the reserved user adapter.

    This path intentionally raises NotImplementedError until STEP_40 is submitted.
    Existing public native exports continue using their unchanged implementation.
    """
    if not isinstance(geometry, RoiGeometry):
        raise ValueError('geometry must be a RoiGeometry')
    if mode not in ('no_overlap', 'overlap'):
        raise ValueError('Unsupported mode')
    from .learner_wsi import roi_points_to_level0
    from .patches import grid

    patches = grid(*geometry.model_size_wh, 128, 64 if mode == 'overlap' else 0)
    corners = np.array([point for p in patches for point in
                        ((p.x, p.y), (p.x+p.valid_width, p.y+p.valid_height))], dtype=np.float64)
    mapped = roi_points_to_level0(corners, geometry).reshape(len(patches), 2, 2)
    return [dict(id=i, origin_local=[p.x, p.y], origin_level0=coords[0].tolist(),
                 bbox_local=[p.x, p.y, p.x+p.valid_width, p.y+p.valid_height],
                 bbox_level0=coords.reshape(4).tolist(),
                 valid_size=[p.valid_width, p.valid_height], size=p.size)
            for i, (p, coords) in enumerate(zip(patches, mapped))]
