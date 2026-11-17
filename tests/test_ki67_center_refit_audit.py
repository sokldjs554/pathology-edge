import importlib.util
from pathlib import Path
import numpy as np
import pytest


def auditor():
    path=Path(__file__).resolve().parents[1]/'scripts/audit_ki67_center_refit.py'
    if not path.exists():pytest.fail('refit auditor is missing')
    spec=importlib.util.spec_from_file_location('refit_auditor',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def test_peak_offsets_accept_empty_image_but_reject_missing_or_nonmonotonic():
    a=auditor();p=np.array([[1,2],[3,4]]);s=np.array([.2,.1],dtype=np.float32)
    a.validate_saved_peaks(p,s,np.array([0,0,2]),2,(8,8))
    for offsets in (np.array([0,2]),np.array([0,2,1]),np.array([1,1,2]),np.array([0,0,3]),np.array([0.,0.,2.])):
        with pytest.raises(ValueError):a.validate_saved_peaks(p,s,offsets,2,(8,8))


@pytest.mark.parametrize('points', [np.array([[8,2]]),np.array([[-1,2]]),np.array([[1.2,2]]),np.array([[np.nan,2]])])
def test_peak_coordinates_reject_outside_or_noninteger(points):
    a=auditor()
    with pytest.raises(ValueError):a.validate_saved_peaks(points,np.array([.2]),np.array([0,1]),1,(8,8))


def test_peak_scores_and_duplicate_coordinates_are_rejected():
    a=auditor()
    for scores in (np.array([.009]),np.array([1.1]),np.array([np.nan])):
        with pytest.raises(ValueError):a.validate_saved_peaks(np.array([[1,2]]),scores,np.array([0,1]),1,(8,8))
    with pytest.raises(ValueError):a.validate_saved_peaks(np.array([[1,2],[1,2]]),np.array([.2,.1]),np.array([0,2]),1,(8,8))


def test_reference_row_binds_gt_classes_and_case_id():
    a=auditor();row=dict(image='a',case_id='case1',gt_points=[[2,3]],gt_classes=[0]);metadata=dict(image='a',case_id='case1')
    a.verify_reference(row,metadata,np.array([[2,3]]),np.array([0]))
    for changed in ({**row,'case_id':'case2'},{**row,'gt_classes':[1]},{**row,'gt_points':[[3,2]]}):
        with pytest.raises(ValueError):a.verify_reference(changed,metadata,np.array([[2,3]]),np.array([0]))


def test_audit_excludes_epoch_zero_from_eligible_choices():
    a=auditor();base=dict(localization=dict(fp=10,fn=10),cases={'a':dict(recall=.5)})
    t=dict(split='validation',epoch=0,localization=dict(fp=8,fn=8),cases={'a':dict(recall=.6)},case_macro_f1=.6,case_macro_recall=.6,tumor_recalls=[.6,.6],config=dict(threshold=.1,min_distance=4))
    assert a.refit_choice([t],base) is None
    assert a.refit_choice([{**t,'epoch':1}],base)['epoch']==1
