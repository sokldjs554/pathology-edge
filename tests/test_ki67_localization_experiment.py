import importlib
import json
from copy import deepcopy
import numpy as np
import pytest

@pytest.fixture
def api():
    try:return importlib.import_module('pathology_edge.ki67_localization_experiment')
    except ModuleNotFoundError:pytest.fail('localization experiment runner missing')

def test_sampler_balances_gt_units_not_candidate_multiplicity(api):
    samples=[dict(split='train',case_id='a',points=np.array([[30,30]]*20+[[60,60],[80,80]]),gt_points=np.array([[30,30],[60,60]]),rgb=np.zeros((112,112,3),np.uint8))]
    pools=api.make_local_pools(samples,np.random.default_rng(3))
    draws=api.local_draws(pools,2000,np.random.default_rng(9))
    positives=[j for label,(i,j) in draws if label==1]
    assert 430<sum(j==20 for j in positives)<570
    assert len(positives)==1000
    samples[0]['split']='validation'
    with pytest.raises(ValueError):api.make_local_pools(samples,np.random.default_rng(3))

def test_no_eligible_seed_skips_before_data_or_model_access(api,tmp_path,monkeypatch):
    monkeypatch.setattr(api,'checked',lambda *a,**k:{})
    (tmp_path/'selection.json').write_text(json.dumps({'models':[dict(seed=s,selected=None) for s in api.SEEDS]}))
    monkeypatch.setattr(api,'loaded_detectors',lambda *a:pytest.fail('should not load detector'))
    api.evaluate(tmp_path)
    assert json.loads((tmp_path/'internal-not-run.json').read_text())['new_inference_images']==0

def test_all_three_outcomes_required_for_stability(api):
    result=api.stability_summary([dict(seed=20261117,eligible=True,test_passed=True),dict(seed=20261118,eligible=False,test_passed=False),dict(seed=20261119,eligible=False,test_passed=False)])
    assert result['all_three_test_passed'] is False and result['test_passes']==1 and result['denominator']==3
    with pytest.raises(ValueError):api.stability_summary([dict(seed=20261117,eligible=True,test_passed=True)])

def test_protocol_hash_change_blocks_stages(api,tmp_path):
    (tmp_path/'protocol.json').write_text('{}');(tmp_path/'protocol.sha256').write_text('0'*64)
    with pytest.raises(ValueError,match='Protocol'):api.checked(tmp_path)
