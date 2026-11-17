import importlib
import json
from pathlib import Path
import numpy as np
import pytest
import torch
from pathology_edge.ki67_centers import CenterDetector
from pathology_edge.ki67_evaluation import count_metrics
from pathology_edge.ki67_experiment import sha


def load_refit():
    try:
        return importlib.import_module('pathology_edge.ki67_center_refit')
    except ModuleNotFoundError:
        pytest.fail('fixed detector refit module is missing')


def trial(epoch,tp=12,fp=5,fn=8):
    c=count_metrics(tp,fp,fn)
    return dict(split='validation',epoch=epoch,config={'threshold':.1,'min_distance':4},localization=c,cases={'a':c},case_macro_f1=c['f1'],case_macro_recall=c['recall'],tumor_recalls=[.7,.5])


def baseline():
    return trial(0,10,8,10)


def test_optimizer_preserves_pretrained_weights_and_starts_new_state():
    refit=load_refit()
    torch.set_num_threads(2);model=CenterDetector()
    with torch.no_grad():model.head.bias.fill_(1.25)
    before={k:v.clone() for k,v in model.state_dict().items()}
    optimizer=refit.refit_optimizer(model)
    assert optimizer.state=={} and optimizer.param_groups[0]['lr']==.001
    assert all(torch.equal(v,model.state_dict()[k]) for k,v in before.items())
    optimizer.zero_grad();model(torch.ones(1,3,16,16)).square().mean().backward();optimizer.step()
    assert optimizer.state and not torch.equal(model.head.bias,before['head.bias'])


def test_epoch_zero_control_cannot_be_selected_as_refit():
    refit=load_refit()
    unchanged=trial(0,18,1,2);trained=trial(1)
    assert refit.choose_refit([unchanged,trained],baseline())['selected']==trained
    assert refit.choose_refit([unchanged],baseline())['selected'] is None


def test_refit_selection_keeps_tumor_recall_floor():
    refit=load_refit()
    t=trial(1);t['tumor_recalls'][0]=.55
    assert refit.choose_refit([t],baseline())['selected'] is None


@pytest.mark.parametrize('epoch',[-1,25,1.5,True])
def test_refit_rejects_invalid_epoch(epoch):
    refit=load_refit()
    with pytest.raises(ValueError):refit.choose_refit([trial(epoch)],baseline())


def sample(split='validation'):
    return dict(split=split,case_id='a',points=np.array([[10,10]]),scores=np.array([.7],dtype=np.float32),gt_points=np.array([[10,10]]),gt_classes=np.array([0]))


def test_grid_preserves_float32_cutoff_and_empty_images():
    refit=load_refit()
    empty={**sample(), 'points':np.empty((0,2)), 'scores':np.empty(0), 'gt_points':np.empty((0,2)), 'gt_classes':np.empty(0,dtype=int)}
    rows=refit.configuration_trials([sample(),empty],1)
    assert len(rows)==36
    assert {r['config']['threshold'] for r in rows}=={.01,.02,.03,.05,.075,.1,.15,.2,.3,.5,.7,.9}
    assert {r['config']['min_distance'] for r in rows}=={4,6,8}
    assert all(r['localization']['tp']==0 for r in rows if r['config']['threshold']==.7)
    assert all(r['localization']['tp']==1 for r in rows if r['config']['threshold']==.5)


@pytest.mark.parametrize('split',['train','test'])
def test_grid_refuses_non_validation_labels(split):
    refit=load_refit()
    with pytest.raises(ValueError):refit.configuration_trials([sample(split)],1)


def frozen_fixture(tmp_path):
    root=tmp_path/'run';root.mkdir();source=tmp_path/'source.py';source.write_text('version=1')
    p=dict(schema='ki67-center-refit.v1',seeds=[20261117,20261118,20261119],epochs=24,learning_rate=.001,batch_size=8,torch_threads=2,
        thresholds=[.01,.02,.03,.05,.075,.1,.15,.2,.3,.5,.7,.9],distances=[4,6,8],floors={'case_macro_recall':.4797951648158369,'tumor_recalls':[270/483,439/1292]},source_hashes={str(source):sha(source)},input_hashes={},parent=str(tmp_path/'missing-parent'),prior=str(tmp_path/'missing-prior'),external=str(tmp_path/'missing-external'))
    (root/'protocol.json').write_text(json.dumps(p));(root/'protocol.sha256').write_text(sha(root/'protocol.json'))
    (root/'selection.json').write_text(json.dumps({'models':[{'seed':s,'selected':None,'checkpoint':None} for s in p['seeds']]}))
    (root/'selection-lock.json').write_text(json.dumps({'protocol_sha256':sha(root/'protocol.json'),'selection_sha256':sha(root/'selection.json'),'evidence_hashes':{}}))
    return root,source


def test_source_and_protocol_hash_drift_are_rejected(tmp_path):
    refit=load_refit()
    root,source=frozen_fixture(tmp_path);assert refit.checked(root,selected=True)['epochs']==24
    source.write_text('version=2')
    with pytest.raises(ValueError):refit.checked(root)
    source.write_text('version=1');(root/'protocol.json').write_text('{}')
    with pytest.raises(ValueError):refit.checked(root)


def test_selection_drift_is_rejected(tmp_path):
    refit=load_refit()
    root,_=frozen_fixture(tmp_path);(root/'selection.json').write_text('{}')
    with pytest.raises(ValueError):refit.checked(root,selected=True)


def test_no_eligible_seed_skips_without_opening_missing_holdouts(tmp_path):
    refit=load_refit()
    root,_=frozen_fixture(tmp_path)
    refit.evaluate(root);refit.evaluate(root,external=True)
    for tag in ('internal','external'):
        assert json.loads((root/(tag+'-not-run.json')).read_text())['new_inference_images']==0
        assert not (root/(tag+'-started.json')).exists()
    status=json.loads((root/'stability.json').read_text())
    assert status['denominator']==3 and status['test_passes']==0
    assert len(status['seeds'])==3 and not status['all_three_test_passed']


def test_epoch_zero_reproduces_original_validation_summary():
    refit=load_refit();base=baseline()
    expected=dict(validation_case_macro_f1=base['case_macro_f1'],validation_case_macro_recall=base['case_macro_recall'])
    refit.verify_initial_baseline(base,expected)
    expected['validation_case_macro_recall']+=.01
    with pytest.raises(ValueError):refit.verify_initial_baseline(base,expected)
