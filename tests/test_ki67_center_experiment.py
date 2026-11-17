import json
import numpy as np
import pytest
from pathology_edge import ki67_center_experiment as e
from pathology_edge.ki67_experiment import sha


def sample(case,points,scores,truth,split='validation'):
    return dict(case_id=case,split=split,points=np.array(points,dtype=int).reshape(-1,2),
                scores=np.array(scores,dtype=float),gt_points=np.array(truth,dtype=int).reshape(-1,2))


def test_selection_uses_validation_and_deterministic_ties():
    s=sample('a',[[2,2],[20,20]],[.4,.15],[[2,2]])
    result=e.select_configuration([s])
    assert result['config']=={'threshold':.3,'min_distance':8}
    assert result['case_macro_f1']==1
    s['split']='test'
    with pytest.raises(ValueError,match='validation'):e.select_configuration([s])
    with pytest.raises(ValueError):e.select_configuration([])


def test_selection_weights_cases_not_image_counts():
    pts=[[0,0]]+[[20+12*i,10] for i in range(9)]
    samples=[sample('large',pts,[.4]+[.2]*9,[[0,0]]) for _ in range(9)]
    samples.append(sample('small',[[0,0]],[.2],[[0,0]]))
    result=e.select_configuration(samples)
    assert result['config']['threshold']==.2
    assert result['case_macro_f1']==pytest.approx((2/11+1)/2)


def test_selection_lock_requires_all_weights_and_protocol(tmp_path):
    for name in ['protocol.json','detector-1.pt','selection.json']:(tmp_path/name).write_text('{}')
    lock=dict(protocol_sha256=sha(tmp_path/'protocol.json'),selection_sha256=sha(tmp_path/'selection.json'),
              model_hashes={'detector-1.pt':sha(tmp_path/'detector-1.pt')})
    (tmp_path/'selection-lock.json').write_text(json.dumps(lock))
    e.verify_selection(tmp_path)
    (tmp_path/'detector-1.pt').write_text('changed')
    with pytest.raises(ValueError,match='hash'):e.verify_selection(tmp_path)


def test_fresh_stage_never_overwrites_existing_outputs(tmp_path):
    e.start_stage(tmp_path,'fit')
    first=(tmp_path/'fit-started.json').read_bytes()
    with pytest.raises(FileExistsError):e.start_stage(tmp_path,'fit')
    assert (tmp_path/'fit-started.json').read_bytes()==first
