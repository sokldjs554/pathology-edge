import numpy as np
from scipy.optimize import linear_sum_assignment


def binary_metrics(prediction, target, region=None):
    p, t = np.asarray(prediction), np.asarray(target)
    if p.shape != t.shape or p.ndim != 2:
        raise ValueError('Equal HW arrays required')
    if not np.isin(p, [0, 1]).all() or not np.isin(t, [0, 1]).all():
        raise ValueError('Threshold probabilities before evaluation')
    if region is not None:
        if region.shape != t.shape:
            raise ValueError('Region shape mismatch')
        p, t = p[region], t[region]
    p, t = p.astype(bool), t.astype(bool)
    tp, fp, fn = int((p & t).sum()), int((p & ~t).sum()), int((~p & t).sum())
    # Both-empty masks are perfect agreement. Precision/recall undefined -> zero.
    return dict(tp=tp, fp=fp, fn=fn, pixels=int(p.size),
                dice=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 1.0,
                iou=tp/(tp+fp+fn) if tp+fp+fn else 1.0,
                precision=tp/(tp+fp) if tp+fp else 0.0,
                recall=tp/(tp+fn) if tp+fn else 0.0)


def point_metrics(pred_xy, target_xy, radius=12):
    """Maximum-cardinality, then minimum-distance one-to-one centroid matching.

    For TNBC, targets are connected-component centroids of binary masks, not
    manually annotated cell centers. This is a proxy, not clinical cell accuracy.
    """
    p, t = np.asarray(pred_xy, dtype=float).reshape(-1, 2), np.asarray(target_xy, dtype=float).reshape(-1, 2)
    if radius <= 0 or not np.isfinite(p).all() or not np.isfinite(t).all():
        raise ValueError('Finite points and positive radius required')
    tp = 0
    if len(p) and len(t):
        d = np.linalg.norm(p[:, None] - t[None], axis=2)
        penalty = (min(len(p), len(t))+1) * (radius+1)
        row, col = linear_sum_assignment(np.where(d <= radius, d, penalty))
        tp = int((d[row, col] <= radius).sum())
    fp, fn = len(p)-tp, len(t)-tp
    return dict(tp=tp, fp=fp, fn=fn, precision=tp/(tp+fp) if tp+fp else 0,
                recall=tp/(tp+fn) if tp+fn else 0,
                f1=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 1.0)
