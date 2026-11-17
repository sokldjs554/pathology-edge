import importlib,json
import pytest
from pathology_edge.ki67_experiment import sha
from test_ki67_normalized import fixture,records


def pipeline():
    try:return importlib.import_module('pathology_edge.ki67_normalized_pipeline')
    except ModuleNotFoundError:pytest.fail('Normalized pipeline module missing')


def score(f1=.5,mae=8,ids=('a','b'),missing=False):
    return dict(macro_f1=f1,case_ratio_mae_pp=mae,case_ratio_valid=len(ids)-(1 if missing else 0),
                per_case=[dict(case_id=k,ratio_error_pp=None if missing and i==0 else mae) for i,k in enumerate(ids)])


def test_classifier_is_selected_on_both_f1_and_same_case_fraction_coverage():
    p=pipeline();scores={n:score() for n in p.ARMS};scores['lr']=score(.9,2,('b','c'));scores['cnn-20261114']=score(.8,11);scores['cnn-20261115']=score(.7,7)
    result=p.choose_classifier(score(.4,10),scores,'cnn-20261113',('a','b'))
    assert result['selected_classifier']=='cnn-20261115' and result['validation_pipeline_passed']


@pytest.mark.parametrize('bad',[score(.9,2,missing=True),score(float('nan'),2),score(.9,float('nan')),score(.9,2,('a','a'))])
def test_missing_or_nonfinite_candidate_cannot_win(bad):
    p=pipeline();scores={n:score(.3,12) for n in p.ARMS};scores['lr']=bad
    r=p.choose_classifier(score(.4,10),scores,'cnn-20261113',('a','b'))
    assert r['selected_classifier']=='cnn-20261113' and not r['validation_pipeline_passed']


def test_reference_seed_mapping_and_tie_order_are_fixed():
    p=pipeline();assert [p.reference_classifier(s) for s in (20261117,20261118,20261119)]==['cnn-20261113','cnn-20261114','cnn-20261115']
    assert p.choose_classifier(score(.4,10),{n:score() for n in p.ARMS},'cnn-20261113',('a','b'))['selected_classifier']=='lr'
    with pytest.raises(ValueError):p.reference_classifier(20261120)


def test_pipeline_goal_does_not_pass_by_losing_valid_case():
    p=pipeline();assert not all(p.pipeline_criteria(score(.4,10),score(.7,1,missing=True),('a','b')).values())
    assert all(p.pipeline_criteria(score(.4,10),score(.5,9),('a','b')).values())


def noeligible(tmp_path):
    _,root,_,_=fixture(tmp_path);(root/'selection.json').write_text(json.dumps({'models':records()}));(root/'selection-lock.json').write_text(json.dumps(dict(protocol_sha256=sha(root/'protocol.json'),selection_sha256=sha(root/'selection.json'),evidence_hashes={})));return root


def test_no_eligible_classification_and_evaluation_never_open_missing_data(tmp_path):
    p=pipeline();root=noeligible(tmp_path);p.select_classifiers(root);p.evaluate(root);p.evaluate(root,True)
    for tag in ('internal','external'):assert json.loads((root/(tag+'-not-run.json')).read_text())['new_inference_images']==0
    r=json.loads((root/'stability.json').read_text());assert r['denominator']==3 and r['test_passes']==0 and r['pipeline_passes']==0


def test_classifier_lock_change_prevents_any_holdout_access(tmp_path):
    p=pipeline();root=noeligible(tmp_path);p.select_classifiers(root);(root/'classifier-selection.json').write_text('{}')
    with pytest.raises(ValueError):p.evaluate(root)
    assert not (root/'internal-not-run.json').exists()
