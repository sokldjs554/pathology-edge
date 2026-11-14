"""Catch sparse-label substitutions, pixel pooling, unstable logits and biased loss selection."""
import copy
import importlib
import math
import numpy as np
import pytest
import torch


def api():
    return importlib.import_module('pathology_edge.ki67_supervision')


@pytest.mark.parametrize('mode,expected',[('soft_mse',.5),('soft_bce',2*math.log(2))])
def test_binary_targets_have_hand_derived_balanced_loss(mode,expected):
    logits=torch.zeros((1,1,1,2),dtype=torch.float64,requires_grad=True)
    target=torch.tensor([[[[1.,0.]]]],dtype=torch.float64)
    loss=api().supervision_loss(logits,target,mode)
    assert loss.item()==pytest.approx(expected)
    loss.backward()
    assert logits.grad[0,0,0,0]<0<logits.grad[0,0,0,1]


def test_soft_target_has_real_weight_and_loss_not_thresholded():
    logits=torch.zeros((1,1,1,3),dtype=torch.float64,requires_grad=True)
    target=torch.tensor([[[[1.,.5,0.]]]],dtype=torch.float64)
    assert api().supervision_loss(logits,target,'soft_mse').item()==pytest.approx(1/3)


@pytest.mark.parametrize('mode',['soft_mse','soft_bce'])
def test_batch_averages_images_instead_of_pooling_foreground_mass(mode):
    logits=torch.tensor([[[[-1.,2.,1.]]],[[[3.,-.5,2.]]]],dtype=torch.float64,requires_grad=True)
    target=torch.tensor([[[[1.,0.,0.]]],[[[1.,1.,0.]]]],dtype=torch.float64)
    each=[api().supervision_loss(logits[i:i+1],target[i:i+1],mode) for i in range(2)]
    assert api().supervision_loss(logits,target,mode).item()==pytest.approx((each[0].item()+each[1].item())/2)
    assert torch.autograd.gradcheck(lambda x:api().supervision_loss(x,target,mode),(logits,))


@pytest.mark.parametrize('mode',['soft_mse','soft_bce'])
@pytest.mark.parametrize('target_value',[0.,1.])
def test_empty_full_maps_and_extreme_logits_remain_finite(mode,target_value):
    x=torch.tensor([[[[-1000.,0.,1000.]]]],requires_grad=True)
    loss=api().supervision_loss(x,torch.full_like(x,target_value),mode)
    assert torch.isfinite(loss)
    loss.backward();assert torch.isfinite(x.grad).all()
    assert x.grad[0,0,0,1]>0 if target_value==0 else x.grad[0,0,0,1]<0


@pytest.mark.parametrize('mutation',['shape','integer','nan','range','empty','dtype','mode','array'])
def test_invalid_loss_inputs_fail_before_broadcast_or_training(mutation):
    x=torch.zeros(1,1,2,2);y=torch.zeros_like(x);mode='soft_mse'
    if mutation=='shape':y=torch.zeros(1,2,2,2)
    if mutation=='integer':y=y.long()
    if mutation=='nan':x[0,0,0,0]=float('nan')
    if mutation=='range':y[0,0,0,0]=1.01
    if mutation=='empty':x=x[:0];y=y[:0]
    if mutation=='dtype':y=y.double()
    if mutation=='mode':mode='focal'
    if mutation=='array':y=y.numpy()
    with pytest.raises(ValueError):api().supervision_loss(x,y,mode)


def reports():
    out={}
    for mode,f1 in [('focal',.4),('soft_mse',.45),('soft_bce',.44)]:
        trials=[]
        for th in (.01,.02,.03,.05,.075,.1,.15,.2,.3,.5,.7,.9):
            for d in (4,6,8):
                trials.append(dict(config=dict(threshold=th,min_distance=d),case_macro_f1=f1,case_macro_recall=.6,tumor_recalls=[.5,.4],cases={str(i):{} for i in range(15)}))
        out[mode]=dict(mode=mode,training_images=120,heldout_inference_images=0,trials=trials,best=copy.deepcopy(trials[-1]))
    return out


def change_score(r,mode,**values):
    for t in r[mode]['trials']:t.update(values)
    r[mode]['best']=copy.deepcopy(r[mode]['trials'][-1])


def test_choose_loss_requires_gain_and_positive_tumor_recall():
    r=reports();assert api().choose_loss(r)['selected_loss']=='soft_mse'
    change_score(r,'soft_bce',case_macro_f1=.8,tumor_recalls=[.49,.9])
    assert api().choose_loss(r)['selected_loss']=='soft_mse'
    change_score(r,'soft_mse',case_macro_f1=.429999)
    assert api().choose_loss(r)['selected_loss'] is None


def test_gain_boundary_and_fixed_tie_order():
    r=reports();change_score(r,'soft_mse',case_macro_f1=.43);change_score(r,'soft_bce',case_macro_f1=.43)
    assert api().choose_loss(r)['selected_loss']=='soft_mse'
    change_score(r,'soft_bce',case_macro_recall=.61)
    assert api().choose_loss(r)['selected_loss']=='soft_bce'


@pytest.mark.parametrize('mutation',['missing','heldout','images','nan','forged_best','duplicate_grid','cases','wrong_mode'])
def test_invalid_diagnostic_cannot_select_training_loss(mutation):
    r=reports()
    if mutation=='missing':del r['focal']
    if mutation=='heldout':r['soft_mse']['heldout_inference_images']=1
    if mutation=='images':r['soft_mse']['training_images']=119
    if mutation=='nan':r['soft_mse']['trials'][0]['case_macro_f1']=float('nan')
    if mutation=='forged_best':r['soft_mse']['best']['case_macro_f1']=.99
    if mutation=='duplicate_grid':r['soft_mse']['trials'][0]=copy.deepcopy(r['soft_mse']['trials'][1])
    if mutation=='cases':r['soft_mse']['trials'][0]['cases']={'wrong':{}}
    if mutation=='wrong_mode':r['soft_mse']['mode']='soft_bce'
    with pytest.raises(ValueError):api().choose_loss(r)
