"""Explicit binary-nucleus evaluation of annotated external ROIs, not whole WSI."""
from pathlib import Path
import xml.etree.ElementTree as ET

import cv2
import numpy as np

from .metrics import binary_metrics
from .patches import boundary_mask


def rasterize_xml(path: Path, shape: tuple[int, int]) -> tuple[np.ndarray, int]:
    """Union Aperio nucleus polygons: nearest integer vertices, filled edges included.

    Instances are collapsed to foreground. Negative regions/holes fail explicitly.
    The image canvas clips polygons crossing its edge; vertices are not clamped.
    This explicitly defined OpenCV rasterization is not the official MATLAB/AJI
    leaderboard conversion. No stain conversion, resizing or manual corrections.
    """
    h, w = shape
    if h <= 0 or w <= 0:
        raise ValueError('Positive image shape required')
    root = ET.parse(path).getroot()
    regions = root.findall('.//Region')
    if not regions:
        raise ValueError('No annotated nucleus regions')
    mask = np.zeros((h, w), np.uint8)
    for region in regions:
        if region.attrib.get('NegativeROA', '0') != '0':
            raise ValueError('Unsupported negative region; do not silently fill holes')
        vertices = region.findall('./Vertices/Vertex')
        points = np.asarray([(float(v.attrib['X']), float(v.attrib['Y']))
                             for v in vertices], dtype=np.float64)
        if (len(points) < 3 or points.shape != (len(points), 2)
                or not np.isfinite(points).all()
                or np.any(np.abs(points) > 2**30)):
            raise ValueError('Invalid nucleus coordinate')
        rounded = np.rint(points).astype(np.int32)
        cv2.fillPoly(mask, [rounded], 1)
    return mask.astype(bool), len(regions)


def score_probability(probability: np.ndarray, target: np.ndarray,
                      threshold: float) -> dict:
    """Same 128px seams and 8px half-width for both models, full annotated ROI."""
    if (probability.ndim != 2 or probability.shape != target.shape
            or not np.isfinite(probability).all()
            or np.any((probability < 0) | (probability > 1))):
        raise ValueError('Invalid probability map')
    if not np.isfinite(threshold) or not 0 < threshold < 1:
        raise ValueError('Invalid fixed threshold')
    seam = boundary_mask(target.shape, size=128, radius=8)
    if not seam.any() or seam.all():
        raise ValueError('Both seam and interior must contain pixels')
    prediction = probability >= threshold
    return {name: binary_metrics(prediction, target, region)
            for name, region in [('all', None), ('boundary', seam), ('interior', ~seam)]}
