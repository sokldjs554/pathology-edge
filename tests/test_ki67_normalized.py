import importlib
import json
import numpy as np
import pytest
import torch
from pathology_edge.ki67_centers import CenterDetector,predict_centers
from pathology_edge.ki67_experiment import sha


def mod(name='ki67_normalized_experiment'):
    try:return importlib.import_module('pathology_edge.'+name)
    except ModuleNotFoundError:pytest.fail('Normalized detector feature missing: '+name)


def test_normalized_native_geometry_gradients_and_batch_independence():
    cls=mod('ki67_normalized_centers').NormalizedCenterDetector
    torch.set_num_threads(1);torch.manual_seed(1);m=cls(4);x=torch.rand(2,3,17,19)
    y=m(x);assert y.shape==(2,1,17,19);y.square().mean().backward()
    assert all(p.grad is not None and torch.isfinite(p.grad).all() for p in m.parameters())
    m.eval();assert torch.allclose(m(x[:1]),m(x)[:1],rtol=1e-5,atol=1e-6)
    assert predict_centers(np.zeros((17,19,3),dtype=np.uint8),m,{'threshold':.5,'min_distance':4})['probability_map'].shape==(17,19)
    assert sum(p.numel() for p in CenterDetector().parameters())==7537


@pytest.mark.parametrize('width',[0,8,True,16.0])
def test_width_contract_rejects_unregistered_architecture(width):
    cls=mod('ki67_normalized_centers').NormalizedCenterDetector
    with pytest.raises(ValueError):cls(width)


def test_checkpoint_width_cannot_be_silently_reinterpreted():
    cls=mod('ki67_normalized_centers').NormalizedCenterDetector
    with pytest.raises(RuntimeError):cls(16).load_state_dict(cls(4).state_dict(),strict=True)
    with pytest.raises(ValueError):cls(4)(torch.full((1,3,16,16),float('nan')))


def records():
    return [dict(width=w,seed=s,selected=None,checkpoint=None,additional_epochs=24) for w in (4,16) for s in (20261117,20261118,20261119)]


def test_only_primary_width16_enters_three_seed_denominator():
    m=mod();assert [r['seed'] for r in m.primary_models({'models':records()})]==[20261117,20261118,20261119]
    assert all(r['width']==16 for r in m.primary_models({'models':records()[::-1]}))


@pytest.mark.parametrize('mutation',['missing','duplicate','unexpected_seed','unexpected_width','not_complete'])
def test_selection_requires_all_six_unique_complete_workers(mutation):
    m=mod();r=records()
    if mutation=='missing':r.pop()
    if mutation=='duplicate':r[-1]=r[0].copy()
    if mutation=='unexpected_seed':r[0]['seed']=0
    if mutation=='unexpected_width':r[0]['width']=8
    if mutation=='not_complete':r[0]['additional_epochs']=23
    with pytest.raises(ValueError):m.primary_models({'models':r})


def fixture(tmp_path):
    m=mod();root=tmp_path/'run';root.mkdir();source=tmp_path/'source.py';source.write_text('a=1')
    p={**m.FIXED,'source_hashes':{str(source):sha(source)},'input_hashes':{}}
    (root/'protocol.json').write_text(json.dumps(p));(root/'protocol.sha256').write_text(sha(root/'protocol.json'))
    return m,root,source,p


def test_protocol_and_source_drift_stop_worker(tmp_path):
    m,root,source,p=fixture(tmp_path);assert m.checked(root)['primary_width']==16
    source.write_text('a=2')
    with pytest.raises(ValueError):m.checked(root)
    source.write_text('a=1');p['primary_width']=4;(root/'protocol.json').write_text(json.dumps(p));(root/'protocol.sha256').write_text(sha(root/'protocol.json'))
    with pytest.raises(ValueError):m.checked(root)


def test_seal_refuses_partial_jobs_without_writing_a_selection(tmp_path):
    m,root,_,_=fixture(tmp_path)
    with pytest.raises(ValueError):m.seal(root)
    assert not (root/'selection.json').exists()


def test_seal_binds_every_worker_evidence_and_rejects_later_drift(tmp_path):
    m,root,_,_=fixture(tmp_path)
    for r in records():
        p=root/m.job_name(r['width'],r['seed']);p.mkdir();(p/'result.json').write_text(json.dumps(r));(p/'proof.txt').write_text('original')
        (p/'complete.json').write_text(json.dumps({'protocol_sha256':sha(root/'protocol.json'),'evidence_hashes':{n:sha(p/n) for n in ('result.json','proof.txt')}}))
    m.seal(root);m.checked(root,selected=True)
    (root/m.job_name(16,20261119)/'proof.txt').write_text('changed')
    with pytest.raises(ValueError):m.checked(root,selected=True)
