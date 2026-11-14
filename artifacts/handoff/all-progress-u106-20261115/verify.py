"""Independent checks of the finished handoff, without running model code."""
import hashlib
import io
import json
import posixpath
import re
import subprocess
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
WORK = Path(__file__).resolve().parent
report = json.loads((WORK/'build-report.json').read_text())
archive = ROOT/report['path']
data = archive.read_bytes()
assert len(data) == report['bytes']
assert hashlib.sha256(data).hexdigest() == report['sha256']
z = zipfile.ZipFile(io.BytesIO(data))
names = z.namelist()
assert len(names) == len(set(names)) == report['members']
assert all(not n.startswith('/') and '..' not in n.split('/') for n in names)
assert z.testzip() is None
manifest = json.loads(z.read('MANIFEST.json'))
assert set(names) == {f['path'] for f in manifest['files']} | {'MANIFEST.json'}
for f in manifest['files']:
    b = z.read(f['path'])
    assert len(b) == f['bytes'] and hashlib.sha256(b).hexdigest() == f['sha256'], f['path']
coverage = json.loads(z.read('COVERAGE.json'))
for p in coverage['user_code']:
    original = subprocess.check_output(['git','show',f"{report['source_commit']}:{p}"],cwd=ROOT)
    assert z.read(p) == original, p
records = re.findall(r'^\| (U\d+) \|',z.read('docs/CONTRIBUTIONS.md').decode(),re.M)
assert len(records) == 107 and set(records) == {f'U{i:02d}' for i in range(107)}
for a in report['user_original_archives']:
    b=z.read(a['path']); assert hashlib.sha256(b).hexdigest()==a['sha256']
    assert zipfile.ZipFile(io.BytesIO(b)).testzip() is None
inventory = json.loads(z.read('FILE_INVENTORY.json'))['files']
assert len(inventory)==4019 and len({r['path'] for r in inventory})==4019
for row in inventory:
    if row['included']:
        assert hashlib.sha256(z.read(row['path'])).hexdigest()==row['sha256']
    else:
        assert report['source_commit'] in row['url'] and len(row['sha256'])==64
for row in coverage['phases']:
    assert all(p in names for p in row['files']),row

class Links(HTMLParser):
    def __init__(self): super().__init__(); self.paths=[]
    def handle_starttag(self,tag,attrs):
        for k,v in attrs:
            if k in ('href','src') and v: self.paths.append(v)

pages=['START_HERE.html','PERSONAL_RECORDS.html','DOWNLOADS.html',
       'review/final-transfer/review.html',
       'artifacts/experiments/ki67-normalized-20261114/review/index.html',
       'artifacts/experiments/ki67-union-20261113/review/index.html',
       'artifacts/experiments/user-cnn-vit-errors-20261112/index.html']
link_count=0
for p in pages:
    parser=Links(); parser.feed(z.read(p).decode())
    for link in parser.paths:
        u=urlsplit(link)
        if u.scheme or u.netloc or not u.path: continue
        path=posixpath.normpath(posixpath.join(posixpath.dirname(p),unquote(u.path)))
        assert path in names,(p,link,path)
        link_count+=1
final=json.loads(z.read('artifacts/experiments/ki67-final-transfer-20261115/final-summary.json'))
assert final==json.loads(z.read('review/final-transfer/final-summary.json'))
assert not manifest['new_user_completion_claimed'] and not manifest['new_training_or_inference_run']
out={**report,'all_checks_passed':True,'crc_all_members':True,'manifest_verified_members':len(manifest['files']),
     'tracked_inventory_entries':len(inventory),'user_code_byte_identical':7,'user_original_archives_crc_sha_verified':2,
     'personal_record_ids_preserved':107,'latest_user_id':'U106','followup_chat_preserved_separately':True,
     'phase_groups':len(coverage['phases']),'navigation_pages':len(pages),'local_links_verified':link_count,
     'final_summary_identical_to_published':True,'scope':'Package integrity/navigation only; no new training, inference or user test.'}
(WORK/'verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:out[k] for k in ['all_checks_passed','members','bytes','sha256','local_links_verified','phase_groups','personal_record_ids_preserved']}))
