import importlib
import numpy as np
import pytest
import torch


def api():
    return importlib.import_module('pathology_edge.ki67_transfer')


def test_frozen_encoder_native_shape_and_trainable_decoder():
    m=api();torch.set_num_threads(1);torch.manual_seed(7)
    model=m.TransferCenterDetector();x=torch.rand(2,3,33,35)
    original={k:v.clone() for k,v in model.features.state_dict().items()}
    out=model(x);assert out.shape==(2,1,33,35)
    out.square().mean().backward()
    assert all(p.grad is None and not p.requires_grad for p in model.features.parameters())
    assert all(p.grad is not None and torch.isfinite(p.grad).all() for p in model.decoder.parameters())
    torch.optim.Adam(model.decoder.parameters()).step()
    assert all(torch.equal(v,original[k]) for k,v in model.features.state_dict().items())
    model.eval();assert torch.allclose(model(x[:1]),model(x)[:1],rtol=1e-4,atol=1e-5)


def test_weight_loading_is_exact_strict_and_finite():
    m=api();a=m.TransferCenterDetector();state={k:v.clone() for k,v in a.features.state_dict().items()}
    b=m.TransferCenterDetector(state)
    assert all(torch.equal(v,b.features.state_dict()[k]) for k,v in state.items())
    bad=dict(state);bad.pop(next(iter(bad)))
    with pytest.raises((ValueError,RuntimeError)):m.TransferCenterDetector(bad)
    bad=dict(state);bad[next(iter(bad))]=torch.full_like(next(iter(state.values())),float('nan'))
    with pytest.raises(ValueError):m.TransferCenterDetector(bad)


@pytest.mark.parametrize('x',[torch.ones(1,3,16,20),torch.ones(1,4,32,32),torch.ones(0,3,32,32),torch.full((1,3,32,32),float('nan')),torch.ones(1,3,32,32)*1.1])
def test_input_rejects_invalid_geometry_or_rgb(x):
    with pytest.raises(ValueError):api().TransferCenterDetector()(x)


def test_sampling_equalizes_cases_without_relabeling_or_heldout():
    rows=[dict(split='train',case_id='A')]+[dict(split='train',case_id='B') for _ in range(3)]
    p=api().balanced_probabilities(rows)
    assert p==pytest.approx([.5,1/6,1/6,1/6])
    assert rows[0]==dict(split='train',case_id='A')
    rows[-1]['split']='test'
    with pytest.raises(ValueError):api().balanced_probabilities(rows)


@pytest.mark.parametrize('rows',[[],[{}],[dict(split='train',case_id='')]])
def test_sampler_rejects_bad_membership(rows):
    with pytest.raises(ValueError):api().balanced_probabilities(rows)


def test_decoder_initialization_is_paired_despite_encoder_weights():
    m=api();torch.manual_seed(5);state=m.TransferCenterDetector().features.state_dict()
    torch.manual_seed(19);a=m.TransferCenterDetector()
    torch.manual_seed(19);b=m.TransferCenterDetector(state)
    assert all(torch.equal(v,b.decoder.state_dict()[k]) for k,v in a.decoder.state_dict().items())
    assert any(not torch.equal(v,b.features.state_dict()[k]) for k,v in a.features.state_dict().items())
