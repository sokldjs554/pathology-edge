"""Frozen proposal union and a binary retention gate, not clinical background truth."""
import math
import numpy as np
import torch
from torch import nn
from scipy.spatial import cKDTree
from .ki67_cnn import cell_crops
from .ki67_evaluation import points_array, class_array, match_points, count_metrics


def _coordinates(points, shape_hw=None):
    points = points_array(points)
    if np.any(points < 0) or np.any(points != np.floor(points)):
        raise ValueError('Expected nonnegative integer XY coordinates')
    if shape_hw is not None:
        if len(shape_hw) != 2 or any(isinstance(v, bool) or not isinstance(v, (int, np.integer)) or v <= 0 for v in shape_hw):
            raise ValueError('Expected positive integer height/width')
        if np.any(points[:, 0] >= shape_hw[1]) or np.any(points[:, 1] >= shape_hw[0]):
            raise ValueError('Coordinates outside image')
    return points.astype(np.int64)


def merge_proposals(learned_xy, log_xy, shape_hw):
    sources = {}
    for values, bit in ((learned_xy, 1), (log_xy, 2)):
        for x, y in _coordinates(values, shape_hw):
            sources[(int(x), int(y))] = sources.get((int(x), int(y)), 0) | bit
    ordered = sorted(sources, key=lambda p: (p[1], p[0]))
    return dict(points_xy=np.array(ordered, dtype=np.int64).reshape(-1, 2),
                sources=np.array([sources[p] for p in ordered], dtype=np.uint8))


def negative_proxy_indices(points, gt, shape_hw):
    points, gt = _coordinates(points, shape_hw), _coordinates(gt, shape_hw)
    if not len(gt) or not len(points):
        return np.empty(0, dtype=np.int64)
    distance = cKDTree(gt).query(points)[0]
    interior = ((points >= 24).all(axis=1) &
                (points[:, 0] < shape_hw[1]-24) & (points[:, 1] < shape_hw[0]-24))
    return np.flatnonzero(interior & (distance > 12))


class CandidateRejector(nn.Module):
    """Score a native 32px RGB crop; class 1 means retain, scores uncalibrated."""
    def __init__(self):
        super().__init__()
        layers, previous = [], 3
        for channels in (8, 16, 32):
            layers += [nn.Conv2d(previous, channels, 3, padding=1), nn.LeakyReLU(.1),
                       nn.Conv2d(channels, channels, 3, padding=1), nn.LeakyReLU(.1), nn.MaxPool2d(2)]
            previous = channels
        self.features = nn.Sequential(*layers)
        self.head = nn.Linear(512, 2)

    def forward(self, inputs):
        if inputs.ndim != 4 or inputs.shape[1:] != (3, 32, 32) or not inputs.is_floating_point() or not torch.isfinite(inputs).all():
            raise ValueError('Expected finite Nx3x32x32 input')
        return self.head(self.features(inputs).flatten(1))


def retention_scores(rgb, points, model):
    if not isinstance(model, CandidateRejector) or not all(torch.isfinite(t).all() for t in model.state_dict().values()):
        raise ValueError('Expected finite CandidateRejector weights')
    crops = cell_crops(rgb, points, size=32)
    model.eval()
    result = []
    with torch.inference_mode():
        for start in range(0, len(crops), 256):
            inputs = torch.from_numpy(crops[start:start+256].transpose(0, 3, 1, 2).copy()).float()/255
            logits = model(inputs)
            if not torch.isfinite(logits).all():
                raise ValueError('Nonfinite gate logits')
            result.append(torch.softmax(logits, dim=1)[:, 1].cpu().numpy())
    scores = np.concatenate(result).astype(np.float64) if result else np.empty(0)
    if not np.isfinite(scores).all() or np.any(scores < 0) or np.any(scores > 1):
        raise ValueError('Invalid retention scores')
    return scores


