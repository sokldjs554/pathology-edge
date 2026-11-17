import gzip,json
from pathlib import Path
root=Path('work/localization-20261114');p=json.loads((root/'protocol.json').read_text());rows=[]
for m in json.loads((root/'selection.json').read_text())['models']:
 a=m['baseline'];base=a['localization'];trials=[t for h in json.loads(gzip.decompress((root/f"trials-{m['seed']}.json.gz").read_bytes())) for t in h['trials']]
 def flags(t):
  loc=t['localization']
  return dict(joint_fp_fn=loc['fp']<=base['fp'] and loc['fn']<=base['fn'] and (loc['fp']<base['fp'] or loc['fn']<base['fn']),case_mean_floor=t['case_macro_recall']>=p['floors']['case_macro_recall'],tumor_positive_floor=t['tumor_recalls'][0]>=p['floors']['tumor_recalls'][0],tumor_negative_floor=t['tumor_recalls'][1]>=p['floors']['tumor_recalls'][1],every_case=all(t['cases'][k]['recall']>=.9*v['recall'] for k,v in a['cases'].items()))
 joint=[t for t in trials if flags(t)['joint_fp_fn']]
 best=max(joint,key=lambda t:(t['case_macro_f1'],t['case_macro_recall'],-t['epoch'],t['config']['threshold'],t['config']['min_distance'])) if joint else None
 rows.append(dict(seed=m['seed'],trial_count=len(trials),full_condition_count=sum(all(flags(t).values()) for t in trials),joint_condition_count=len(joint),individual_condition_counts={k:sum(flags(t)[k] for t in trials) for k in flags(trials[0])},baseline=a,diagnostic=m['diagnostic'],diagnostic_conditions=flags(m['diagnostic']),best_joint_diagnostic=best,best_joint_conditions=flags(best) if best else None))
result=dict(scope='Post hoc failure diagnosis only; original all-constraint selection unchanged. Validation227/4cases, not test performance.',floors=p['floors'],seeds=rows)
(root/'failure-analysis.json').write_text(json.dumps(result,indent=2)+'\n')
for r in rows:
 t=r['best_joint_diagnostic'];print(json.dumps(dict(seed=r['seed'],config=t['config'],epoch=t['epoch'],counts=t['localization'],f1=t['case_macro_f1'],case_recall=t['case_macro_recall'],tumor_recalls=t['tumor_recalls'],conditions=r['best_joint_conditions'])))
