"""Training ownership, balanced sampling, and selection lock boundaries."""
import importlib
import json
import numpy as np
import pytest

@pytest.fixture
def api():
    try:return importlib.import_module('pathology_edge.ki67_union_experiment')
    except ModuleNotFoundError:pytest.fail('union experiment runner missing')

def test_balanced_sampler_uses_cases_then_examples(api):
    pools={0:{'a':[(0,0)],'b':[(1,i) for i in range(90)]},1:{'a':[(2,0)],'b':[(3,0)]}}
    draws=api.balanced_draws(pools,1000,np.random.default_rng(9))
    assert np.bincount([d[0] for d in draws]).tolist()==[500,500]
    assert 200<sum(label==0 and item[0]==0 for label,item in draws)<300
    with pytest.raises(ValueError):api.balanced_draws({0:{},1:pools[1]},64,np.random.default_rng(9))

def test_training_pool_excludes_other_splits_and_empty_truth_negatives(api):
    record=dict(split='train',case_id='a',rgb=np.zeros((64,64,3),np.uint8),gt_points=np.array([[30,30]]),gt_classes=np.array([0]),points=np.array([[30,30],[50,50]]))
    pools=api.make_pools([record],np.random.default_rng(8))
    assert len(pools[1]['a'])==1
    record['split']='validation'
    with pytest.raises(ValueError):api.make_pools([record],np.random.default_rng(8))

def test_all_three_seed_reports_required_before_lock(api):
    for seeds in ([20261117],[20261117,20261118,20261118]):
        with pytest.raises(ValueError):api.validate_selection({'models':[dict(seed=s,selected=None) for s in seeds]})
    result=api.validate_selection({'models':[dict(seed=s,selected=None) for s in api.SEEDS]})
    assert result==[]

def test_evaluation_without_eligible_seed_never_loads_data(api,tmp_path,monkeypatch):
    p={'scope':'reused','seeds':list(api.SEEDS)}
    monkeypatch.setattr(api,'checked',lambda root,selected=False:p)
    (tmp_path/'selection.json').write_text(json.dumps({'models':[dict(seed=s,selected=None) for s in api.SEEDS]}))
    monkeypatch.setattr(api,'load_sample',lambda *a:pytest.fail('must not access test image'))
    monkeypatch.setattr(api,'loaded_detectors',lambda *a:pytest.fail('must not load models'))
    api.evaluate(tmp_path)
    assert json.loads((tmp_path/'internal-not-run.json').read_text())['new_inference_images']==0

def test_protocol_tampering_rejected(api,tmp_path):
    (tmp_path/'protocol.json').write_text('{}')
    (tmp_path/'protocol.sha256').write_text('0'*64)
    with pytest.raises(ValueError,match='Protocol'):api.checked(tmp_path)
