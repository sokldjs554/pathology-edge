"""Independent audit must reject changed candidates, counts and eligibility."""
import importlib.util
from pathlib import Path
from copy import deepcopy
import numpy as np
import pytest

@pytest.fixture
def audit():
    path=Path(__file__).resolve().parents[1]/'scripts/audit_ki67_union.py'
    if not path.exists():pytest.fail('independent audit missing')
    spec=importlib.util.spec_from_file_location('union_audit',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def test_independent_decoder_and_counts(audit):
    r=dict(case_id='a',points=[[0,0],[2,0],[20,20]],gt_points=[[0,0],[30,30]],gt_classes=[0,1])
    got=audit.independent_summary([r],[np.array([.9,.8,.7])],dict(threshold=.5,min_distance=4))
    assert [got['localization'][k] for k in ('tp','fp','fn')]==[1,1,1]
    assert got['tumor_recalls']==[1,0]
    bad=deepcopy(got);bad['localization']['fp']=2
    with pytest.raises(ValueError):audit.compare_metrics(got,bad)

def test_independent_selection_refuses_changed_eligibility(audit):
    baseline={'localization':{'fp':6,'fn':6},'cases':{'a':{'recall':.4}}}
    floors={'case_macro_recall':.5,'tumor_recalls':[.5,.5]}
    good=dict(split='validation',epoch=1,config=dict(threshold=.5,min_distance=4),localization=dict(fp=5,fn=5),case_macro_f1=.5,case_macro_recall=.5,tumor_recalls=[.5,.5],cases={'a':dict(recall=.5)})
    assert audit.independent_choice([good],baseline,floors)==good
    good['tumor_recalls'][0]=.4
    assert audit.independent_choice([good],baseline,floors) is None

def test_candidate_reference_must_match_exact_points(audit):
    with pytest.raises(ValueError):audit.exact_points([[1,2]],[[2,1]])
    audit.exact_points([],[])

def test_saved_float32_score_is_compared_at_its_exact_value(audit):
    # np.float32(.7) is 0.699999988..., strictly below the configured .7.
    points,scores=audit.independent_decode([[0,0]],np.array([.7],dtype=np.float32),dict(threshold=.7,min_distance=4))
    assert len(points)==0
