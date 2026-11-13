"""Independent rematching/count audit; never imports the new filter evaluator."""
import argparse
import json
from pathlib import Path
import hashlib
from collections import defaultdict
import numpy as np
from audit_auto_ki67 import recount, aggregate, compare


def read(path):
    return json.loads(Path(path).read_text())


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def audit(run,external=False):
    run=Path(run); tag='bcdata' if external else 'patherea'
    p=read(run/'protocol.json')
    parent=Path(p['external'] if external else p['parent'])
    predfile=parent/('private-predictions.json' if external else 'predictions.json')
    rows=read(predfile); retention=read(run/(tag+'-retention.json')); result=read(run/(tag+'-results.json'))
    old=read(parent/'results.json')['arms']
    compare(digest(predfile),result['baseline_prediction_sha256'])
    compare(digest(run/(tag+'-retention.json')),result['retention_sha256'])
    compare(digest(run/'selection-lock.json'),result['selection_lock_sha256'])
    threshold=read(run/'threshold-selection.json')['threshold']
    compare(threshold,result['threshold']); compare(len(rows),len(retention))
    filtered=[]
    for row,r in zip(rows,retention):
        compare(row['image'],r['image'])
        compare(len(row['points']),len(r['scores']))
        scores=np.asarray(r['scores'])
        if not np.isfinite(scores).all() or np.any(scores<0) or np.any(scores>1): raise ValueError('Invalid retained scores')
        indices=np.flatnonzero(scores>=threshold).tolist()
        compare(indices,r['keep_indices'])
        filtered.append({**row,'points':[row['points'][i] for i in indices],
                         'classes':{a:[v[i] for i in indices] for a,v in row['classes'].items()}})
    compare(sum(len(r['points']) for r in rows),result['original_candidates'])
    compare(sum(len(r['points']) for r in filtered),result['kept_candidates'])
    for variant,data in [('baseline',rows),('filtered',filtered)]:
        for arm,report in result[variant].items():
            stats=[recount(r,arm,external) for r in data]
            overall=aggregate(stats,external);compare(overall,report,variant+'/'+arm)
            if variant=='baseline': compare(overall,old[arm],'historical/'+arm)
            compare(len(data),len(report['per_image']))
            images=[]
            for row,s,stored in zip(data,stats,report['per_image']):
                compare(row['image'],stored['image']); v=aggregate([s],external)
                compare(v,stored); images.append(v)
            values=[('image',images)]
            if not external:
                groups=defaultdict(list)
                for row,s in zip(data,stats): groups[row['case_id']].append(s)
                cases=[]
                for c in report['per_case']:
                    v=aggregate(groups[c['case_id']],False); compare(v,c); cases.append(v)
                values.append(('case',cases))
            for kind,group in values:
                errors=[v['ratio_error_pp'] for v in group if v['ratio_error_pp'] is not None]
                compare(len(errors),report[kind+'_ratio_valid'])
                compare(float(np.mean(errors)) if errors else None,report[kind+'_ratio_mae_pp'])
                compare(float(np.mean([abs(v['count_error']) for v in group])),report[kind+'_count_mae'])
    return dict(all_checks_passed=True,scope=tag,images=len(rows),
        image_arm_recounts=len(rows)*len(result['baseline'])*2,
        baseline_matches_historical=True,retention_threshold_matches=True,
        independent_maximum_cardinality_solver=True,new_inference_run=False,
        original_candidates=result['original_candidates'],kept_candidates=result['kept_candidates'])


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True)
    p.add_argument('--external',action='store_true');p.add_argument('--output',type=Path,required=True)
    a=p.parse_args(); result=audit(a.run,a.external)
    with a.output.open('x') as f: json.dump(result,f,indent=2)
    print(json.dumps(result))
