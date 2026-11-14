import gzip,json
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
from sklearn.metrics import roc_auc_score,average_precision_score
from pathology_edge.ki67_union import retain_candidates
from pathology_edge.ki67_evaluation import match_points
root=Path('work/union-gate-20261113');selection=json.load(open(root/'selection.json'));report=[]
for model in selection['models']:
 seed=model['seed'];rows=json.load(gzip.open(root/f'validation-{seed}.json.gz','rt'));chosen=model['diagnostic'];values=np.load(root/f'validation-scores-{seed}.npz')[f"epoch_{chosen['epoch']}"] .astype(np.float64)
 offset=0;labels=[];scores=[];kept_buckets={'fp_6_to_12':0,'fp_farther_12':0,'fp_duplicate_within_6':0,'fp_border24':0,'tp':0};all_buckets={}
 for r in rows:
  points=np.array(r['points']).reshape(-1,2);gt=np.array(r['gt_points']).reshape(-1,2);v=values[offset:offset+len(points)];offset+=len(points)
  d=cKDTree(gt).query(points)[0] if len(gt) else np.full(len(points),np.inf)
  labels.extend((d<=6).tolist());scores.extend(v.tolist())
  for name,mask in {'near_6':d<=6,'ambiguous_6_12':(d>6)&(d<=12),'far_12':d>12}.items():all_buckets.setdefault(name,[]).extend(v[mask].tolist())
  kept=retain_candidates(points,v,**chosen['config']);xy=kept['points_xy'];pairs=match_points(xy,gt);tp={i for i,j in pairs};kept_buckets['tp']+=len(pairs)
  for i,idx in enumerate(kept['indices']):
   if i in tp:continue
   key='fp_duplicate_within_6' if d[idx]<=6 else 'fp_6_to_12' if d[idx]<=12 else 'fp_farther_12';kept_buckets[key]+=1
   x,y=points[idx];kept_buckets['fp_border24']+=int(x<24 or y<24 or x>=200 or y>=200)
 result=dict(seed=seed,diagnostic_epoch=chosen['epoch'],candidate_proximity_auroc=roc_auc_score(labels,scores),candidate_proximity_average_precision=average_precision_score(labels,scores),score_quantiles={k:np.quantile(v,[.1,.5,.9]).tolist() for k,v in all_buckets.items()},kept=kept_buckets)
 report.append(result);print(json.dumps(result),flush=True)
Path('work/ki67-followup-20261114/diagnosis.json').write_text(json.dumps({'scope':'Reused validation diagnostic, candidate proximity labels not expert cell/noncell truth. No new training/test/external inference.','seeds':report},indent=2)+'\n')
