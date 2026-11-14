import importlib.util
from pathlib import Path
import pytest
from test_ki67_normalized_pipeline import score


def audit_module():
    path=Path(__file__).resolve().parents[1]/'scripts/audit_ki67_normalized.py'
    if not path.exists():pytest.fail('Normalized independent audit missing')
    spec=importlib.util.spec_from_file_location('audit_normalized',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def test_independent_classifier_choice_rejects_coverage_and_error_tradeoffs():
    m=audit_module();names=('lr','cnn-20261113','cnn-20261114','cnn-20261115');scores={n:score(.3,11) for n in names};scores['lr']=score(.9,1,missing=True);scores[names[2]]=score(.8,12);scores[names[3]]=score(.6,8)
    assert m.independent_classifier_choice(score(.4,10),scores,names[1],['a','b'])==(names[3],True)
    scores[names[3]]=score(.6,8,('a','c'));assert m.independent_classifier_choice(score(.4,10),scores,names[1],['a','b'])==(names[1],False)


def test_epoch_grid_requires_every_fixed_configuration_once():
    m=audit_module();h=[dict(epoch=e,train_loss=1.,trials=[dict(epoch=e,split='validation',config=dict(threshold=t,min_distance=d)) for t in m.THRESHOLDS for d in m.DISTANCES]) for e in range(1,25)]
    m.validate_history(h)
    h[-1]['trials'][-1]=h[-1]['trials'][0]
    with pytest.raises(ValueError):m.validate_history(h)


def test_grid_rejects_missing_epoch_and_nonfinite_training_loss():
    m=audit_module()
    with pytest.raises(ValueError):m.validate_history([])
    h=[dict(epoch=e,train_loss=float('nan'),trials=[]) for e in range(1,25)]
    with pytest.raises(ValueError):m.validate_history(h)
