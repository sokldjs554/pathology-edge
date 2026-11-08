"""WSI geometry/provenance checks; no OpenSlide installation or download required."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from pathology_edge.merge import deduplicate
from pathology_edge.wsi_export import (
    difference_rgba, patch_manifest, select_boundary_case, suppression_trace,
)


def test_patch_manifest_translates_native_origin_and_clips_trailing_padding():
    # A padded 128px patch must never claim a larger valid WSI footprint.
    patches = patch_manifest(150, 130, (1000, 2000), 'no_overlap')
    assert len(patches) == 4
    assert patches[-1]['id'] == 3
    assert patches[-1]['origin_local'] == [128, 128]
    assert patches[-1]['origin_level0'] == [1128, 2128]
    assert patches[-1]['bbox_level0'] == [1128, 2128, 1150, 2130]
    assert patches[-1]['valid_size'] == [22, 2]
    overlap = patch_manifest(150, 130, (1000, 2000), 'overlap')
    assert len(overlap) == 9
    assert overlap[1]['origin_local'] == [64, 0]
    with pytest.raises(ValueError, match='mode'):
        patch_manifest(150, 130, (1000, 2000), 'arbitrary')


def candidate(x, patch, edge=False, score=.8, width=10):
    return dict(x=float(x), y=5., bbox=[x-width/2, 0, x+width/2, 10],
                patch_id=patch, touches_edge=edge, score=score, area=50)


def test_nms_trace_explains_actual_complete_component_priority_and_both_triggers():
    raw = [candidate(5, 0, True, .99), candidate(7, 1, False, .8), candidate(40, 2)]
    kept, removed = deduplicate(raw)
    trace = suppression_trace(raw, removed)
    assert [o['raw_index'] for o in kept] == [1, 2]
    assert len(trace) == 1
    record = trace[0]
    assert (record['suppressed_index'], record['kept_index']) == (0, 1)
    assert record['box_iou'] == pytest.approx(2/3)
    assert record['center_distance'] == 2
    assert record['iou_trigger'] and record['distance_trigger']
    assert record['touches_edge_priority']
    assert record['suppressed_patch_id'] == 0 and record['kept_patch_id'] == 1


def test_nms_trace_distinguishes_distance_only_suppression_and_rejects_false_trace():
    raw = [candidate(1, 0, width=2), candidate(5, 1, width=2)]
    _, removed = deduplicate(raw)
    record = suppression_trace(raw, removed)[0]
    assert record['box_iou'] == 0 and record['center_distance'] == 4
    assert record['distance_trigger'] and not record['iou_trigger']
    assert not record['touches_edge_priority']
    with pytest.raises(ValueError, match='suppression'):
        suppression_trace([candidate(1, 0), candidate(100, 1)],
                          [{'suppressed_index': 1, 'kept_index': 0}])


def test_difference_overlay_encodes_a_only_blue_and_b_only_orange_without_agreement():
    a = np.array([[1, 0, 1], [0, 0, 0]], dtype=bool)
    b = np.array([[0, 1, 1], [0, 0, 0]], dtype=bool)
    rgba = difference_rgba(a, b)
    np.testing.assert_array_equal(rgba[0, 0], [59, 130, 246, 180])
    np.testing.assert_array_equal(rgba[0, 1], [249, 115, 22, 180])
    assert np.count_nonzero(rgba[..., 3]) == 2
    assert not rgba[0, 2].any()
    with pytest.raises(ValueError, match='shape'):
        difference_rgba(a, b[:, :2])


def test_boundary_case_selection_is_deterministic_and_translates_native_bbox():
    a = np.zeros((256, 256), bool)
    b = a.copy()
    b[64:72, 124:132] = True  # a centered window must include both sides of x=128
    cases = select_boundary_case(a, b, (1000, 2000), 'R-test')
    assert len(cases) == 1
    case = cases[0]
    assert case['bbox_local'] == [96, 16, 160, 80]
    assert case['bbox_level0'] == [1096, 2016, 1160, 2080]
    assert case['center_level0'] == [1128, 2048]
    assert case['added_pixels'] == case['changed_pixels'] == case['boundary_changed_pixels'] == 64
    assert case['removed_pixels'] == 0
    assert select_boundary_case(a, a, (1000, 2000), 'empty') == []
    b[:] = False
    b[30:50, 30:50] = True  # changes only away from every internal seam
    assert select_boundary_case(a, b, (1000, 2000), 'interior-only') == []


def file_sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_exported_wsi_pixels_hashes_nms_and_difference_cases_match_real_outputs():
    root = Path(__file__).resolve().parents[1]
    payload_file = root/'dist/wsi.json'
    if not payload_file.exists():
        pytest.skip('Optional checked-in real WSI export has not been generated')
    data = json.loads(payload_file.read_text())
    assert data['analysis']['ground_truth'] is False
    assert data['analysis']['total_pixels'] == 3*1024*1024
    assert data['model']['sha256'] == file_sha(root/'artifacts/model.pt')
    assert data['slide']['source_sha256'] == json.loads((root/'artifacts/wsi/source.json').read_text())['source_sha256']
    worker_pids = []
    for roi in data['rois']:
        image_path = root/'dist'/roi['image']
        image = np.asarray(Image.open(image_path))
        assert image.shape == (1024, 1024, 3)
        assert file_sha(image_path) == roi['image_sha256']
        thumb_path = root/'dist'/roi['thumbnail']
        assert Image.open(thumb_path).size == (160, 160)
        assert file_sha(thumb_path) == roi['thumbnail_sha256']
        assert hashlib.sha256(image.tobytes()).hexdigest() == roi['image_pixel_sha256']
        masks = {}
        for name, method in roi['methods'].items():
            worker_pids.append(method['worker_pid'])
            assert len(method['timings_seconds']) == 3 and all(t > 0 for t in method['timings_seconds'])
            assert method['median_seconds'] == float(np.median(method['timings_seconds']))
            assert method['torch_threads'] == 4 and method['opencv_threads'] == 1
            assert method['read_seconds'] > 0 and method['peak_process_rss_mib'] > 0
            assert 'metrics' not in method
            for field in ['mask', 'overlay']:
                assert file_sha(root/'dist'/method[field]) == method[f'{field}_sha256']
            mask = np.asarray(Image.open(root/'dist'/method['mask'])) > 0
            masks[name] = mask
            overlay = np.asarray(Image.open(root/'dist'/method['overlay']))
            np.testing.assert_array_equal(overlay[..., 3] > 0, mask)
            assert method['repeat_probability_sha256'].count(method['repeat_probability_sha256'][0]) == 3
            assert method['image_pixel_sha256'] == roi['image_pixel_sha256']
            assert len(method['patches']) == method['patch_count']
            assert len(method['raw']) == method['raw_count']
            assert len(method['objects']) == method['merged_count']
            assert len(method['suppressed']) == method['suppressed_count']
            for raw_index, obj in enumerate(method['raw']):
                assert obj['raw_index'] == raw_index
                patch = method['patches'][obj['patch_id']]
                assert obj['bbox_level0'] == [obj['bbox'][i]+roi['origin'][i % 2] for i in range(4)]
                assert obj['center_level0'] == [obj['x']+roi['origin'][0], obj['y']+roi['origin'][1]]
                assert patch['bbox_local'][0] <= obj['bbox'][0] < obj['bbox'][2] <= patch['bbox_local'][2]
                assert patch['bbox_local'][1] <= obj['bbox'][1] < obj['bbox'][3] <= patch['bbox_local'][3]
            if name == 'overlap':
                expected_kept, expected_removed = deduplicate(method['raw'])
                assert [o['raw_index'] for o in expected_kept] == [o['raw_index'] for o in method['objects']]
                assert [(r['suppressed_index'], r['kept_index']) for r in expected_removed] == [(r['suppressed_index'], r['kept_index']) for r in method['suppressed']]
                assert suppression_trace(method['raw'], expected_removed) == method['suppressed']
            else:
                assert not method['suppressed']
        a, b = masks['no_overlap'], masks['overlap']
        difference = roi['difference']
        assert difference['added_pixels'] == int((b & ~a).sum())
        assert difference['removed_pixels'] == int((a & ~b).sum())
        assert file_sha(root/'dist'/difference['overlay']) == difference['overlay_sha256']
        np.testing.assert_array_equal(np.asarray(Image.open(root/'dist'/difference['overlay'])), difference_rgba(a, b))
        assert select_boundary_case(a, b, roi['origin'], roi['id']) == difference['cases']
        for case in difference['cases']:
            x0, y0, x1, y1 = case['bbox_local']
            assert x1-x0 == y1-y0 == 64
            assert ((x0+x1)//2) % 128 == 0 or ((y0+y1)//2) % 128 == 0
    assert len(set(worker_pids)) == 6


def test_refresh_cases_uses_saved_masks_without_inference_and_minifies_public_json(tmp_path):
    import os
    import subprocess
    import sys

    dest, artifacts = tmp_path/'dist', tmp_path/'artifacts'
    (dest/'wsi').mkdir(parents=True)
    artifacts.mkdir()
    a = np.zeros((256, 256), np.uint8)
    b = a.copy()
    b[64:72, 124:132] = 255
    methods = {}
    for name, mask in [('no_overlap', a), ('overlap', b)]:
        relative = f'wsi/R1-{name}-mask.png'
        Image.fromarray(mask).save(dest/relative)
        methods[name] = dict(mask=relative, mask_sha256=file_sha(dest/relative),
                             timings_seconds=[.3, .4, .5], warmup_seconds=.8,
                             worker_pid=123, raw=[{'raw_index': 5}], suppressed=[])
    protocol = dict(case_selection='previous edge-aligned rule', ground_truth=False)
    payload = dict(schema_version=1, slide={'source_sha256': 'pinned-source'},
                   model={'sha256': 'pinned-model'}, analysis={'ground_truth': False},
                   provenance={'pipeline_sha256': 'original-inference-code'},
                   rois=[dict(id='R1', origin=[1000, 2000], width=256, height=256,
                              methods=methods, difference=dict(added_pixels=64, removed_pixels=0,
                                                               overlay='unchanged.png', cases=[]))])
    (dest/'wsi.json').write_text(json.dumps(payload, indent=2))
    (artifacts/'protocol.json').write_text(json.dumps(protocol))
    (dest/'wsi/provenance.json').write_text(json.dumps(dict(slide=payload['slide'],
        protocol=protocol, provenance=payload['provenance'], roi_images=[])))
    root = Path(__file__).resolve().parents[1]
    command = [sys.executable, '-m', 'pathology_edge.wsi_export', '--refresh-cases',
               '--output-dist', str(dest), '--artifacts', str(artifacts)]
    process = subprocess.run(command, capture_output=True, text=True,
                             env=dict(os.environ, PYTHONPATH=str(root/'src')))
    assert process.returncode == 0, process.stderr
    updated = json.loads((dest/'wsi.json').read_text())
    assert updated['rois'][0]['methods'] == methods  # measured inference is immutable
    assert updated['model'] == payload['model'] and updated['slide'] == payload['slide']
    assert updated['rois'][0]['difference']['cases'][0]['bbox_local'] == [96, 16, 160, 80]
    assert updated['rois'][0]['difference']['added_pixels'] == 64
    assert updated['provenance']['inference_pipeline_sha256'] == 'original-inference-code'
    assert updated['provenance']['case_selection_pipeline_sha256'] == file_sha(root/'src/pathology_edge/wsi_export.py')
    assert len((dest/'wsi.json').read_text().splitlines()) == 1
    assert json.loads((artifacts/'experiment.json').read_text()) == updated
    assert json.loads((artifacts/'protocol.json').read_text())['case_selection_revision'] == 2

    # A changed input mask must be rejected before any previously published JSON changes.
    before = (dest/'wsi.json').read_bytes()
    Image.fromarray(a).save(dest/methods['overlap']['mask'])
    rejected = subprocess.run(command, capture_output=True, text=True,
                              env=dict(os.environ, PYTHONPATH=str(root/'src')))
    assert rejected.returncode != 0 and 'mask SHA-256' in rejected.stderr
    assert (dest/'wsi.json').read_bytes() == before


def test_local_dzi_keeps_native_edge_pixels_and_every_level(tmp_path):
    # Optional library fixture, never an external WSI download. Catches dropping
    # the last 6px column, overlap off-by-one, missing levels, and wrong public URL.
    openslide = pytest.importorskip('openslide')
    import importlib.util
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location('local_dzi_export', root/'scripts/export_wsi_tiles.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    yy, xx = np.mgrid[:1030, :2050]
    rgb = np.stack([xx % 256, yy % 256, (xx+yy) % 256], axis=-1).astype(np.uint8)
    with openslide.ImageSlide(Image.fromarray(rgb)) as slide:
        report = module.generate_pyramid(slide, tmp_path/'tiles', tile_size=1022,
                                         overlap=1, quality=75, workers=2)
    assert report['native_dimensions'] == [2050, 1030]
    assert report['max_level'] == 12
    assert report['level_count'] == 13
    assert report['level_tiles'][-1] == [3, 2]
    assert report['all_tile_dimensions_verified']
    assert Image.open(tmp_path/'tiles/12/2_1.jpeg').size == (7, 9)
    assert (tmp_path/'tiles/0/0_0.jpeg').exists()
    assert len(list((tmp_path/'tiles').rglob('*.jpeg'))) == report['tile_count']
    assert report['total_bytes'] == sum(p.stat().st_size for p in (tmp_path/'tiles').rglob('*.jpeg'))
    # Stitch the native tile interiors across the x=1022 seam, discarding overlap.
    decoded = module.read_native_patch(tmp_path/'tiles', 12, 1022, 1, 1000, 300, 64, 64)
    assert decoded.shape == (64, 64, 3)
    error = np.abs(decoded.astype(float)-rgb[300:364, 1000:1064].astype(float)).mean()
    assert error < 5  # allows JPEG loss; never claims pixel equality


def test_local_dzi_corrects_thumbnail_rounding_without_resizing_native(tmp_path):
    openslide = pytest.importorskip('openslide')
    import importlib.util
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location('rounded_dzi_export',root/'scripts/export_wsi_tiles.py')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with openslide.ImageSlide(Image.new('RGB',(46,33),(100,40,150))) as slide:
        report=module.generate_pyramid(slide,tmp_path/'tiles',workers=1)
    assert Image.open(tmp_path/'tiles/2/0_0.jpeg').size == (3,3)
    assert Image.open(tmp_path/'tiles/6/0_0.jpeg').size == (46,33)
    assert report['native_tiles_resized'] == 0
    correction=next(r for r in report['lower_level_geometry_adjustments'] if r['path']=='2/0_0.jpeg')
    assert correction['before']==[3,2] and correction['after']==[3,3]
    assert all(r['level']<report['max_level'] for r in report['lower_level_geometry_adjustments'])
