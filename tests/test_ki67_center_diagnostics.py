import numpy as np
import pytest
from pathology_edge import ki67_center_diagnostics as d


def test_fn_stages_are_exclusive_and_class_specific():
    # Final: (2,2) suppresses(9,2), whose GT is(14,2); isolated low peak at30.
    p=np.array([[2,2],[9,2],[30,2],[50,2]])
    scores=np.array([.9,.8,.05,.7])
    gt=np.array([[2,2],[14,2],[30,2],[70,2],[50,2],[52,2]])
    r=d.diagnose_candidates(p,scores,gt,np.array([0,1,0,1,2,3]),dict(threshold=.1,min_distance=8))
    assert r['counts']==dict(matched=2,no_peak=1,below_threshold=1,distance_suppressed=1,assignment_competition=1)
    assert r['reasons']==['matched','distance_suppressed','below_threshold','no_peak','matched','assignment_competition']
    assert r['localization']['fn']==4
    assert r['by_class'][0]['below_threshold']==1
    assert r['by_class'][1]['distance_suppressed']==1


def test_exact_radius_and_empty_inputs():
    r=d.diagnose_candidates(np.array([[6,0]]),np.array([.1]),np.array([[0,0]]),np.array([0]),dict(threshold=.1,min_distance=4))
    assert r['counts']['matched']==1
    r=d.diagnose_candidates(np.empty((0,2)),np.empty(0),np.array([[1,1]]),np.array([1]),dict(threshold=.1,min_distance=4))
    assert r['counts']['no_peak']==1
    r=d.diagnose_candidates(np.empty((0,2)),np.empty(0),np.empty((0,2)),np.empty(0,dtype=int),dict(threshold=.1,min_distance=4))
    assert sum(r['counts'].values())==0


def test_selection_constraints_precede_f1_and_do_not_relax():
    def trial(threshold,f1,recall,pos,neg):
        return dict(split='validation',config=dict(threshold=threshold,min_distance=4),case_macro_f1=f1,case_macro_recall=recall,tumor_recalls=[pos,neg])
    floors=dict(case_macro_recall=.6,tumor_recalls=[.5,.7])
    a=trial(.1,.7,.5,.8,.8);b=trial(.05,.5,.7,.6,.8);c=trial(.02,.6,.7,.4,.8)
    r=d.select_recall_configuration([a,b,c],floors)
    assert r['selected']['config']==b['config'] and r['feasible_trials']==1
    assert d.select_recall_configuration([a,c],floors)['selected'] is None
    with pytest.raises(ValueError):d.select_recall_configuration([{**b,'split':'test'}],floors)


def test_class_accounting_separates_misses_confusion_and_unmatched():
    # One correct positive, one negative -> positive confusion, one missednegative;
    # plus unmatched positive. Predcounts=3positive,0negative; truth=1positive,2negative.
    r=d.class_accounting(np.array([[0,0],[20,0],[90,0]]),np.array([0,0,0]),np.array([[0,0],[20,0],[40,0]]),np.array([0,1,1]))
    assert r['missed_reference_by_class']==[0,1,0,0]
    assert r['unmatched_prediction_by_class']==[1,0,0,0]
    assert r['matched_confusion'][1][0]==1
    assert r['predicted_counts']==[3,0,0,0] and r['reference_counts']==[1,2,0,0]


@pytest.mark.parametrize('classes',[np.array([4]),np.array([0.,1.]),np.array([],dtype=int)])
def test_invalid_reference_class_labels_rejected(classes):
    with pytest.raises(ValueError):d.diagnose_candidates(np.array([[1,1]]),np.array([.5]),np.array([[1,1]]),classes,dict(threshold=.1,min_distance=4))
