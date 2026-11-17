import importlib.util
from pathlib import Path
import numpy as np
import pytest


def api():
    p=Path(__file__).resolve().parents[1]/'scripts/audit_ki67_transfer.py'
    spec=importlib.util.spec_from_file_location('transfer_audit',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def test_independent_cell_summary_includes_unmatched_and_false_class_cells():
    rows=[dict(image='a',case_id='case',points=[[2,2],[20,20]],gt_points=[[2,2],[50,50]],gt_classes=[0,1],classes={'cnn':[1,0]})]
    s=api().cell_summary(rows,'cnn')
    assert s['localization']['tp']==1 and s['localization']['fp']==1 and s['localization']['fn']==1
    assert s['macro_f1']==0
    assert s['target_fraction']['fraction']==.5 and s['predicted_fraction']['fraction']==.5
    assert s['case_ratio_mae_pp']==0 and s['case_ratio_valid']==1
    assert s['matched_only_accuracy']==0


def test_independent_summary_preserves_empty_tumor_denominator():
    rows=[dict(image='a',case_id='case',points=[[2,2]],gt_points=[[2,2]],gt_classes=[0],classes={'cnn':[2]})]
    s=api().cell_summary(rows,'cnn')
    assert s['case_ratio_mae_pp'] is None and s['case_ratio_valid']==0
    assert s['predicted_fraction']['fraction'] is None


def test_sampling_replay_requires_every_fixed_epoch():
    m=api();rng=np.random.default_rng(20261117);p=np.array([.5,.5])
    orders=m.replay_orders(20261117,p,epochs=2,draws=2,batch=8)
    assert orders.shape==(2,2)
    assert orders[0].tolist()==rng.choice(2,size=2,replace=True,p=p).tolist()
    assert np.array_equal(orders,m.replay_orders(20261117,p,epochs=2,draws=2,batch=8))
