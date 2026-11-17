import json
import numpy as np
import pytest
from pathology_edge.ki67_experiment import validate_manifest, select_detector, verify_hashes, fresh_json, summarize


def test_split_leak_and_duplicate_pixels_rejected():
    rows = [{'image':'a', 'case_id':'c1', 'split':'train', 'pixel_sha256':'h1'},
            {'image':'b', 'case_id':'c2', 'split':'test', 'pixel_sha256':'h2'}]
    validate_manifest(rows, {'a':'train', 'b':'test'})
    rows[1]['case_id'] = 'c1'
    with pytest.raises(ValueError, match='case'):
        validate_manifest(rows, {'a':'train', 'b':'test'})
    rows[1]['case_id'], rows[1]['pixel_sha256'] = 'c2', 'h1'
    with pytest.raises(ValueError, match='pixel'):
        validate_manifest(rows, {'a':'train', 'b':'test'})


def test_mismatch_and_path_traversal_rejected():
    with pytest.raises(ValueError):
        validate_manifest([{'image':'../a', 'case_id':'c', 'split':'train', 'pixel_sha256':'h'}], {'../a':'train'})


def test_selection_refuses_test_and_has_fixed_tie_break():
    sample = {'split':'test', 'case_id':'x', 'response':np.zeros((12,12)), 'points':np.empty((0,2))}
    with pytest.raises(ValueError, match='validation'):
        select_detector([sample])
    sample['split'] = 'validation'
    result = select_detector([sample])
    assert len(result['trials']) == 9
    assert result['config'] == {'min_response':.10, 'min_distance':8}


def test_fresh_outputs_and_hash_tampering(tmp_path):
    p = tmp_path/'a.json'
    fresh_json(p, {'a':1})
    with pytest.raises(FileExistsError):
        fresh_json(p, {'a':2})
    assert json.loads(p.read_text()) == {'a':1}
    with pytest.raises(ValueError, match='hash'):
        verify_hashes(tmp_path, {'a.json':'wrong'})


def test_summary_uses_pooled_case_counts_and_reports_coverage():
    rows = [dict(image='a', case_id='c', gt_points=[[1,1]], gt_classes=[0], points=[[1,1]], classes={'lr':[0]}),
            dict(image='b', case_id='c', gt_points=[[1,1]], gt_classes=[1], points=[], classes={'lr':[]}),
            dict(image='c', case_id='d', gt_points=[[1,1]], gt_classes=[0], points=[], classes={'lr':[]})]
    r = summarize(rows, 'lr')
    assert r['localization']['tp'] == 1 and r['localization']['fn'] == 2
    assert r['case_ratio_mae_pp'] == 50
    assert r['case_ratio_valid'] == 1 and r['case_count'] == 2
    assert r['image_ratio_valid'] == 1 and r['image_count'] == 3
