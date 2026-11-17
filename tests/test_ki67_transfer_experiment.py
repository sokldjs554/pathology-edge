import copy
import json
import pytest
from pathology_edge import ki67_transfer_experiment as m


def records():
    trial=dict(epoch=1,split='validation',config=dict(threshold=.1,min_distance=6))
    return [dict(arm=a,seed=s,epochs=24,selected=None,diagnostic=copy.deepcopy(trial),evaluation_trial=copy.deepcopy(trial),evaluation_checkpoint='diagnostic.pt') for a in m.ARMS for s in m.SEEDS]


def test_diagnostics_are_included_even_when_none_is_adopted():
    result=m.primary_models(dict(models=records()[::-1]))
    assert [r['seed'] for r in result]==list(m.SEEDS)
    assert all(r['selected'] is None and r['evaluation_checkpoint']=='diagnostic.pt' for r in result)


@pytest.mark.parametrize('fault',['missing','duplicate','wrong_arm','incomplete','wrong_epoch','wrong_cutoff','wrong_split','wrong_checkpoint','changed_trial'])
def test_invalid_selection_never_reaches_evaluation(fault):
    rows=records()
    if fault=='missing':rows.pop()
    if fault=='duplicate':rows[-1]=rows[0]
    if fault=='wrong_arm':rows[0]['arm']='other'
    if fault=='incomplete':rows[0]['epochs']=23
    if fault=='wrong_epoch':rows[0]['evaluation_trial']['epoch']=True
    if fault=='wrong_cutoff':rows[0]['evaluation_trial']['config']['threshold']=.111
    if fault=='wrong_split':rows[0]['evaluation_trial']['split']='test'
    if fault=='wrong_checkpoint':rows[0]['evaluation_checkpoint']='selected.pt'
    if fault=='changed_trial':rows[0]['evaluation_trial']['epoch']=2
    with pytest.raises(ValueError):m.primary_models(dict(models=rows))


def test_hash_checked_source_and_protocol(tmp_path,monkeypatch):
    root=tmp_path;source=root/'source.py';source.write_text('original')
    p={**m.FIXED,'source_hashes':{str(source):m.sha(source)},'input_hashes':{},'learner_hashes':{}}
    (root/'protocol.json').write_text(json.dumps(p));(root/'protocol.sha256').write_text(m.sha(root/'protocol.json'))
    real=m.sha
    monkeypatch.setattr(m,'sha',lambda p:m.WEIGHT_SHA256 if str(p).endswith('official-weights.pth') else real(p))
    assert m.checked(root)['selection_fallback']=='diagnostic'
    source.write_text('changed')
    with pytest.raises(ValueError):m.checked(root)
    source.write_text('original');p['epochs']=12;(root/'protocol.json').write_text(json.dumps(p));(root/'protocol.sha256').write_text(real(root/'protocol.json'))
    with pytest.raises(ValueError):m.checked(root)


def test_missing_workers_cannot_create_lock(tmp_path,monkeypatch):
    monkeypatch.setattr(m,'checked',lambda *a,**k:{})
    with pytest.raises(ValueError):m.seal(tmp_path)
    assert not (tmp_path/'selection-lock.json').exists()
