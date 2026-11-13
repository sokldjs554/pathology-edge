"""Independent decoder replay and count audit; does not import production decoders."""
import argparse
from collections import defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.optimize import linear_sum_assignment
from audit_auto_ki67 import recount,aggregate,compare


def read(path):
    return json.load(gzip.open(path,'rt')) if str(path).endswith('.gz') else json.loads(Path(path).read_text())


def decode(row,config):
    points=np.asarray(row['points'],dtype=float).reshape(-1,2);scores=row['scores'];kept=[]
    order=sorted(range(len(points)),key=lambda i:(-scores[i],points[i,1],points[i,0]))
    for i in order:
        if scores[i]<config['threshold']:continue
        if kept and np.any(((points[kept]-points[i])**2).sum(1)<config['min_distance']**2):continue
        kept.append(i)
    return points[kept].tolist()


def stats(row):
    return recount({**row,'classes':{'audit':[0]*len(row['points'])}},'audit',False)


def matched_gt_indices(points,gt):
    points=np.asarray(points).reshape(-1,2);gt=np.asarray(gt).reshape(-1,2)
    if not len(points) or not len(gt):return set()
    distances=np.sqrt(((points[:,None]-gt[None])**2).sum(2));penalty=min(len(points),len(gt))+1
    costs=np.concatenate([np.where(distances<=6,distances/6,2*penalty),np.full((len(points),len(points)),penalty)],1)
    ii,jj=linear_sum_assignment(costs)
    return {int(j) for i,j in zip(ii,jj) if j<len(gt) and distances[i,j]<=6}


def validate_selection(root):
    selection=read(root/'selection.json');trials_checked=0;stages_checked=0
    baseline=read(root/'validation-log.json.gz');bg=defaultdict(list);bt=np.zeros(4,dtype=int);br=np.zeros(4,dtype=int)
    for row in baseline:
        bg[row['case_id']].append(stats(row));gc=np.asarray(row['gt_classes'],dtype=int)
        ids=matched_gt_indices(row['points'],row['gt_points']);bt+=np.bincount(gc[list(ids)],minlength=4);br+=np.bincount(gc,minlength=4)
    baseline_recall=float(np.mean([aggregate(v,False)['localization']['recall'] for v in bg.values()]))
    compare(baseline_recall,selection['baseline']['case_macro_recall']);compare((bt[:2]/br[:2]).tolist(),selection['baseline']['tumor_recalls'])
    for model in selection['models']:
        samples=read(root/f"validation-peaks-{model['seed']}.json.gz")
        for trial in model['trials']:
            groups=defaultdict(list);matched_classes=np.zeros(4,dtype=int);reference_classes=np.zeros(4,dtype=int)
            for row in samples:
                decoded=decode(row,trial['config']);groups[row['case_id']].append(stats({**row,'points':decoded}))
                ids=matched_gt_indices(decoded,row['gt_points']);gc=np.asarray(row['gt_classes'],dtype=int)
                matched_classes+=np.bincount(gc[list(ids)],minlength=4);reference_classes+=np.bincount(gc,minlength=4)
            cases={k:aggregate(v,False)['localization'] for k,v in groups.items()}
            compare(cases,trial['cases']);compare(float(np.mean([v['f1'] for v in cases.values()])),trial['case_macro_f1'])
            compare(float(np.mean([v['recall'] for v in cases.values()])),trial['case_macro_recall'])
            compare(matched_classes.tolist(),trial['matched_by_reference_class']);compare(reference_classes.tolist(),trial['reference_by_class'])
            compare((matched_classes[:2]/reference_classes[:2]).tolist(),trial['tumor_recalls'])
            trials_checked+=1
        # Radius coverage independently reconstructed for each final unmatched GT.
        for row in samples:
            raw=np.asarray(row['points']).reshape(-1,2);scores=np.asarray(row['scores']);gt=np.asarray(row['gt_points']).reshape(-1,2)
            passed=raw[scores>=model['old_config']['threshold']];kept=np.asarray(decode(row,model['old_config'])).reshape(-1,2)
            old=row['diagnosis'];counted=defaultdict(int);matched=matched_gt_indices(kept,gt)
            for j,reason in enumerate(old['reasons']):
                if reason=='matched':
                    if j not in matched:raise ValueError('Wrong matched reference')
                    counted[reason]+=1;continue
                if j in matched:raise ValueError('Matched reference marked missed')
                near=[bool(np.any(((p-gt[j])**2).sum(1)<=36)) for p in (raw,passed,kept)]
                expected='no_peak' if not near[0] else 'below_threshold' if not near[1] else 'distance_suppressed' if not near[2] else 'assignment_competition'
                if reason!=expected:raise ValueError('FN stage mismatch')
                counted[reason]+=1
            compare({k:counted[k] for k in old['counts']},old['counts'])
            compare(stats({**row,'points':kept.tolist()})['matched'],old['counts']['matched']);stages_checked+=len(gt)
        floors=model['floors']
        feasible=[t for t in model['trials'] if t['case_macro_recall']>=floors['case_macro_recall'] and all(x>=y for x,y in zip(t['tumor_recalls'],floors['tumor_recalls']))]
        expected=max(feasible,key=lambda t:(t['case_macro_f1'],t['case_macro_recall'],t['config']['threshold'],t['config']['min_distance'])) if feasible else None
        if expected!=model['selected'] or len(feasible)!=model['feasible_trials']:raise ValueError('Selection mismatch')
    return dict(validation_trials=trials_checked,reference_stage_checks=stages_checked)


