import importlib.util
import json
from pathlib import Path
import pytest
from pathology_edge.ki67_experiment import sha

SPEC=importlib.util.spec_from_file_location('recall_runner',Path(__file__).parents[1]/'scripts/run_ki67_recall.py')
r=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(r)


def test_localization_floors_use_reference_class_not_prediction_class():
    rows=[dict(case_id='a',points=[[0,0],[20,0]],gt_points=[[0,0],[20,0],[40,0]],gt_classes=[0,1,1]),
          dict(case_id='b',points=[],gt_points=[[0,0]],gt_classes=[0])]
    v=r.localization_summary(rows)
    assert v['tumor_recalls']==[.5,.5]
    assert v['case_macro_recall']==pytest.approx(1/3)
    assert v['localization']['recall']==.5


def test_compressed_evidence_is_fresh_and_round_trips(tmp_path):
    path=tmp_path/'rows.json.gz';r.write_rows(path,[dict(x=1)])
    before=path.read_bytes()
    with pytest.raises(FileExistsError):r.write_rows(path,[])
    assert path.read_bytes()==before and r.read_rows(path)==[dict(x=1)]


@pytest.mark.parametrize('changed',['protocol','source','input','selection','evidence'])
def test_locked_runner_rejects_changed_evidence_before_inference(tmp_path,changed):
    source=tmp_path/'source.py';source.write_text('original')
    inp=tmp_path/'input.json';inp.write_text('{}')
    p=dict(input_hashes={str(inp):sha(inp)},source_hashes={str(source):sha(source)},seeds=list(r.SEEDS),thresholds=list(r.THRESHOLDS),distances=list(r.DISTANCES))
    (tmp_path/'protocol.json').write_text(json.dumps(p))
    (tmp_path/'selection.json').write_text('{}')
    (tmp_path/'evidence.json').write_text('{}')
    lock=dict(protocol_sha256=sha(tmp_path/'protocol.json'),selection_sha256=sha(tmp_path/'selection.json'),evidence_hashes={'evidence.json':sha(tmp_path/'evidence.json')})
    (tmp_path/'selection-lock.json').write_text(json.dumps(lock))
    assert r.checked(tmp_path,selected=True)==p
    path={'protocol':tmp_path/'protocol.json','source':source,'input':inp,'selection':tmp_path/'selection.json','evidence':tmp_path/'evidence.json'}[changed]
    path.write_text(path.read_text()+' ')
    with pytest.raises(ValueError):r.checked(tmp_path,selected=True)
