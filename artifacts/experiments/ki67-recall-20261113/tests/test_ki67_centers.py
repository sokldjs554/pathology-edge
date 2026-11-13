import inspect
import numpy as np
import pytest
import torch
from pathology_edge import ki67_centers as c


def test_target_xy_clips_at_border_and_uses_max_not_sum():
    t=c.center_target(np.array([[0,0],[2,0]]),(4,5),sigma=1)
    assert t.shape==(4,5) and t.dtype==np.float32
    assert t[0,0]==t[0,2]==1
    assert t[0,1]==pytest.approx(.60653066)
    assert t[1,0]==pytest.approx(.60653066)
    assert t[3,4]==0  # outside both radius3 circular supports
    assert c.center_target(np.empty((0,2)),(4,5)).sum()==0
    one=c.center_target(np.array([[3,1]]),(5,6),sigma=1)
    assert one[1,3]==1 and one[3,1]<1


@pytest.mark.parametrize('points',[[[1.5,2]],[[-1,0]],[[5,0]],[[1,1],[1,1]],[[np.nan,0]]])
def test_target_rejects_invalid_or_duplicate_centers(points):
    with pytest.raises(ValueError):c.center_target(np.array(points),(5,5))


@pytest.mark.parametrize('sigma',[0,-1,True,'2',float('inf')])
def test_target_rejects_bad_sigma(sigma):
    with pytest.raises(ValueError):c.center_target(np.empty((0,2)),(4,4),sigma=sigma)


def test_focal_hand_value_and_gradient_direction():
    x=torch.zeros((1,1,1,2),requires_grad=True)
    t=torch.tensor([[[[1.,0.]]]])
    loss=c.center_focal_loss(x,t)
    assert loss.item()==pytest.approx(.3465735903)
    loss.backward()
    assert x.grad[0,0,0,0]<0 and x.grad[0,0,0,1]>0
    t[0,0,0,1]=.5
    assert c.center_focal_loss(x,t).item()==pytest.approx(.1841172198)


def test_focal_empty_reference_and_extreme_logits_stay_finite():
    assert c.center_focal_loss(torch.zeros(1,1,2,2),torch.zeros(1,1,2,2)).item()==pytest.approx(.6931471806)
    x=torch.tensor([[[[-1000.,1000.]]]],requires_grad=True)
    loss=c.center_focal_loss(x,torch.tensor([[[[1.,0.]]]]));loss.backward()
    assert torch.isfinite(loss) and torch.isfinite(x.grad).all()


@pytest.mark.parametrize('target',[torch.zeros(1,2,2),torch.ones(1,1,2,2)*2,torch.ones(1,1,2,2)*float('nan'),torch.zeros(1,1,2,2,dtype=torch.int64)])
def test_focal_rejects_malformed_target(target):
    with pytest.raises(ValueError):c.center_focal_loss(torch.zeros(1,1,2,2),target)


def test_plateau_has_one_center_and_distance_equality_kept():
    p,s=c.peak_candidates(np.full((4,4),.5))
    assert p.tolist()==[[1,1]] and s.tolist()==[.5]
    heat=np.zeros((12,12));heat[2,2]=.8;heat[2,6]=.8;heat[10,10]=.7
    found=c.decode_centers(heat,.8,4)
    assert found['points_xy'].tolist()==[[2,2],[6,2]]
    assert c.decode_centers(heat,.8,4.1)['points_xy'].tolist()==[[2,2]]
    assert c.decode_centers(np.zeros((4,4)),.1,4)['points_xy'].shape==(0,2)


@pytest.mark.parametrize('heat',[np.array([[np.nan]]),np.ones((2,2))*1.1,np.zeros((0,2)),np.zeros((1,2,2))])
def test_invalid_probability_map_rejected(heat):
    with pytest.raises(ValueError):c.decode_centers(heat,.1,4)


def test_model_preserves_odd_native_geometry_and_has_gradients():
    model=c.CenterDetector()
    out=model(torch.zeros(2,3,17,19))
    assert out.shape==(2,1,17,19)
    out.mean().backward()
    assert model.head.weight.grad is not None and torch.isfinite(model.head.weight.grad).all()
    with pytest.raises(ValueError):model(torch.zeros(1,1,17,19))


def test_image_only_inference_rejects_nan_weights():
    model=c.CenterDetector()
    with torch.no_grad():model.head.weight.fill_(float('nan'))
    with pytest.raises(ValueError):c.predict_centers(np.zeros((16,20,3),dtype=np.uint8),model,{'threshold':.2,'min_distance':6})
    assert list(inspect.signature(c.predict_centers).parameters)==['rgb','model','config']


def test_detector_preserves_gradient_through_negative_block_activations():
    model=c.CenterDetector()
    for name in ('e1','e2','bottom','d2','d1'):
        block=getattr(model,name)
        with torch.no_grad():
            for layer in (block[0],block[2]):
                layer.weight.zero_();layer.bias.zero_();layer.weight[0,0,1,1]=1
        x=-torch.ones(1,block[0].in_channels,5,5,requires_grad=True)
        x.retain_grad();out=block(x);out[0,0,2,2].backward()
        assert out[0,0,2,2].item()==pytest.approx(-.01)
        assert x.grad[0,0,2,2].item()==pytest.approx(.01)
