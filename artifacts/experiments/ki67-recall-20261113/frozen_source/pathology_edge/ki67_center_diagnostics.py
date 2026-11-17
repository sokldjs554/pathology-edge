"""Decoder-stage observations, not claims about biological causes of missed cells."""
import numpy as np
from scipy.spatial.distance import cdist
from .ki67_centers import decode_candidates
from .ki67_evaluation import points_array, class_array, match_points, count_metrics

REASONS=('matched','no_peak','below_threshold','distance_suppressed','assignment_competition')


def _references(points,classes):
    points=points_array(points);classes=class_array(classes)
    if len(points)!=len(classes):raise ValueError('Each reference needs one class')
    return points,classes


def diagnose_candidates(points,scores,gt,classes,config):
    gt,classes=_references(gt,classes)
    kept=decode_candidates(points,scores,**config)['points_xy']
    points=points_array(points);scores=np.asarray(scores)
    passing=points[scores>=config['threshold']]
    pairs=match_points(kept,gt,6);matched={j for _,j in pairs}
    near=[(cdist(gt,p)<=6).any(axis=1) for p in (points,passing,kept)]
    reasons=[]
    for j in range(len(gt)):
        if j in matched:reason='matched'
        elif not near[0][j]:reason='no_peak'
        elif not near[1][j]:reason='below_threshold'
        elif not near[2][j]:reason='distance_suppressed'
        else:reason='assignment_competition'
        reasons.append(reason)
    return dict(counts={r:reasons.count(r) for r in REASONS},reasons=reasons,
        by_class=[{r:sum(c==k and reason==r for c,reason in zip(classes.tolist(),reasons)) for r in REASONS} for k in range(4)],
        localization=count_metrics(len(pairs),len(kept)-len(pairs),len(gt)-len(pairs)))


def select_recall_configuration(trials,floors):
    if not trials or any(t['split']!='validation' for t in trials):
        raise ValueError('Selection accepts validation only')
    def values(t):return [t['case_macro_recall'],*t['tumor_recalls']]
    for t in [floors,*trials]:
        v=values(t)
        if len(v)!=3 or not np.isfinite(v).all() or min(v)<0 or max(v)>1:
            raise ValueError('Expected recall metrics in [0,1]')
    if any(not np.isfinite(t['case_macro_f1']) or not 0<=t['case_macro_f1']<=1 for t in trials):
        raise ValueError('Expected F1 in [0,1]')
    feasible=[t for t in trials if all(a>=b for a,b in zip(values(t),values(floors)))]
    chosen=max(feasible,key=lambda t:(t['case_macro_f1'],t['case_macro_recall'],t['config']['threshold'],t['config']['min_distance'])) if feasible else None
    return dict(selected=chosen,feasible_trials=len(feasible),total_trials=len(trials),floors=floors)


def class_accounting(points,classes,gt,gt_classes):
    points,classes=_references(points,classes);gt,gt_classes=_references(gt,gt_classes)
    pairs=match_points(points,gt,6);pi={i for i,_ in pairs};gi={j for _,j in pairs}
    confusion=np.zeros((4,4),dtype=np.int64)
    for i,j in pairs:confusion[gt_classes[j],classes[i]]+=1
    missed=np.bincount([c for j,c in enumerate(gt_classes) if j not in gi],minlength=4)
    unmatched=np.bincount([c for i,c in enumerate(classes) if i not in pi],minlength=4)
    reference=np.bincount(gt_classes,minlength=4);predicted=np.bincount(classes,minlength=4)
    if not np.array_equal(confusion.sum(0)+unmatched,predicted) or not np.array_equal(confusion.sum(1)+missed,reference):
        raise ValueError('Class count accounting failed')
    return dict(matched_confusion=confusion.tolist(),missed_reference_by_class=missed.tolist(),
        unmatched_prediction_by_class=unmatched.tolist(),reference_counts=reference.tolist(),predicted_counts=predicted.tolist())
