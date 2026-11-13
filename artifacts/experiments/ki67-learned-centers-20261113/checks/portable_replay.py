import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import numpy as np

root=Path('artifacts/experiments/ki67-learned-centers-20261113').resolve()
bundle=json.loads((root/'inference-bundle.json').read_text());checks=[]
env={**os.environ,'PYTHONPATH':'frozen_source','PYTHONDONTWRITEBYTECODE':'1','OMP_NUM_THREADS':'2','OPENBLAS_NUM_THREADS':'2'}
with tempfile.TemporaryDirectory(prefix='center-replay-',dir='work') as folder:
    folder=Path(folder).resolve()
    for model in bundle['detectors']:
        seed=model['seed'];expected=json.loads((root/f'examples/expected-{seed}.json').read_text())
        for arm in bundle['classifiers']:
            output=folder/f'{seed}-{arm}.json'
            cmd=[sys.executable,'scripts/infer_ki67_centers.py','--bundle','inference-bundle.json','--image','examples/first-case.png',
                 '--detector-seed',str(seed),'--classifier',arm,'--output',str(output)]
            proc=subprocess.run(cmd,cwd=root,env=env,check=True,capture_output=True,text=True)
            r=json.loads(output.read_text())
            if r['points_xy']!=expected['points'] or r['scores']!=expected['scores'] or r['classes']!=expected['classes'][arm]:
                raise ValueError('Portable output differs from stored results')
            classes=np.asarray(r['classes']);prob=np.asarray(r['probabilities']).reshape(-1,4)
            pos=int((classes==0).sum());den=int(((classes==0)|(classes==1)).sum())
            ratio={'positive_tumor_cells':pos,'tumor_cells':den,'fraction':pos/den if den else None}
            if ratio!=r['positive_fraction'] or r['ground_truth_supplied'] or r['image_size_wh']!=[224,224]:raise ValueError('Output contract mismatch')
            if not np.isfinite(prob).all() or (prob<0).any() or (prob>1).any() or not np.allclose(prob.sum(1),1,atol=1e-6):raise ValueError('Invalid class scores')
            checks.append(dict(seed=seed,classifier=arm,candidates=len(classes),coordinates_scores_classes_exact=True,
                               fraction=ratio,ground_truth_supplied=False))
with (root/'portable-replay.json').open('x') as f:
    json.dump(dict(all_checks_passed=True,image_only_cli_calls=len(checks),unique_images=1,
                   training_run=False,checks=checks),f,indent=2)
print(json.dumps({'all_checks_passed':True,'image_only_cli_calls':len(checks),'unique_images':1}))
