import numpy as np
import pytest
import importlib.util
from pathlib import Path
import json
import zipfile


def runner():
    spec = importlib.util.spec_from_file_location('external_runner', Path(__file__).parents[1] / 'scripts/run_external_monuseg.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_aperio_union_preserves_xy_and_rejects_holes(tmp_path):
    from pathology_edge.external_validation import rasterize_xml
    xml = tmp_path / 'nuclei.xml'
    xml.write_text('<Annotations><Annotation><Regions><Region NegativeROA="0"><Vertices>'
                   '<Vertex X="3" Y="1"/><Vertex X="5" Y="1"/>'
                   '<Vertex X="5" Y="2"/><Vertex X="3" Y="2"/>'
                   '</Vertices></Region></Regions></Annotation></Annotations>')
    mask, count = rasterize_xml(xml, (4, 8))
    expected = np.zeros((4, 8), bool)
    expected[1:3, 3:6] = True
    np.testing.assert_array_equal(mask, expected)
    assert count == 1
    xml.write_text(xml.read_text().replace('NegativeROA="0"', 'NegativeROA="1"'))
    with pytest.raises(ValueError, match='negative'):
        rasterize_xml(xml, (4, 8))


@pytest.mark.parametrize('coordinate', ['nan', 'inf', '1e100'])
def test_xml_rejects_nonfinite_and_overflow_coordinates(tmp_path, coordinate):
    from pathology_edge.external_validation import rasterize_xml
    xml = tmp_path / 'nuclei.xml'
    xml.write_text(f'<Annotations><Annotation><Regions><Region><Vertices>'
                   f'<Vertex X="{coordinate}" Y="1"/><Vertex X="5" Y="1"/>'
                   '<Vertex X="5" Y="2"/></Vertices></Region></Regions>'
                   '</Annotation></Annotations>')
    with pytest.raises(ValueError, match='coordinate'):
        rasterize_xml(xml, (4, 8))


def test_partly_outside_annotation_is_clipped_by_canvas(tmp_path):
    from pathology_edge.external_validation import rasterize_xml
    xml = tmp_path / 'edge.xml'
    xml.write_text('<Annotations><Region><Vertices>'
                   '<Vertex X="-1" Y="1"/><Vertex X="2" Y="1"/>'
                   '<Vertex X="2" Y="5"/><Vertex X="-1" Y="5"/>'
                   '</Vertices></Region></Annotations>')
    mask, count = rasterize_xml(xml, (4, 8))
    expected = np.zeros((4, 8), bool)
    expected[1:, :3] = True
    np.testing.assert_array_equal(mask, expected)
    assert count == 1


def test_external_scores_partition_pixels_and_use_locked_threshold():
    from pathology_edge.external_validation import score_probability
    target = np.zeros((256, 256), bool)
    target[120:136, 124:132] = True
    probability = np.where(target, .4, .1).astype(np.float32)
    result = score_probability(probability, target, .35)
    assert result['all']['dice'] == 1.0
    assert result['boundary']['tp'] == target.sum()
    assert result['interior']['tp'] == 0
    assert result['all']['pixels'] == result['boundary']['pixels'] + result['interior']['pixels']
    assert score_probability(probability, target, .5)['all']['dice'] == 0.0
    probability[0, 0] = np.nan
    with pytest.raises(ValueError, match='probability'):
        score_probability(probability, target, .35)


def test_extracted_payload_must_match_archive(tmp_path):
    module = runner()
    data = tmp_path / 'MoNuSegTestData'
    data.mkdir()
    (data / 'sample.tif').write_bytes(b'original image')
    (data / 'sample.xml').write_bytes(b'original annotation')
    archive = tmp_path / 'test.zip'
    with zipfile.ZipFile(archive, 'w') as z:
        for p in data.iterdir():
            z.write(p, f'MoNuSegTestData/{p.name}')
    module.verify_payloads(data, archive)
    (data / 'sample.xml').write_bytes(b'changed annotation')
    with pytest.raises(ValueError, match='archive payload'):
        module.verify_payloads(data, archive)


def external_fixture(tmp_path):
    from PIL import Image
    from pathology_edge.external_validation import score_probability
    module = runner()
    (tmp_path/'models').mkdir()
    (tmp_path/'source/pathology_edge').mkdir(parents=True)
    for a in module.EXPECTED_MODELS:
        (tmp_path/'models'/f'{a}.pt').write_bytes(a.encode())
    # A small synthetic fixed model identity; no checkpoint is deserialized.
    module.EXPECTED_MODELS = {a:module.digest(tmp_path/'models'/f'{a}.pt') for a in module.EXPECTED_MODELS}
    (tmp_path/'source/pathology_edge/model.py').write_text('frozen synthetic source')
    (tmp_path/'runner.py').write_text('frozen synthetic runner')
    protocol = {'images': [{'id': str(i), 'case_id': str(i)} for i in range(14)],
                'threshold': .35, 'models': module.EXPECTED_MODELS, 'image_count': 14, 'case_count': 14,
                'source_sha256': {'model.py': module.digest(tmp_path/'source/pathology_edge/model.py')},
                'runner_sha256': module.digest(tmp_path/'runner.py')}
    module.save(tmp_path/'protocol.json', protocol)
    module.save(tmp_path/'status.json', {'completed':True, 'returncode':0})
    target = np.zeros((256, 256), bool)
    target[10:20, 10:20] = True
    Image.fromarray(target.astype(np.uint8)*255).save(tmp_path/'target.png')
    probability = target.astype(np.float32)
    np.savez_compressed(tmp_path/'prediction.npz', probability=probability)
    metrics = score_probability(probability, target, .35)
    rows = [{'id': str(i), 'case_id': str(i), 'target': 'target.png',
             'models': {a: {'probability': 'prediction.npz', 'metrics': metrics}
                        for a in module.EXPECTED_MODELS}} for i in range(14)]
    assets = ['target.png','prediction.npz','source/pathology_edge/model.py'] + [f'models/{a}.pt' for a in module.EXPECTED_MODELS]
    report = {'rows': rows, 'protocol_sha256': module.digest(tmp_path/'protocol.json'),
              'files': {n:module.digest(tmp_path/n) for n in assets},
              'means': {a: {r: 1.0 for r in ('all','boundary','interior')} for a in module.EXPECTED_MODELS},
              'delta_refined_minus_baseline': {r: 0.0 for r in ('all','boundary','interior')},
              'wins_ties_losses': {r: [0,14,0] for r in ('all','boundary','interior')}}
    module.save(tmp_path/'results.json', report)
    return module, report


@pytest.mark.parametrize('damage', ['missing_image', 'duplicate_image', 'wrong_delta', 'wrong_wins'])
def test_audit_rejects_incomplete_or_misaggregated_external_results(tmp_path, damage):
    module, report = external_fixture(tmp_path)
    if damage == 'missing_image': report['rows'].pop()
    if damage == 'duplicate_image': report['rows'][-1] = report['rows'][0]
    if damage == 'wrong_delta': report['delta_refined_minus_baseline']['all'] = 123
    if damage == 'wrong_wins': report['wins_ties_losses']['all'] = [14,0,0]
    module.save(tmp_path/'results.json', report)
    with pytest.raises(ValueError, match='image|aggregate'):
        module.audit(tmp_path)


def test_complete_external_evidence_audits_without_model_execution(tmp_path):
    module, _ = external_fixture(tmp_path)
    assert module.audit(tmp_path)['region_checks'] == 84


@pytest.mark.parametrize('damage', ['failed_status','omitted_target','unlisted_altered_model','altered_source','altered_runner'])
def test_audit_rejects_incomplete_provenance(tmp_path, damage):
    module, report = external_fixture(tmp_path)
    if damage == 'failed_status': module.save(tmp_path/'status.json', {'completed':False,'returncode':1})
    if damage == 'omitted_target': report['files'].pop('target.png')
    if damage == 'unlisted_altered_model':
        report['files'].pop('models/small_vit.pt')
        (tmp_path/'models/small_vit.pt').write_bytes(b'other checkpoint')
    if damage == 'altered_source':
        name = 'source/pathology_edge/model.py'
        (tmp_path/name).write_text('altered')
        report['files'][name] = module.digest(tmp_path/name)
    if damage == 'altered_runner': (tmp_path/'runner.py').write_text('altered')
    module.save(tmp_path/'results.json', report)
    with pytest.raises(ValueError):
        module.audit(tmp_path)