def retain_candidates(points, scores, threshold, min_distance):
    points, scores = _coordinates(points), np.asarray(scores)
    if (isinstance(threshold, (bool, str)) or not np.isscalar(threshold) or
        not np.isrealobj(threshold) or not np.isfinite(threshold) or not 0 <= threshold <= 1 or
        isinstance(min_distance, (bool, str)) or not np.isscalar(min_distance) or
        not np.isrealobj(min_distance) or not np.isfinite(min_distance) or min_distance <= 0):
        raise ValueError('Invalid threshold/distance')
    if scores.shape != (len(points),) or scores.dtype.kind not in 'iuf' or not np.isfinite(scores).all() or np.any(scores < 0) or np.any(scores > 1):
        raise ValueError('Invalid retention scores')
    # Normalize before negation and scalar comparisons. Unsigned negation wraps;
    # float32 scalar comparison can round the configured cutoff down to a score.
    scores = scores.astype(np.float64, copy=False)
    order = np.lexsort((points[:, 0], points[:, 1], -scores))
    kept, buckets = [], {}
    for i in order:
        if scores[i] < threshold:
            break
        x, y = points[i]
        bucket = (math.floor(x/min_distance), math.floor(y/min_distance))
        neighbors = [j for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                     for j in buckets.get((bucket[0]+dx, bucket[1]+dy), [])]
        if any(float(np.sum((points[i]-points[j])**2)) < min_distance**2 for j in neighbors):
            continue
        kept.append(int(i))
        buckets.setdefault(bucket, []).append(int(i))
    indices = np.array(kept, dtype=np.int64)
    return dict(points_xy=points[indices], scores=scores[indices].astype(np.float64), indices=indices)


def summarize_locations(samples):
    """Aggregate class-blind matching; true tumor class recall is localization only."""
    cases, matched, totals = {}, np.zeros(4, dtype=int), np.zeros(4, dtype=int)
    for sample in samples:
        points, gt = points_array(sample['points']), points_array(sample['gt_points'])
        classes = class_array(sample['gt_classes'])
        if len(classes) != len(gt):
            raise ValueError('Each target point needs a class')
        pairs = match_points(points, gt)
        counts = np.array([len(pairs), len(points)-len(pairs), len(gt)-len(pairs)])
        cases.setdefault(sample['case_id'], np.zeros(3, dtype=int))[:] += counts
        totals += np.bincount(classes, minlength=4)
        matched += np.bincount([classes[j] for _, j in pairs], minlength=4)
    if not cases:
        raise ValueError('Cannot summarize an empty validation set')
    pooled = np.sum(list(cases.values()), axis=0)
    cases = {k: count_metrics(*v) for k, v in sorted(cases.items())}
    return dict(localization=count_metrics(*pooled), cases=cases,
                case_macro_f1=float(np.mean([v['f1'] for v in cases.values()])),
                case_macro_recall=float(np.mean([v['recall'] for v in cases.values()])),
                tumor_recalls=[float(matched[k]/totals[k]) if totals[k] else 0. for k in (0, 1)],
                matched_by_true_class=matched.tolist(), true_class_counts=totals.tolist())


def validation_summary(samples, config):
    if not samples or any(s.get('split') != 'validation' for s in samples):
        raise ValueError('Selection must use validation only')
    retained = [{**s, 'points': retain_candidates(s['points'], s['scores'], **config)['points_xy']} for s in samples]
    return dict(split='validation', config=config, **summarize_locations(retained))


def trial_key(trial):
    return (trial['case_macro_f1'], trial['case_macro_recall'], -trial['epoch'],
            trial['config']['threshold'], trial['config']['min_distance'])


def choose_trial(trials, baseline, floors):
    eligible = []
    for trial in trials:
        if trial.get('split') != 'validation':
            raise ValueError('Selection must use validation only')
        values = [trial['case_macro_f1'], trial['case_macro_recall'], *trial['tumor_recalls'],
                  *[v['recall'] for v in trial['cases'].values()]]
        if not all(np.isfinite(v) and 0 <= v <= 1 for v in values):
            raise ValueError('Invalid selection metrics')
        loc, base = trial['localization'], baseline['localization']
        feasible = (loc['fp'] <= base['fp'] and loc['fn'] <= base['fn'] and
                    (loc['fp'] < base['fp'] or loc['fn'] < base['fn']) and
                    trial['case_macro_recall'] >= floors['case_macro_recall'] and
                    all(a >= b for a, b in zip(trial['tumor_recalls'], floors['tumor_recalls'])) and
                    set(trial['cases']) == set(baseline['cases']) and
                    all(trial['cases'][k]['recall'] >= .9*v['recall'] for k, v in baseline['cases'].items()))
        if feasible:
            eligible.append(trial)
    return dict(selected=max(eligible, key=trial_key) if eligible else None, feasible_trials=len(eligible))
