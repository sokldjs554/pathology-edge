"""Prevent a train-only diagnostic from silently changing membership or budget."""
import copy
import importlib.util
from pathlib import Path
import pytest


def validator():
    path=Path(__file__).resolve().parents[1]/'scripts/audit_ki67_supervision_spike.py'
    spec=importlib.util.spec_from_file_location('supervision_spike_audit',path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    return m.verify_spike_protocol


def fixture():
    images=[f'{c}_{i}.png' for c in range(15) for i in range(8)]
    cases={str(c):8 for c in range(15)}
    p=dict(mode='soft_mse',images=images,cases=cases,seed=20261117,steps=300,batch8=True,learning_rate=.001,threads=1,
           augmentation='same paired rot90/flips RGB[.9,1.1]',source_sha256='source')
    return p,images,cases


def test_original_training_membership_accepted():
    p,images,cases=fixture();validator()(p,'soft_mse',images,cases,'source')


@pytest.mark.parametrize('mutation',['image','cases','seed','steps','source','mode','augmentation'])
def test_diagnostic_changes_rejected(mutation):
    p,images,cases=fixture();p=copy.deepcopy(p)
    if mutation=='image':p['images'][0]='test.png'
    if mutation=='cases':p['cases']['0']=7
    if mutation=='seed':p['seed']+=1
    if mutation=='steps':p['steps']=301
    if mutation=='source':p['source_sha256']='other'
    if mutation=='mode':p['mode']='focal'
    if mutation=='augmentation':p['augmentation']='none'
    with pytest.raises(ValueError):validator()(p,'soft_mse',images,cases,'source')
