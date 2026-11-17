"""Coverage-aware foreground evaluation of PanopTILs manual annotation ROIs.

Nuclear rectangles are location labels, not segmentation ground truth. Ignore
their entire inclusive bounding extent, ambiguous nuclei, and unlabeled pixels.
"""
import math
import re

import numpy as np

from .metrics import binary_metrics
from .patches import boundary_mask
from .wsi_roi import RoiGeometry


def roi_geometry(record):
    """Check encoded level-0 bounds and describe continuous output edge mapping.

    This verifies metadata arithmetic, not pixel-exact registration of labels.
    """
    match = re.fullmatch(r'.+_left-(\d+)_top-(\d+)_bottom-(\d+)_right-(\d+)', record['id'])
    if match is None:
        raise ValueError('ROI name must encode bounds')
    left, top, bottom, right = map(int, match.groups())
    if record['bounds_level0'] != dict(left=left, top=top, right=right, bottom=bottom):
        raise ValueError('Encoded bounds differ from source request')
    return RoiGeometry((left, top), 0, 1., (right-left, bottom-top),
                       tuple(record['evaluation_input_wh']),
                       (record['tiles']['sizeX'], record['tiles']['sizeY']))


def _bounds(row):
    try:
        values = tuple(float(row[k]) for k in ('left', 'top', 'right', 'bottom'))
        if not all(math.isfinite(v) for v in values):
            raise ValueError
        if values[0] >= values[2] or values[1] >= values[3]:
            raise ValueError
        return values
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError('Finite positive-area annotation bounds required') from exc


def annotation_region(mask, annotations, fov):
    """Return target/valid masks; only valid pixels have interpretable GT labels."""
    if not isinstance(mask, np.ndarray) or mask.dtype != np.uint8 or mask.ndim != 3 or mask.shape[2] != 3:
        raise ValueError('Expected uint8 three-channel annotation mask')
    if mask.size == 0 or np.any(mask[..., 0] > 8) or np.any(mask[..., 1] > 9) or np.any(mask[..., 2] > 1):
        raise ValueError('Unknown annotation code or empty image')
    h, w = mask.shape[:2]
    left, top, right, bottom = _bounds(fov)
    if any(v != int(v) for v in (left, top, right, bottom)) or left < 0 or top < 0 or right > w or bottom > h:
        raise ValueError('FOV must use integer bounds inside the image')
    fov_mask = np.zeros((h, w), bool)
    fov_mask[int(top):int(bottom), int(left):int(right)] = True
    boxes = np.zeros((h, w), bool)
    count = 0
    for row in annotations:
        if row.get('type') not in ('polyline', 'rectangle'):
            raise ValueError('Unknown annotation type')
        if row['type'] == 'rectangle':
            x0, y0, x1, y1 = _bounds(row)
            boxes[min(h, max(0, math.floor(y0))):max(0, min(h, math.ceil(y1)+1)),
                  min(w, max(0, math.floor(x0))):max(0, min(w, math.ceil(x1)+1))] = True
            count += 1
    nucleus = mask[..., 1]
    target = (nucleus >= 1) & (nucleus <= 7)
    valid = fov_mask & (mask[..., 0] != 0) & (target | (nucleus == 9)) & ~boxes
    if not valid.any():
        raise ValueError('No evaluable annotation pixels')
    stats = dict(image_pixels=h*w, fov_pixels=int(fov_mask.sum()), valid_pixels=int(valid.sum()),
                 valid_fraction=float(valid.mean()), ignored_pixels=int((~valid).sum()),
                 foreground_valid_pixels=int((target & valid).sum()),
                 rectangle_annotations_excluded=count, rectangle_pixels_inside_fov=int((boxes & fov_mask).sum()),
                 ambiguous_pixels_inside_fov=int(((nucleus == 8) & fov_mask).sum()))
    return target, valid, stats


def score_roi(probability, target, valid, threshold):
    if (probability.ndim != 2 or probability.shape != target.shape or valid.shape != target.shape
            or target.dtype != bool or valid.dtype != bool or not valid.any()
            or not np.isfinite(probability).all() or np.any((probability < 0) | (probability > 1))
            or not math.isfinite(threshold) or not 0 < threshold < 1):
        raise ValueError('Aligned probabilities, bool masks and fixed threshold required')
    seams = boundary_mask(target.shape, size=128, radius=8)
    regions = {'all': valid, 'boundary': valid & seams, 'interior': valid & ~seams}
    return {name: binary_metrics(probability >= threshold, target, region) if region.any() else None
            for name, region in regions.items()}


def contour_agreement_region(mask, annotations, fov):
    """Score only mask/CSV contour agreement; disagreements become ignored pixels.

    Pillow integer polygons include their outline. This is a conservative audit
    convention, not proof of the historical mask exporter's exact rasterization.
    A case with no polylines can supply background only, not contour accuracy.
    """
    from PIL import Image, ImageDraw
    annotations = list(annotations)
    target, valid, stats = annotation_region(mask, annotations, fov)
    canvas = Image.new('1', (mask.shape[1], mask.shape[0]))
    draw = ImageDraw.Draw(canvas)
    count = 0
    for row in annotations:
        if row['type'] != 'polyline':
            continue
        try:
            x = [float(v) for v in row['coords_x'].split(',')]
            y = [float(v) for v in row['coords_y'].split(',')]
            if (len(x) != len(y) or len(x) < 3 or any(not math.isfinite(v) or v != int(v)
                    or abs(v) >= 2**30 for v in x+y)):
                raise ValueError
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            raise ValueError('Finite integer CSV polygon vertices required') from exc
        draw.polygon([(int(a),int(b)) for a,b in zip(x,y)], outline=1, fill=1)
        count += 1
    contours = np.asarray(canvas, dtype=bool)
    unsupported = valid & target & ~contours
    contradictory = valid & ~target & contours
    stats.update(base_valid_pixels=int(valid.sum()), polyline_records=count,
                 unsupported_foreground_pixels=int(unsupported.sum()),
                 contradictory_background_pixels=int(contradictory.sum()))
    valid = valid & ~(unsupported | contradictory)
    if not valid.any():
        raise ValueError('No mask/CSV agreement pixels remain')
    stats.update(valid_pixels=int(valid.sum()), valid_fraction=float(valid.mean()),
                 ignored_pixels=int((~valid).sum()), foreground_valid_pixels=int((target&valid).sum()))
    return target, valid, stats
