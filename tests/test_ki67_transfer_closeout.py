import importlib
import json
from pathlib import Path
import pytest


def setup(tmp_path,monkeypatch):
    m=importlib.import_module('pathology_edge.ki67_transfer_evaluation')
    monkeypatch.setattr(m,'evaluation_lock',lambda root:{})
    (tmp_path/'evaluation-lock.json').write_text('{}');hashes={}
    for split in ('validation','test','bcdata','deepliif'):
        folder=tmp_path/'evaluation'/split;folder.mkdir(parents=True)
        (folder/'scores.json').write_text('{"f1":0.4}')
        (folder/'summary.json').write_text(json.dumps({'all_checks_passed':True,'passes':0,'evidence_hashes':{'scores.json':m.sha(folder/'scores.json')}}))
        hashes[split]=m.sha(folder/'summary.json')
    ref=tmp_path/'external-input-review';ref.mkdir();(ref/'view.png').write_bytes(b'original pixels')
    (ref/'summary.json').write_text(json.dumps({'all_checks_passed':True,'evidence_hashes':{'view.png':m.sha(ref/'view.png')}}))
    audit=dict(all_checks_passed=True,evaluation_lock_sha256=m.sha(tmp_path/'evaluation-lock.json'),stage_summary_hashes=hashes,reference_review_summary_sha256=m.sha(ref/'summary.json'))
    (tmp_path/'audit.json').write_text(json.dumps(audit))
    return m


@pytest.mark.parametrize('fault',['score','summary','lock','missing_audit','missing_stage','asset'])
def test_closeout_rejects_post_audit_mutation(tmp_path,monkeypatch,fault):
    m=setup(tmp_path,monkeypatch)
    assert m.validate_audited(tmp_path)['all_checks_passed']
    if fault=='score':(tmp_path/'evaluation/test/scores.json').write_text('{"f1":1}')
    if fault=='summary':(tmp_path/'evaluation/test/summary.json').write_text('{"all_checks_passed":true,"passes":3,"evidence_hashes":{}}')
    if fault=='lock':(tmp_path/'evaluation-lock.json').write_text('{"changed":true}')
    if fault=='missing_audit':(tmp_path/'audit.json').unlink()
    if fault=='missing_stage':(tmp_path/'evaluation/test/summary.json').unlink()
    if fault=='asset':(tmp_path/'external-input-review/view.png').write_bytes(b'changed pixels')
    with pytest.raises((ValueError,FileNotFoundError)):m.validate_audited(tmp_path)
