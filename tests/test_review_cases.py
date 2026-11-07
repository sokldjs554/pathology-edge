import json
from pathlib import Path
import numpy as np
from PIL import Image
from pathology_edge.review_cases import describe_region, export_cases

ROOT = Path(__file__).resolve().parents[1]


def test_exact_error_changes_and_half_open_region():
    a = np.array([[1, 0, 1, 0], [1, 1, 0, 0]], bool)
    b = np.array([[0, 1, 1, 1], [1, 0, 0, 0]], bool)
    t = np.array([[0, 1, 0, 0], [1, 1, 0, 0]], bool)
    band = np.ones_like(a)
    band[1] = False
    r = describe_region(a, b, t, band, (0, 0, 4, 2))
    assert (r['corrected'], r['regressed'], r['net_corrected']) == (2, 1, 1)
    assert r['corrected_runs'] == [[0, 0, 2]]
    assert r['regressed_runs'] == [[0, 3, 1]]
    assert r['before']['pixels'] == 4
    assert r['before']['dice'] == 0
    assert r['after']['dice'] == 0.5


def test_identical_predictions_have_no_changed_pixels():
    mask = np.ones((8, 8), bool)
    r = describe_region(mask, mask, mask, mask, (2, 2, 6, 6))
    assert r['net_corrected'] == r['changed'] == 0
    assert r['corrected_runs'] == r['regressed_runs'] == []
    assert r['before']['dice'] == r['after']['dice'] == 1


def test_saved_case_evidence_reconstructs_actual_pixels_and_metrics():
    data = export_cases(ROOT / 'dist')
    assert data == json.loads((ROOT / 'dist/cases.json').read_text())
    original = json.loads((ROOT / 'dist/results.json').read_text())
    samples = {s['id']: s for s in original['samples']}
    assert {r['direction'] for r in data['cases']} == {'improved', 'worsened'}
    for case in data['cases']:
        s = samples[case['sample_id']]
        a, b = [np.asarray(Image.open(ROOT / 'dist' / s['methods'][m]['overlay']))[..., 3] > 0
                for m in ('no_overlap', 'overlap')]
        t = np.asarray(Image.open(ROOT / 'dist' / s['gt'])) > 127
        x0, y0, x1, y1 = case['bbox']
        assert x1-x0 == y1-y0 == 64
        assert min(x0, y0) >= 32 and max(x1, y1) <= 480
        yy, xx = np.mgrid[y0:y1, x0:x1]
        band = np.zeros((64, 64), bool)
        for k in (128, 256, 384):
            band |= ((xx >= k-8) & (xx < k+8)) | ((yy >= k-8) & (yy < k+8))
        pa, pb, gt = a[y0:y1, x0:x1], b[y0:y1, x0:x1], t[y0:y1, x0:x1]
        for key, expected in [('corrected', (pa != gt) & (pb == gt) & band),
                              ('regressed', (pa == gt) & (pb != gt) & band)]:
            decoded = np.zeros((64, 64), bool)
            for y, x, length in case[key + '_runs']:
                assert not decoded[y, x:x+length].any()
                decoded[y, x:x+length] = True
            np.testing.assert_array_equal(decoded, expected)
            assert decoded.sum() == case[key]
        for label, prediction in [('before', pa), ('after', pb)]:
            tp = int((prediction & gt & band).sum())
            fp = int((prediction & ~gt & band).sum())
            fn = int((~prediction & gt & band).sum())
            assert case[label]['dice'] == 2*tp/(2*tp+fp+fn)
        sign = 1 if case['direction'] == 'improved' else -1
        assert sign*case['net_corrected'] >= 16
        assert sign*(case['after']['dice']-case['before']['dice']) > 0
    for direction, case_id in data['recommended'].items():
        c = next(c for c in data['cases'] if c['id'] == case_id)
        s = samples[c['sample_id']]
        sign = 1 if direction == 'improved' else -1
        for scope in ('all', 'boundary'):
            assert sign*(s['methods']['overlap']['metrics'][scope]['dice'] -
                         s['methods']['no_overlap']['metrics'][scope]['dice']) > 0
