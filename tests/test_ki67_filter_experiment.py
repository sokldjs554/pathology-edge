import json
import numpy as np
import pytest
from pathology_edge.ki67_filter_experiment import subset_row, verify_selection, predict_gate
from pathology_edge.ki67_experiment import sha


def test_subsetting_preserves_gt_and_all_classifiers_with_consistent_order():
    row=dict(image='a',points=[[1,2],[3,4],[5,6]],gt_points=[[2,2]],gt_classes=[0],
             classes={'lr':[0,1,2],'cnn':[3,2,1]})
    original=json.dumps(row)
    kept=subset_row(row,[0,2])
    assert kept['points']==[[1,2],[5,6]]
    assert kept['classes']=={'lr':[0,2],'cnn':[3,1]}
    assert kept['gt_points']==[[2,2]] and json.dumps(row)==original
    assert subset_row(row,[])['classes']=={'lr':[],'cnn':[]}
    for ids in ([2,0],[0,0],[3],[-1],[True],[1.5]):
        with pytest.raises(ValueError): subset_row(row,ids)


def test_selection_lock_rejects_changed_gate_or_protocol(tmp_path):
    for n in ['protocol.json','gate.json','threshold-selection.json']:
        (tmp_path/n).write_text('{}')
    lock={'hashes':{n:sha(tmp_path/n) for n in ['protocol.json','gate.json','threshold-selection.json']}}
    (tmp_path/'selection-lock.json').write_text(json.dumps(lock))
    verify_selection(tmp_path)
    (tmp_path/'gate.json').write_text('{"changed":true}')
    with pytest.raises(ValueError,match='hash'): verify_selection(tmp_path)


def test_image_only_filter_on_white_image_has_no_candidates():
    model=dict(schema='candidate-correspondence-gate.v1',mean=[0.]*41,scale=[1.]*41,
               coefficients=[0.]*41,intercept=0.)
    result=predict_gate(np.full((32,32,3),255,dtype=np.uint8),model,.5)
    assert result['points'].shape==(0,2) and result['keep_indices']==[]
