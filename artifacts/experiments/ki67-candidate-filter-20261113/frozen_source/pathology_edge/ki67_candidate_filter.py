"""Candidate-to-annotation correspondence gate, not clinical cellness probability.

Training labels are proxies derived from released point annotations. No ground
truth enters feature extraction, gate scoring, or candidate retention.
"""
from collections import defaultdict
import warnings
import numpy as np
from scipy.spatial.distance import cdist
from scipy.special import expit
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from .ihc_baseline import extract_features
from .ki67_detection import validate_rgb
from .ki67_evaluation import points_array, match_points, count_metrics

THRESHOLDS = (0., .1, .2, .3, .4, .5, .6, .7, .8, .9, .95, .99, 1.)


def _centers(points, shape_hw):
    points = points_array(points)
    if len(shape_hw) != 2 or any(isinstance(v, bool) or not isinstance(v, (int, np.integer)) or v <= 0 for v in shape_hw):
        raise ValueError('Expected positive integer image height/width')
    h, w = shape_hw
    if np.any(points != np.floor(points)) or np.any(points < 0) or np.any(points[:,0] >= w) or np.any(points[:,1] >= h):
        raise ValueError('Expected integer centers inside image')
    return points.astype(np.int64)


def training_labels(points, target, shape_hw):
    points, target = _centers(points, shape_hw), _centers(target, shape_hw)
    labels = np.full(len(points), -1, dtype=np.int64)
    if not len(target) or not len(points):
        return labels
    # Unknown ROI polygon support means these are negative PROXIES only.
    h, w = shape_hw
    interior = (points[:,0] >= 24) & (points[:,0] < w-24) & (points[:,1] >= 24) & (points[:,1] < h-24)
    labels[interior & (cdist(points, target).min(axis=1) > 12)] = 0
    for i, _ in match_points(points, target, 6):
        labels[i] = 1
    return labels


def _features(features):
    x = np.asarray(features)
    if x.ndim != 2 or x.shape[1] != 41 or x.dtype.kind not in 'iuf' or not np.isfinite(x).all():
        raise ValueError('Expected finite real Nx41 features')
    return x.astype(np.float64)


def gate_features(rgb, points, responses):
    validate_rgb(rgb)
    points = _centers(points, rgb.shape[:2])
    response = np.asarray(responses)
    if response.shape != (len(points),) or response.dtype.kind not in 'iuf' or not np.isfinite(response).all():
        raise ValueError('Expected one finite response per candidate')
    return _features(np.column_stack([extract_features(rgb, points), response]))


def fit_gate(features, labels, *, split):
    if split != 'train':
        raise ValueError('Gate fitting accepts train only')
    x, y = _features(features), np.asarray(labels)
    if y.shape != (len(x),) or y.dtype.kind not in 'iu' or not np.isin(y, [-1,0,1]).all():
        raise ValueError('Expected labels -1 (ignore), 0 or 1')
    used = y >= 0
    x, y = x[used], y[used]
    if set(y.tolist()) != {0,1}:
        raise ValueError('Both proxy classes required for training')
    scaler = StandardScaler().fit(x)
    clf = LogisticRegression(C=1., class_weight='balanced', solver='lbfgs', max_iter=2000)
    with warnings.catch_warnings():
        warnings.simplefilter('error', ConvergenceWarning)
        clf.fit(scaler.transform(x), y)
    return dict(schema='candidate-correspondence-gate.v1', mean=scaler.mean_.tolist(),
                scale=scaler.scale_.tolist(), coefficients=clf.coef_[0].tolist(),
                intercept=float(clf.intercept_[0]), training_samples=len(y),
                training_class_counts=np.bincount(y,minlength=2).tolist(), iterations=int(clf.n_iter_[0]),
                target='released-annotation correspondence proxy; not expert non-cell label')


def gate_scores(features, model):
    x = _features(features)
    try:
        if model['schema'] != 'candidate-correspondence-gate.v1':
            raise ValueError('Unknown gate schema')
        mean, scale, coef, bias = [np.asarray(model[k]) for k in ('mean','scale','coefficients','intercept')]
        if [a.shape for a in (mean,scale,coef,bias)] != [(41,),(41,),(41,),()] or any(a.dtype.kind not in 'iuf' or not np.isfinite(a).all() for a in (mean,scale,coef,bias)) or np.any(scale <= 0):
            raise ValueError('Invalid gate model')
    except (KeyError, TypeError) as exc:
        raise ValueError('Invalid gate model') from exc
    with np.errstate(over='ignore', invalid='ignore'):
        logits = ((x-mean)/scale) @ coef + bias
    if not np.isfinite(logits).all():
        raise ValueError('Nonfinite gate logits')
    return expit(logits)


def _threshold(value):
    if isinstance(value,(bool,str)) or not np.isscalar(value) or not np.isfinite(value) or not 0 <= value <= 1:
        raise ValueError('Threshold must be finite in [0,1]')
    return float(value)


def keep_candidates(features, model, threshold):
    return gate_scores(features, model) >= _threshold(threshold)


def select_threshold(samples, thresholds=THRESHOLDS):
    if not samples or any(s['split'] != 'validation' for s in samples):
        raise ValueError('Threshold selection accepts validation only')
    thresholds = sorted({_threshold(t) for t in thresholds})
    if not thresholds or thresholds[0] != 0:
        raise ValueError('Must include unfiltered fallback threshold0')
    for s in samples:
        p, g = points_array(s['points']), points_array(s['gt_points'])
        scores = np.asarray(s['scores'])
        if scores.shape != (len(p),) or scores.dtype.kind not in 'iuf' or not np.isfinite(scores).all() or np.any(scores < 0) or np.any(scores > 1):
            raise ValueError('Invalid candidate scores')
    trials, baseline = [], None
    for threshold in thresholds:
        counts = defaultdict(lambda: np.zeros(3,dtype=np.int64))
        for s in samples:
            points = np.asarray(s['points'])[np.asarray(s['scores']) >= threshold]
            truth = np.asarray(s['gt_points'])
            tp = len(match_points(points, truth, 6))
            counts[s['case_id']] += [tp, len(points)-tp, len(truth)-tp]
        cases = {c:count_metrics(*n) for c,n in sorted(counts.items())}
        if baseline is None:
            baseline = cases
        trials.append(dict(threshold=threshold, cases=cases,
            case_macro_f1=float(np.mean([c['f1'] for c in cases.values()])),
            case_macro_recall=float(np.mean([c['recall'] for c in cases.values()])),
            eligible=all(cases[c]['recall'] + 1e-12 >= .9*baseline[c]['recall'] for c in cases)))
    chosen = max((t for t in trials if t['eligible']),
                 key=lambda t:(t['case_macro_f1'],t['case_macro_recall'],-t['threshold']))
    return dict(threshold=chosen['threshold'], trials=trials,
                criterion='case-macro localization F1 with >=90% baseline recall in every validation case')
