from pathlib import Path
import json, hashlib, zipfile, xml.etree.ElementTree as ET
import numpy as np
from PIL import Image
import cv2
out = Path('/workspace/pathology-edge-loss/work/external-monuseg-locked-20261111')
repo = out.parents[1]
p = json.loads((out/'protocol.json').read_text())
r = json.loads((out/'results.json').read_text())
sha = lambda b: hashlib.sha256(b).hexdigest()
file_sha = lambda f: sha(Path(f).read_bytes())
assert file_sha(out/'protocol.json') == r['protocol_sha256']
assert len(p['images']) == len(r['rows']) == 14
assert len({i['id'] for i in p['images']}) == len({i['id'] for i in r['rows']}) == 14
assert {i['id'] for i in p['images']} == {i['id'] for i in r['rows']}
canonical = json.loads((repo/'artifacts/experiments/user-vit-refinement-20261112/re-audited-summary.json').read_text())
expected = {x['architecture']: x['model_sha256'] for x in canonical['rows']}
assert p['models'] == expected
for name, expected_sha in expected.items():
    assert file_sha(out/'models'/f'{name}.pt') == expected_sha
    tr = json.loads((out/'models'/f'{name}-training.json').read_text())
    assert tr['threshold'] == p['threshold'] == .35
    assert tr['config']['seed'] == p['seed'] == 20261116
assert file_sha(out/'runner.py') == p['runner_sha256']
for name, digest in p['source_sha256'].items():
    assert file_sha(out/'source/pathology_edge'/name) == digest
for name, digest in r['files'].items():
    assert file_sha(out/name) == digest
archive = Path(p['images'][0]['image']).parent.parent/'MoNuSegTestData.zip'
assert file_sha(archive) == p['archive_sha256']
xml_region_count = region_checks = archive_checks = target_checks = 0
images = {x['id']: x for x in p['images']}
metric_rows = {a: {region: [] for region in ('all','boundary','interior')} for a in expected}
with zipfile.ZipFile(archive) as z:
    members = {Path(n).name:n for n in z.namelist() if n.lower().endswith(('.tif','.xml'))}
    assert len(members) == 28
    for row in r['rows']:
        item = images[row['id']]
        for key in ('image','xml'):
            f = Path(item[key]); b = f.read_bytes()
            assert sha(b) == item[f'{key}_sha256'] == sha(z.read(members[f.name]))
            archive_checks += 1
        im = np.asarray(Image.open(item['image']).convert('RGB'))
        assert im.shape == (1000,1000,3) and sha(im.tobytes()) == item['rgb_sha256']
        target = np.zeros((1000,1000),np.uint8)
        regions = ET.parse(item['xml']).getroot().findall('.//Region')
        assert len(regions) == row['annotation_regions']
        for region in regions:
            assert region.get('NegativeROA','0') == '0'
            xy = np.array([[float(v.attrib['X']),float(v.attrib['Y'])] for v in region.findall('./Vertices/Vertex')])
            assert xy.shape[0] >= 3 and np.isfinite(xy).all()
            cv2.fillPoly(target,[np.rint(xy).astype(np.int32)],1)
        xml_region_count += len(regions)
        stored = np.asarray(Image.open(out/row['target']))
        assert set(np.unique(stored)).issubset({0,255})
        assert np.array_equal(stored>0,target>0)
        target_checks += 1
        target = target.astype(bool)
        band = np.zeros(target.shape,bool)
        for seam in range(128,1000,128):
            band[:,seam-8:seam+8] = True
            band[seam-8:seam+8,:] = True
        for a in expected:
            saved = row['models'][a]
            with np.load(out/saved['probability'],allow_pickle=False) as npz:
                assert set(npz.files) == {'probability'}
                prob = npz['probability']
            assert prob.shape == target.shape and np.isfinite(prob).all()
            assert ((prob>=0)&(prob<=1)).all()
            pred = prob >= .35
            for name,selection in [('all',np.ones_like(band)),('boundary',band),('interior',~band)]:
                y = target[selection]; x = pred[selection]
                tp = int(np.count_nonzero(x&y)); fp = int(np.count_nonzero(x&~y)); fn = int(np.count_nonzero(~x&y))
                actual = dict(tp=tp,fp=fp,fn=fn,pixels=int(selection.sum()),
                    dice=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 1.,
                    iou=tp/(tp+fp+fn) if tp+fp+fn else 1.,
                    precision=tp/(tp+fp) if tp+fp else 0.,recall=tp/(tp+fn) if tp+fn else 0.)
                assert actual == saved['metrics'][name],(row['id'],a,name)
                metric_rows[a][name].append(actual['dice'])
                region_checks += 1
means = {a: {region:float(np.mean(vals)) for region,vals in arms.items()} for a,arms in metric_rows.items()}
assert means == r['means']
counts = {}
for region in ('all','boundary','interior'):
    deltas = np.asarray(metric_rows['small_vit_refined'][region]) - metric_rows['small_vit'][region]
    counts[region] = [int((deltas>0).sum()),int((deltas==0).sum()),int((deltas<0).sum())]
    assert counts[region] == r['wins_ties_losses'][region]
    assert means['small_vit_refined'][region]-means['small_vit'][region] == r['delta_refined_minus_baseline'][region]
tnbc = json.loads((repo/'work/external-data-research/tnbc-rgb-hashes.json').read_text())
tnbc_shas = set()
for entry in tnbc:
    im = np.asarray(Image.open(entry['path']).convert('RGB')); d = sha(im.tobytes())
    assert list(im.shape) == entry['shape'] and d == entry['decoded_rgb_sha256']
    tnbc_shas.add(d)
assert not tnbc_shas & {i['rgb_sha256'] for i in p['images']}
print(json.dumps(dict(success=True,checkpoint_hashes_match_user=True,
    source_files=len(p['source_sha256']),report_file_hash_checks=len(r['files']),
    archive_payload_checks=archive_checks,rerasterized_masks=target_checks,
    annotation_regions=xml_region_count,independent_region_checks=region_checks,mean_checks=6,
    means=means,wins_ties_losses=counts,tnbc_images_redecoded=len(tnbc),
    exact_decoded_duplicates=0,inference=False,training=False),indent=2))
