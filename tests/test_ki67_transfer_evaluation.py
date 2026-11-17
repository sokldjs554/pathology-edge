import importlib
import pytest


def api():return importlib.import_module('pathology_edge.ki67_transfer_evaluation')


def score(f1=.4,fraction=.5):
    return dict(localization={'f1':f1},two_class_macro_f1=f1,per_image=[dict(image='same',gt_fraction=.5,pred_fraction=fraction)])


def test_external_success_requires_detection_classification_and_same_population():
    a=score();b=score(.5)
    assert api().external_comparison(a,b)['passed']
    b['two_class_macro_f1']=.3
    assert not api().external_comparison(a,b)['passed']
    b=score(.5,None)
    r=api().external_comparison(a,b)
    assert not r['passed'] and r['fractions']['missing_B_ids']==['same']
    assert r['fractions']['B_mae_pp'] is None


def test_fraction_improvement_alone_cannot_pass():
    a=score(.4,.8);b=score(.3,.5)
    r=api().external_comparison(a,b)
    assert r['fractions']['passed'] and not r['passed']


def test_fixed_classifier_seed_pairing():
    assert [api().classifier_for_seed(s) for s in (20261117,20261118,20261119)]==['cnn-20261113','cnn-20261114','cnn-20261115']
    for seed in (True,0,'20261117'):
        with pytest.raises(ValueError):api().classifier_for_seed(seed)


def test_three_seed_denominator_includes_unadopted_diagnostics():
    rows=[dict(seed=s,eligible=False,passed=i==0) for i,s in enumerate((20261117,20261118,20261119))]
    r=api().stability(rows)
    assert r['passes']==1 and r['denominator']==3 and not r['all_three_passed']
    assert r['adopted_seeds']==0
    with pytest.raises(ValueError):api().stability(rows[:1])
    with pytest.raises(ValueError):api().stability([rows[0]]*3)
