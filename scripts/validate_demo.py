"""Static artifact and real-output linkage checks. Not browser interaction QA."""
import json
import re
from pathlib import Path
from PIL import Image

root=Path('dist')
html=(root/'index.html').read_text()
js=(root/'app.js').read_text()
ids=re.findall(r'\bid="([^"]+)"',html)
assert len(ids)==len(set(ids)), 'Duplicate DOM IDs'
for key in re.findall(r"\$\('([^']+)'\)",js):
    assert key in ids, f'Missing DOM target {key}'
data=json.loads((root/'results.json').read_text())
assert len(data['samples'])==7
for sample in data['samples']:
    paths=[sample['image'],sample['gt']]+[m['overlay'] for m in sample['methods'].values()]
    for path in paths:
        p=(root/path).resolve();assert p.is_relative_to(root.resolve())
        assert Image.open(p).size==(sample['width'],sample['height'])
assert '실시간 추론 아님' in html
assert 'WSI 전체 검증 미수행' in html
print('PASS: 7 real samples, 42 images/overlays, DOM targets, source/mode labels. Static-only check; browser evidence is separate.')
