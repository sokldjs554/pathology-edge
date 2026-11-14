import json,time
from pathlib import Path
import numpy as np
import torch
from pathology_edge.ki67_center_experiment import loaded_detectors
from pathology_edge.ki67_centers import predict_centers
from pathology_edge.ki67_experiment import load_sample,sha
from pathology_edge.ki67_union import summarize_locations
root=Path('work/learned-centers-leaky-run-20261113');p=json.loads((root/'protocol.json').read_text());rows=[r for r in json.loads((Path(p['parent'])/'source-manifest.json').read_text()) if r['split']=='train'];torch.set_num_threads(2)
images=[]
for r in rows:
 rgb,gt,gc=load_sample(p['data_dir'],r);images.append((r,rgb,gt,gc))
results=[]
for seed,(model,config) in loaded_detectors(root).items():
 started=time.perf_counter();pred=[]
 for r,rgb,gt,gc in images:
  found=predict_centers(rgb,model,config);pred.append(dict(image=r['image'],case_id=r['case_id'],points=found['points_xy'],gt_points=gt,gt_classes=gc))
 summary=summarize_locations(pred);report=dict(seed=seed,model_sha256=sha(root/f'detector-{seed}.pt'),scope='Training-set fit diagnostic, not held-out performance. No fitting or test access.',images=len(rows),seconds=time.perf_counter()-started,summary=summary);results.append(report);print(json.dumps(dict(seed=seed,training_f1=summary['case_macro_f1'],recall=summary['case_macro_recall'],tumor_recalls=summary['tumor_recalls'],seconds=report['seconds'])),flush=True)
Path('work/ki67-next-20261114/train-fit.json').write_text(json.dumps(results,indent=2)+'\n')