def evaluate_audit(folder,external):
    rows=read(folder/'predictions.json.gz');result=read(folder/'results.json');recounts=0
    digest=hashlib.sha256((folder/'predictions.json.gz').read_bytes()).hexdigest()
    compare(digest,result['predictions_sha256'])
    for arm,report in result['arms'].items():
        calculated=[recount(r,arm,external) for r in rows];groups=defaultdict(list);images=[]
        for row,stat,stored in zip(rows,calculated,report['per_image']):
            compare(row['image'],stored['image']);value=aggregate([stat],external);compare(value,stored);images.append(value)
            if not external:groups[row['case_id']].append(stat)
            recounts+=1
        compare(aggregate(calculated,external),report)
        cases=[]
        if not external:
            for stored in report['per_case']:
                value=aggregate(groups[stored['case_id']],False);compare(value,stored);cases.append(value)
        for kind,values in [('image',images)]+([] if external else [('case',cases)]):
            errors=[v['ratio_error_pp'] for v in values if v['ratio_error_pp'] is not None]
            compare(len(errors),report[kind+'_ratio_valid']);compare(float(np.mean(errors)) if errors else None,report[kind+'_ratio_mae_pp'])
    return recounts


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True)
    p.add_argument('--scope',choices=['full','public'],default='full',help='public audits validation/internal only; external coordinates are not redistributed')
    p.add_argument('--report',type=Path);a=p.parse_args();root=a.run
    lock=read(root/'selection-lock.json')
    for name,key in [('protocol.json','protocol_sha256'),('selection.json','selection_sha256')]:compare(hashlib.sha256((root/name).read_bytes()).hexdigest(),lock[key])
    for name,digest in lock['evidence_hashes'].items():compare(hashlib.sha256((root/name).read_bytes()).hexdigest(),digest)
    evidence=validate_selection(root);print('VALIDATION',evidence,flush=True)
    n=0
    for model in read(root/'selection.json')['models']:
        if model['selected'] is None:continue
        for scope in (('internal','external') if a.scope=='full' else ('internal',)):
            n+=evaluate_audit(root/f"seed-{model['seed']}"/scope,scope=='external');print('AUDITED',scope,flush=True)
    result=dict(all_checks_passed=True,**evidence,image_classifier_recounts=n,new_inference_run=False,audit_scope=a.scope,external_point_recount_run=a.scope=='full')
    with (a.report or root/'independent-audit.json').open('x') as f:json.dump(result,f,indent=2)
    print(result)


if __name__=='__main__':main()
