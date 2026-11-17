import inspect
import numpy as np
import pytest
from pathology_edge.ki67_candidate_filter import (
    training_labels, gate_features, fit_gate, gate_scores, keep_candidates,
    select_threshold,
)


def test_proxy_labels_ignore_border_nearby_unmatched_and_empty_truth():
    points = np.array([[30,30],[36,30],[42,30],[43,30],[80,80],[1,1]])
    truth = np.array([[30,30]])
    # one matched positive; <=12px ambiguous, >12px interior proxy negative
    assert training_labels(points, truth, (100,100)).tolist() == [1,-1,-1,0,-1,-1]
    assert training_labels(points, np.empty((0,2)), (100,100)).tolist() == [-1]*6


def test_proxy_positives_one_to_one_not_all_points_near_one_cell():
    assert training_labels(np.array([[30,30],[31,30]]),np.array([[30,30]]),(80,80)).tolist()==[1,-1]


@pytest.mark.parametrize('point', [[-1,2],[3.5,2],[100,2],[np.nan,1]])
def test_invalid_centers_rejected(point):
    with pytest.raises(ValueError):
        training_labels(np.array([point]),np.array([[10,10]]),(100,100))


def test_features_keep_order_and_reject_invalid_response():
    rgb = np.full((60,60,3),180,dtype=np.uint8)
    p=np.array([[10,10],[30,30]])
    x=gate_features(rgb,p,np.array([.1,.8]))
    assert x.shape==(2,41)
    assert x[:,-1].tolist()==[.1,.8]
    assert gate_features(rgb,np.empty((0,2)),np.array([])).shape==(0,41)
    with pytest.raises(ValueError): gate_features(rgb,p,np.array([np.nan,.2]))
    with pytest.raises(ValueError): gate_features(rgb,p,np.array([.2]))


def toy_model():
    return dict(schema='candidate-correspondence-gate.v1',mean=[0.]*41,
                scale=[1.]*41,coefficients=[0.]*41,intercept=0.)


def test_gate_equality_empty_and_no_gt_interface():
    model=toy_model()
    assert np.array_equal(keep_candidates(np.zeros((3,41)),model,.5),[True]*3)
    assert not keep_candidates(np.zeros((3,41)),model,.51).any()
    assert keep_candidates(np.empty((0,41)),model,.5).shape==(0,)
    assert list(inspect.signature(keep_candidates).parameters)==['features','model','threshold']


@pytest.mark.parametrize('key,value',[('intercept',float('nan')),('scale',[0.]*41),('coefficients',[1.]*40)])
def test_invalid_model_fails_even_with_empty_candidates(key,value):
    model=toy_model(); model[key]=value
    with pytest.raises(ValueError): gate_scores(np.empty((0,41)),model)


@pytest.mark.parametrize('threshold',[float('nan'),-1,1.1,True,'0.5'])
def test_invalid_threshold(threshold):
    with pytest.raises(ValueError): keep_candidates(np.zeros((1,41)),toy_model(),threshold)


def sample(case, scores, points, truth, split='validation'):
    return dict(case_id=case,split=split,scores=np.array(scores),
                points=np.array(points,dtype=float).reshape(-1,2),
                gt_points=np.array(truth,dtype=float).reshape(-1,2))


def test_threshold_selection_retains_recall_in_every_case():
    samples=[sample('a',[.2,.9],[[10,10],[30,30]],[[10,10]]),
             sample('b',[.9,.1,.1],[[10,10],[30,30],[50,50]],[[10,10]])]
    selected=select_threshold(samples,thresholds=[0,.5])
    assert selected['threshold']==0  # .5 sacrifices all of case a, even if b improves
    assert not selected['trials'][1]['eligible']


def test_threshold_tie_and_test_split_rejected():
    s=sample('a',[.9,.1],[[10,10],[30,30]],[[10,10]])
    assert select_threshold([s],thresholds=[0,.5,.7])['threshold']==.5
    s['split']='test'
    with pytest.raises(ValueError,match='validation'): select_threshold([s])


def test_fit_uses_training_only_and_ignores_ambiguous_rows():
    x=np.zeros((5,41)); x[:,0]=[-2,-1,1,2,9999]
    y=np.array([0,0,1,1,-1])
    model=fit_gate(x,y,split='train')
    assert model['mean'][0]==0
    scores=gate_scores(x[:4],model)
    assert scores[0]<scores[-1]
    with pytest.raises(ValueError,match='train'): fit_gate(x,y,split='test')
    with pytest.raises(ValueError): fit_gate(x,np.ones(5,dtype=int),split='train')
