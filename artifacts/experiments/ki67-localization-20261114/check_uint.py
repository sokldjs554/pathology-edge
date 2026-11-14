import gzip,importlib.util,json,hashlib
from pathlib import Path
import numpy as np
from pathology_edge.ki67_union import retain_candidates
root=Path('artifacts/experiments/ki67-union-20261113');path=root/'frozen_source/pathology_edge/ki67_union.py'
spec=importlib.util.spec_from_file_location('pathology_edge._historical_union',path);old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
checked=0
for m in json.loads((root/'selection.json').read_text())['models']:
 rows=json.load(gzip.open(root/f"validation-{m['seed']}.json.gz",'rt'));scores=np.load(root/f"validation-scores-{m['seed']}.npz")[f"epoch_{m['diagnostic']['epoch']}"] .astype(np.float64);offset=0
 for row in rows:
  xy=np.array(row['points']).reshape(-1,2);v=scores[offset:offset+len(xy)];offset+=len(xy)
  before=old.retain_candidates(xy,v,**m['diagnostic']['config']);after=retain_candidates(xy,v,**m['diagnostic']['config'])
  assert all(np.array_equal(before[k],after[k]) for k in ('points_xy','scores','indices'));checked+=1
manifest=json.loads((root/'SHA256SUMS.json').read_text());assert all(hashlib.sha256((root/n).read_bytes()).hexdigest()==v for n,v in manifest.items())
result=dict(old_diagnostic_image_decodings_unchanged=checked,historical_evidence_hashes_unchanged=len(manifest),new_training_run=False,new_inference_run=False)
Path('work/ki67-followup-20261114/uint-invariance.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
