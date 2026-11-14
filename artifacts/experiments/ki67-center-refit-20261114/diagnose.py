import json,gzip
from pathlib import Path
import numpy as np
from scipy.spatial.distance import cdist
from pathology_edge.ki67_evaluation import match_points
from pathology_edge.ki67_union import retain_candidates,summarize_locations
root=Path('work/localization-20261114');selection=json.loads((root/'selection.json').read_text());result=[]
for m in selection['models']:
 seed=m['seed'];rows=json.loads(gzip.decompress((root/f'validation-{seed}.json.gz').read_bytes()));saved=np.load(root/f'validation-output-{seed}.npz');t=m['diagnostic'];sc=saved[f"scores_{t['epoch']}"].astype(np.float64);xy=saved[f"xy_{t['epoch']}"];start=0;stages={k:[] for k in ('A','union','shifted_all','selected')};near_scores=[[] for _ in range(4)];far=[];miss_groups=np.zeros((4,3),int)
 for r in rows:
  n=len(r['points']);s=sc[start:start+n];new=xy[start:start+n];start+=n;gt=np.array(r['gt_points']).reshape(-1,2);gc=np.array(r['gt_classes']);chosen=retain_candidates(new,s,**t['config'])['points_xy']
  sets=dict(A=r['a_points'],union=r['points'],shifted_all=new,selected=chosen)
  for k,p in sets.items():stages[k].append({**r,'points':np.asarray(p).reshape(-1,2)})
  if len(gt) and n:
   d=cdist(new,gt);nearest=d.argmin(1);close=d.min(1)<=6
   far.extend(s[d.min(1)>12].tolist())
   for c in range(4):near_scores[c].extend(s[close&(gc[nearest]==c)].tolist())
   represented=np.any(d<=6,axis=0);high=np.any((d<=6)&(s[:,None]>=t['config']['threshold']),axis=0);matched={j for i,j in match_points(chosen,gt)}
   for j,c in enumerate(gc):
    if j not in matched:miss_groups[c,0 if not represented[j] else 1 if not high[j] else 2]+=1
 result.append(dict(seed=seed,selected_diagnostic=t['config'],stages={k:summarize_locations(v) for k,v in stages.items()},near_score_quantiles_by_gtclass=[np.quantile(s,[.1,.5,.9]).tolist() if s else [] for s in near_scores],far_score_quantiles=np.quantile(far,[.1,.5,.9]).tolist(),missed_by_class_and_stage=miss_groups.tolist(),missed_stage_names=['no_corrected_candidate_within6','all_matching_candidates_below_score','suppression_or_matching_competition']))
for r in result:print(json.dumps(dict(seed=r['seed'],class_counts=r['stages']['A']['true_class_counts'],stage_recall={k:[v['case_macro_recall'],*v['tumor_recalls']] for k,v in r['stages'].items()},missed=r['missed_by_class_and_stage'],near_scores=r['near_score_quantiles_by_gtclass'],far_scores=r['far_score_quantiles'])))
Path('work/ki67-next-20261114/diagnosis.json').write_text(json.dumps(result,indent=2)+'\n')
