import json
from pathlib import Path
import numpy as np
import torch
from pathology_edge.ki67_center_refit import checked,infer_peaks,CenterDetector
from pathology_edge.ki67_experiment import read_json,load_sample
from pathology_edge.ki67_union import retain_candidates,summarize_locations
root=Path('work/center-refit-20261114');p=checked(root,selected=True);models=read_json(root/'selection.json')['models'];torch.set_num_threads(2)
rows=[r for r in read_json(Path(p['parent'])/'source-manifest.json') if r['split']=='train'];data=[(r,*load_sample(p['data_dir'],r)) for r in rows];out=[]
for m in models:
 model=CenterDetector();model.load_state_dict(torch.load(root/(m['checkpoint'] or m['diagnostic_checkpoint']),weights_only=True,map_location='cpu'));cfg=(m['selected'] or m['diagnostic'])['config'];arms={k:[] for k in ('same_A_config','B_config')}
 for r,rgb,gt,gc in data:
  peaks=infer_peaks(rgb,model)
  for tag,config in [('same_A_config',m['a_config']),('B_config',cfg)]:
   arms[tag].append(dict(image=r['image'],case_id=r['case_id'],points=retain_candidates(peaks['points'],peaks['scores'],**config)['points_xy'],gt_points=gt,gt_classes=gc))
 summaries={k:summarize_locations(v) for k,v in arms.items()};out.append(dict(seed=m['seed'],selected_or_diagnostic_epoch=(m['selected'] or m['diagnostic'])['epoch'],summaries=summaries));print(m['seed'],{k:v['case_macro_f1'] for k,v in summaries.items()},flush=True)
(root/'train-fit-diagnostic.json').write_text(json.dumps(dict(scope='Post hoc training-set fit, same-A-config and diagnostic/adopted-B-config. Not generalization evidence; no model/threshold choice changed.',images=696,seeds=out),indent=2)+'\n')
