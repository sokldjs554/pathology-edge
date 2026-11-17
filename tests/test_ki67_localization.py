"""Candidate-native localization geometry and numerical contracts."""
import importlib
import numpy as np
import pytest
import torch

@pytest.fixture
def api():
    try:return importlib.import_module('pathology_edge.ki67_localization')
    except ModuleNotFoundError:pytest.fail('candidate localization module missing')

def test_reflected_context_keeps_integer_anchor_and_real_border_pixels(api):
    rgb=np.repeat(np.arange(25,dtype=np.uint8).reshape(5,5,1),3,2)
    context=api.reflected_context(rgb,np.array([[0,0]]))[0]
    assert context.shape==(33,33,3)
    assert context[16,16,0]==0 and context[16,15,0]==1 and context[15,16,0]==5

@pytest.mark.parametrize('k,expected',[(0,(3,2)),(1,(2,-3)),(2,(-3,-2)),(3,(-2,3))])
@pytest.mark.parametrize('fy,fx',[(False,False),(True,False),(False,True),(True,True)])
def test_augmentation_keeps_off_center_impulse_on_offset_target(api,k,expected,fy,fx):
    context=np.zeros((33,33,3),np.uint8);context[18,19]=255
    crop,offset=api.transform_sample(context,np.array([3.,2.]),k,fy,fx)
    dx,dy=expected;expected=np.array([-dx if fx else dx,-dy if fy else dy])
    assert np.array_equal(offset,expected)
    assert crop.shape==(32,32,3) and (crop[16+expected[1],16+expected[0]]==255).all()

def test_proxy_targets_are_candidate_native_and_ties_are_stable(api):
    p=np.array([[30,30],[42,30],[43,30],[0,0]])
    out=api.proxy_targets(p,np.array([[30,30]]),(80,80))
    assert out['labels'].tolist()==[1,1,0,-1]
    assert out['offsets'][1].tolist()==[-12,0]
    tie=api.proxy_targets(np.array([[30,30]]),np.array([[29,30],[31,30]]),(80,80))
    assert tie['nearest'].tolist()==[0] and tie['offsets'].tolist()==[[-1,0]]
    assert api.proxy_targets(p,np.empty((0,2)),(80,80))['labels'].tolist()==[-1]*4

def test_continuous_bound_and_rounding_are_separate(api):
    delta=api.bounded_offsets(torch.tensor([[1e3,1e3],[-1e3,1e3]]))
    assert torch.all(torch.linalg.vector_norm(delta,dim=1)<=12.00001)
    out=api.corrected_points(np.array([[20,20],[0,0]]),np.array([[8.46,8.51],[-3.,-4.]]),(50,50))
    assert out.tolist()==[[28,29],[0,0]]
    assert np.linalg.norm(out[0]-[20,20])>12

@pytest.mark.parametrize('offset',[[[np.nan,0]],[[np.inf,0]],[[13,0]]])
def test_invalid_continuous_offsets_rejected(api,offset):
    with pytest.raises(ValueError):api.corrected_points(np.array([[20,20]]),np.array(offset),(50,50))

def test_zero_initialized_offset_head_and_loss_update(api):
    torch.set_num_threads(1);torch.manual_seed(7);model=api.LocalizationGate()
    x=torch.rand(4,3,32,32);meta=torch.zeros(4,4)
    logits,offset=model(x,meta)
    assert torch.equal(offset,torch.zeros_like(offset))
    original=model.offset_head.weight.detach().clone()
    loss=api.localization_loss(logits,offset,torch.tensor([0,1,0,1]),torch.tensor([[0.,0.],[3.,2.],[0.,0.],[-2.,1.]]))
    loss.backward();torch.optim.SGD(model.parameters(),lr=.1).step()
    assert not torch.equal(original,model.offset_head.weight)

def test_prediction_is_image_and_proposal_only(api):
    model=api.LocalizationGate();rgb=np.full((40,40,3),127,np.uint8);p=np.array([[0,0],[39,39]])
    r=api.predict_localized(rgb,p,np.zeros((2,4)),model)
    assert np.array_equal(r['corrected_xy'],p) and r['scores'].shape==(2,)
    empty=api.predict_localized(rgb,np.empty((0,2)),np.empty((0,4)),model)
    assert empty['corrected_xy'].shape==(0,2)

def test_nonfinite_weights_rejected_for_empty_input(api):
    model=api.LocalizationGate()
    with torch.no_grad():model.score_head.bias[0]=float('nan')
    with pytest.raises(ValueError):api.predict_localized(np.zeros((40,40,3),np.uint8),np.empty((0,2)),np.empty((0,4)),model)

def test_overflowing_logits_cannot_be_returned(api):
    model=api.LocalizationGate()
    with torch.no_grad():
        for p in model.parameters():p.fill_(1e38)
    with pytest.raises(ValueError):api.predict_localized(np.full((40,40,3),255,np.uint8),np.array([[20,20]]),np.zeros((1,4)),model)
