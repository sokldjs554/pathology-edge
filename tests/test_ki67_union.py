"""Catch unsafe union coordinates, proxy labels, retained scores and selection."""
import importlib
from copy import deepcopy
import numpy as np
import pytest
import torch

@pytest.fixture
def api():
    try:
        return importlib.import_module('pathology_edge.ki67_union')
    except ModuleNotFoundError:
        pytest.fail('candidate-union scoring and constrained selection are not implemented')

def test_union_keeps_exact_coordinates_and_combines_provenance(api):
    result=api.merge_proposals(np.array([[5,4],[2,2],[5,4]]),np.array([[5,4],[3,2]]),(8,9))
    assert result['points_xy'].tolist()==[[2,2],[3,2],[5,4]]
    assert result['sources'].tolist()==[1,2,3]

@pytest.mark.parametrize('points', [[[9,0]], [[-1,0]], [[.5,0]], [[np.nan,0]], [[True,False]]])
def test_union_rejects_invalid_coordinates(api,points):
    with pytest.raises(ValueError):api.merge_proposals(np.array(points),np.empty((0,2)),(8,9))

def test_union_empty_has_stable_shapes(api):
    result=api.merge_proposals(np.empty((0,2)),np.empty((0,2)),(8,9))
    assert result['points_xy'].shape==(0,2) and result['sources'].shape==(0,)

def test_proxy_negatives_exclude_nearby_border_and_unannotated_images(api):
    points=np.array([[24,24],[44,24],[23,50],[76,50],[50,50]])
    gt=np.array([[24,24],[50,50]])
    assert api.negative_proxy_indices(points,gt,(100,100)).tolist()==[1]
    assert api.negative_proxy_indices(points,np.empty((0,2)),(100,100)).tolist()==[]

def test_proxy_distance_is_strictly_more_than_twelve(api):
    assert api.negative_proxy_indices(np.array([[42,30],[43,30]]),np.array([[30,30]]),(100,100)).tolist()==[1]

def test_retention_ties_are_y_then_x_and_zero_threshold_is_valid(api):
    points=np.array([[9,0],[0,9],[0,0],[2,0]])
    result=api.retain_candidates(points,np.array([.5,.5,.5,.5]),0,4)
    assert result['points_xy'].tolist()==[[0,0],[9,0],[0,9]]
    assert result['indices'].tolist()==[2,0,1]

@pytest.mark.parametrize('threshold',[0,.1,.5,1])
def test_zero_threshold_nms_prefix_matches_separate_threshold_nms(api,threshold):
    points=np.array([[0,0],[2,0],[4,0],[8,0],[0,9]])
    scores=np.array([1.,.8,.3,.1,0.])
    direct=api.retain_candidates(points,scores,threshold,4)
    cached=api.retain_candidates(points,scores,0,4)
    assert direct['points_xy'].tolist()==cached['points_xy'][cached['scores']>=threshold].tolist()
    expected={0:[[0,0],[4,0],[8,0],[0,9]],.1:[[0,0],[4,0],[8,0]],.5:[[0,0]],1:[[0,0]]}
    assert direct['points_xy'].tolist()==expected[threshold]

@pytest.mark.parametrize('scores', [[np.nan],[np.inf],[-.1],[1.1],[True]])
def test_invalid_retention_scores_fail_closed(api,scores):
    with pytest.raises(ValueError):api.retain_candidates(np.array([[0,0]]),np.array(scores),.5,4)

def test_gate_updates_and_scores_native_border_crops(api):
    torch.manual_seed(7);torch.set_num_threads(1)
    model=api.CandidateRejector();x=torch.rand(2,3,32,32);old=model.head.weight.detach().clone()
    loss=torch.nn.functional.cross_entropy(model(x),torch.tensor([0,1]));loss.backward()
    torch.optim.SGD(model.parameters(),lr=.01).step()
    assert not torch.equal(old,model.head.weight)
    values=api.retention_scores(np.full((40,40,3),127,np.uint8),np.array([[0,0],[39,39]]),model)
    assert values.shape==(2,) and np.isfinite(values).all() and np.all((values>=0)&(values<=1))

def test_nonfinite_weights_rejected_even_when_no_candidates(api):
    model=api.CandidateRejector()
    with torch.no_grad():model.head.bias[0]=float('nan')
    with pytest.raises(ValueError):api.retention_scores(np.zeros((40,40,3),np.uint8),np.empty((0,2)),model)

def test_finite_weights_with_overflow_do_not_produce_a_class(api):
    model=api.CandidateRejector()
    with torch.no_grad():
        for p in model.parameters():p.fill_(1e38)
    with pytest.raises(ValueError):api.retention_scores(np.full((40,40,3),255,np.uint8),np.array([[20,20]]),model)

def test_validation_summary_counts_one_to_one_and_class_recall(api):
    samples=[dict(split='validation',case_id='a',points=np.array([[0,0],[1,0],[20,20]]),scores=np.array([.9,.8,.7]),gt_points=np.array([[0,0],[30,30]]),gt_classes=np.array([0,1]))]
    result=api.validation_summary(samples,dict(threshold=0,min_distance=1))
    assert {k:result['localization'][k] for k in ['tp','fp','fn']}==dict(tp=1,fp=2,fn=1)
    assert result['tumor_recalls']==[1.,0.] and result['case_macro_f1']==pytest.approx(.4)
    samples[0]['split']='test'
    with pytest.raises(ValueError):api.validation_summary(samples,dict(threshold=0,min_distance=1))

def selection_fixture():
    baseline=dict(localization=dict(tp=4,fp=6,fn=6),cases={'a':dict(recall=.4)})
    floors=dict(case_macro_recall=.5,tumor_recalls=[.5,.5])
    good=dict(split='validation',epoch=3,config=dict(threshold=.5,min_distance=4),localization=dict(tp=5,fp=5,fn=5),cases={'a':dict(recall=.5)},case_macro_f1=.5,case_macro_recall=.5,tumor_recalls=[.5,.5])
    return baseline,floors,good

def test_selection_requires_both_error_counts_and_prior_recall_floors(api):
    baseline,floors,good=selection_fixture()
    assert api.choose_trial([good],baseline,floors)['selected']==good
    for field,value in [('fp',7),('fn',7)]:
        bad=deepcopy(good);bad['localization'][field]=value
        assert api.choose_trial([bad],baseline,floors)['selected'] is None
    bad=deepcopy(good);bad['tumor_recalls']=[.499,.6]
    assert api.choose_trial([bad],baseline,floors)['selected'] is None

def test_selection_rejects_no_strict_gain_or_case_recall_loss(api):
    baseline,floors,good=selection_fixture()
    equal=deepcopy(good);equal['localization']=dict(tp=4,fp=6,fn=6)
    assert api.choose_trial([equal],baseline,floors)['selected'] is None
    dropped=deepcopy(good);dropped['cases']['a']['recall']=.35
    assert api.choose_trial([dropped],baseline,floors)['selected'] is None

def test_selection_tie_prefers_earlier_epoch_before_threshold(api):
    baseline,floors,good=selection_fixture();early=deepcopy(good);early['epoch']=2;early['config']['threshold']=.1
    assert api.choose_trial([good,early],baseline,floors)['selected']==early
    good['split']='test'
    with pytest.raises(ValueError):api.choose_trial([good],baseline,floors)
