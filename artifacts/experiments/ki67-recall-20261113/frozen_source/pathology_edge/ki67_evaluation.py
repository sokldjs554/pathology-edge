"""Class-blind point matching; empty denominators are explicit, not successes."""
import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist


def points_array(points):
    points = np.asarray(points)
    if points.ndim != 2 or points.shape[1] != 2 or points.dtype.kind not in 'iuf' or not np.isfinite(points).all():
        raise ValueError('Expected finite real Nx2 XY points')
    return points.astype(np.float64)


def class_array(classes):
    classes = np.asarray(classes)
    if classes.ndim != 1 or (classes.size and (classes.dtype.kind not in 'iu' or not np.isin(classes, range(4)).all())):
        raise ValueError('Expected integer class IDs 0..3')
    return classes.astype(np.int64)


def match_points(predicted_xy, target_xy, radius=6):
    predicted, target = points_array(predicted_xy), points_array(target_xy)
    if isinstance(radius, (bool, str)) or not np.isscalar(radius) or not np.isfinite(radius) or radius <= 0:
        raise ValueError('Matching radius must be positive and finite')
    n, m = len(predicted), len(target)
    if not n or not m:
        return []
    distances = cdist(predicted, target)
    # Any extra match saves more than the largest possible sum of real costs.
    penalty = min(n, m) + 1.0
    costs = np.full((n, m+n), penalty)
    costs[:, :m] = np.where(distances <= radius, distances/radius, 2*penalty)
    rows, columns = linear_sum_assignment(costs)
    return [(int(i), int(j)) for i, j in zip(rows, columns) if j < m and distances[i, j] <= radius]


def count_metrics(tp, fp, fn):
    tp, fp, fn = int(tp), int(fp), int(fn)
    return {'tp': tp, 'fp': fp, 'fn': fn, 'precision': tp/(tp+fp) if tp+fp else 0.,
            'recall': tp/(tp+fn) if tp+fn else 0., 'f1': 2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0.}


def positive_fraction(classes):
    classes = class_array(classes)
    positive, tumor = int((classes == 0).sum()), int(np.isin(classes, [0, 1]).sum())
    return {'positive_tumor_cells': positive, 'tumor_cells': tumor, 'fraction': positive/tumor if tumor else None}


def evaluate_cells(predicted_xy, predicted_classes, target_xy, target_classes, radius=6):
    predicted, target = points_array(predicted_xy), points_array(target_xy)
    pc, tc = class_array(predicted_classes), class_array(target_classes)
    if len(predicted) != len(pc) or len(target) != len(tc):
        raise ValueError('Each point needs one class')
    pairs = match_points(predicted, target, radius)
    confusion = np.zeros((4, 4), dtype=np.int64)
    for i, j in pairs:
        confusion[tc[j], pc[i]] += 1
    classes = [count_metrics(confusion[k, k], (pc == k).sum()-confusion[k, k], (tc == k).sum()-confusion[k, k]) for k in range(4)]
    return {'localization': count_metrics(len(pairs), len(pc)-len(pairs), len(tc)-len(pairs)),
            'classes': classes, 'macro_f1': float(np.mean([c['f1'] for c in classes])),
            'matched_accuracy': float(np.trace(confusion)/len(pairs)) if pairs else None,
            'matched_confusion': confusion.tolist(), 'pairs': pairs,
            'predicted_fraction': positive_fraction(pc), 'target_fraction': positive_fraction(tc)}
