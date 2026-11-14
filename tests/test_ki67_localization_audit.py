import importlib.util
from pathlib import Path
import numpy as np
import pytest

@pytest.fixture
def audit():
    path=Path(__file__).resolve().parents[1]/'scripts/audit_ki67_localization.py'
    if not path.exists():pytest.fail('localization audit missing')
    spec=importlib.util.spec_from_file_location('localization_audit',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def test_saved_corrections_reject_out_of_image_and_excess_shift(audit):
    p=np.array([[20,20],[0,0]])
    audit.validate_corrected(p,np.array([[28,29],[0,0]]),(40,40))
    for bad in (np.array([[34,20],[0,0]]),np.array([[20,20],[-1,0]]),np.array([[20,20],[40,0]])):
        with pytest.raises(ValueError):audit.validate_corrected(p,bad,(40,40))

def test_saved_corrections_reject_fractional_or_misaligned_rows(audit):
    with pytest.raises(ValueError):audit.validate_corrected(np.array([[20,20]]),np.array([[20.5,20]]),(40,40))
    with pytest.raises(ValueError):audit.validate_corrected(np.array([[20,20]]),np.empty((0,2)),(40,40))

def test_independent_test_criteria_requires_every_seed_and_class(audit):
    base=dict(localization=dict(fp=10,fn=10),cases={'a':{'recall':.5}},tumor_recalls=[.5,.5])
    changed=dict(localization=dict(fp=9,fn=9),cases={'a':{'recall':.5}},tumor_recalls=[.49,.6])
    assert audit.independent_test_pass(base,changed) is False
    changed['tumor_recalls']=[.5,.6]
    assert audit.independent_test_pass(base,changed) is True
