#!/usr/bin/env python3
"""Replay saved validation evidence with independent suppression/selection logic."""
from collections import defaultdict
import argparse
import json
from pathlib import Path
import sys
import numpy as np
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from pathology_edge.ki67_evaluation import match_points, count_metrics
from pathology_edge.ki67_experiment import read_json, fresh_json, sha, load_sample, verify_data
from pathology_edge.ki67_union_experiment import checked, read_rows, SEEDS, THRESHOLDS, DISTANCES, LOG_CONFIG, LEARNED_CONFIG


def exact_points(actual,expected):
    a=np.asarray(actual).reshape(-1,2);b=np.asarray(expected).reshape(-1,2)
    if not np.array_equal(a,b):raise ValueError('Candidate/reference coordinates differ')


def independent_decode(points,scores,config):
    points=np.asarray(points,dtype=np.int64).reshape(-1,2);scores=np.asarray(scores)
    if scores.shape!=(len(points),) or not np.isfinite(scores).all() or np.any(scores<0) or np.any(scores>1):raise ValueError('Invalid saved gate scores')
    order=sorted(range(len(points)),key=lambda i:(-float(scores[i]),int(points[i,1]),int(points[i,0])))
    # Different implementation from production: boolean exclusion using squared
    # distances from each kept center, with deterministic score/y/x ordering.
    excluded=np.zeros(len(points),dtype=bool);kept=[]
    for i in order:
        if scores[i]<config['threshold']:break
        if excluded[i]:continue
        kept.append(i)
        delta=points-points[i]
        excluded|=np.einsum('ij,ij->i',delta,delta)<config['min_distance']**2
    return points[kept],scores[kept]


def _summary(rows,points):
    case_counts=defaultdict(lambda:np.zeros(3,dtype=int));matches=np.zeros(4,dtype=int);totals=np.zeros(4,dtype=int)
    for r,xy in zip(rows,points):
        gt=np.asarray(r['gt_points']).reshape(-1,2);gc=np.asarray(r['gt_classes'],dtype=int)
        pairs=match_points(xy,gt,6);case_counts[r['case_id']]+=[len(pairs),len(xy)-len(pairs),len(gt)-len(pairs)]
        totals+=np.bincount(gc,minlength=4);matches+=np.bincount([gc[j] for _,j in pairs],minlength=4)
    cases={k:count_metrics(*v) for k,v in sorted(case_counts.items())}
    return dict(localization=count_metrics(*np.sum(list(case_counts.values()),axis=0)),cases=cases,
        case_macro_f1=float(np.mean([r['f1'] for r in cases.values()])),case_macro_recall=float(np.mean([r['recall'] for r in cases.values()])),
        tumor_recalls=[float(matches[k]/totals[k]) if totals[k] else 0. for k in (0,1)],matched_by_true_class=matches.tolist(),true_class_counts=totals.tolist())


def independent_summary(rows,scores,config):
    return _summary(rows,[independent_decode(r['points'],s,config)[0] for r,s in zip(rows,scores)])


def compare_metrics(actual,expected):
    def same(a,b,path):
        if isinstance(a,dict):
            for k,v in a.items():same(v,b[k],path+'/'+k)
        elif isinstance(a,(list,tuple)):
            if len(a)!=len(b):raise ValueError('Count mismatch '+path)
            for i,(x,y) in enumerate(zip(a,b)):same(x,y,path+'/'+str(i))
        elif isinstance(a,(float,np.floating)):
            if not np.isfinite(b) or not np.isclose(a,b,rtol=0,atol=1e-12):raise ValueError('Metric mismatch '+path)
        elif a!=b:raise ValueError('Metric mismatch '+path)
    same(actual,expected,'')


def independent_choice(trials,baseline,floors):
    choices=[]
    for t in trials:
        if t['split']!='validation':raise ValueError('Nonvalidation selection')
        if t['localization']['fp']>baseline['localization']['fp']:continue
        if t['localization']['fn']>baseline['localization']['fn']:continue
        if (t['localization']['fp'],t['localization']['fn'])==(baseline['localization']['fp'],baseline['localization']['fn']):continue
        if t['case_macro_recall']<floors['case_macro_recall']:continue
        if any(t['tumor_recalls'][i]<floors['tumor_recalls'][i] for i in (0,1)):continue
        if set(t['cases'])!=set(baseline['cases']):raise ValueError('Validation case set changed')
        if any(t['cases'][k]['recall']<.9*v['recall'] for k,v in baseline['cases'].items()):continue
        choices.append(t)
    key=lambda t:(t['case_macro_f1'],t['case_macro_recall'],-t['epoch'],t['config']['threshold'],t['config']['min_distance'])
    return max(choices,key=key) if choices else None


def audit(root,replay=True):
    root=Path(root);p=checked(root,selected=True);selection=read_json(root/'selection.json')
    if [m['seed'] for m in selection['models']]!=list(SEEDS):raise ValueError('Missing failed seed report')
    manifest={r['image']:r for r in read_json(Path(p['parent'])/'source-manifest.json') if r['split']=='validation'}
    if len(manifest)!=227:raise ValueError('Validation scope mismatch')
    verify_data(p['data_dir'],list(manifest.values()))
    if replay:
        from pathology_edge.ki67_center_experiment import loaded_detectors
        from pathology_edge.ki67_centers import predict_centers, peak_candidates, decode_candidates
        from pathology_edge.ki67_detection import detect_centers
        from pathology_edge.ki67_union import CandidateRejector, retention_scores
        detectors=loaded_detectors(p['prior']);torch.set_num_threads(2)
    checks=0;replays=0;rows_report=[]
    for model in selection['models']:
        seed=model['seed'];rows=read_rows(root/f'validation-{seed}.json.gz');history=read_rows(root/f'trials-{seed}.json.gz')
        if {r['image'] for r in rows}!=set(manifest) or len(rows)!=227 or any(r['split']!='validation' for r in rows):raise ValueError('Saved validation set differs')
        if [h['epoch'] for h in history]!=list(range(1,13)):raise ValueError('Missing training epochs')
        lengths=[len(r['points']) for r in rows];offsets=np.cumsum([0,*lengths]);scorefile=np.load(root/f'validation-scores-{seed}.npz',allow_pickle=False)
        if set(scorefile.files)!={f'epoch_{e}' for e in range(1,13)}:raise ValueError('Missing epoch scores')
        baseline=_summary(rows,[np.asarray(r['a_points']).reshape(-1,2) for r in rows]);compare_metrics(baseline,model['baseline'])
        compare_metrics(_summary(rows,[np.asarray(r['points']).reshape(-1,2) for r in rows]),model['union'])
        all_trials=[]
        for h in history:
            epoch=h['epoch'];scores=scorefile[f'epoch_{epoch}']
            if scores.shape!=(sum(lengths),):raise ValueError('Score array length mismatch')
            pieces=[scores[a:b] for a,b in zip(offsets[:-1],offsets[1:])]
            if len(h['trials'])!=42 or {(t['config']['threshold'],t['config']['min_distance']) for t in h['trials']}!={(t,d) for t in THRESHOLDS for d in DISTANCES}:raise ValueError('Trial grid mismatch')
            cache={d:[independent_decode(r['points'],s,dict(threshold=0,min_distance=d)) for r,s in zip(rows,pieces)] for d in DISTANCES}
            for trial in h['trials']:
                cfg=trial['config'];points=[xy[score>=cfg['threshold']] for xy,score in cache[cfg['min_distance']]]
                recomputed=_summary(rows,points);compare_metrics(recomputed,trial)
                all_trials.append(trial);checks+=1
            eligible=sum(independent_choice([t],baseline,p['floors']) is not None for t in h['trials'])
            if eligible!=h['feasible_trials']:raise ValueError('Feasibility count differs')
        chosen=independent_choice(all_trials,baseline,p['floors'])
        if chosen!=model['selected']:raise ValueError('Selected trial differs')
        if sum(h['feasible_trials'] for h in history)!=model['feasible_trials']:raise ValueError('Seed feasibility count differs')
        diagnostic=max(all_trials,key=lambda t:(t['case_macro_f1'],t['case_macro_recall'],-t['epoch'],t['config']['threshold'],t['config']['min_distance']))
        if diagnostic!=model['diagnostic']:raise ValueError('Diagnostic selection differs')
        if replay:
            gate=CandidateRejector();item=chosen or diagnostic;checkpoint=model['checkpoint'] or model['diagnostic_checkpoint']
            gate.load_state_dict(torch.load(root/checkpoint,weights_only=True,map_location='cpu'))
            selected_scores=scorefile[f"epoch_{item['epoch']}"]
            for index,r in enumerate(rows):
                rgb,gt,gc=load_sample(p['data_dir'],manifest[r['image']]);exact_points(gt,r['gt_points'])
                if gc.tolist()!=r['gt_classes']:raise ValueError('Ground truth classes differ')
                detector,a_config=detectors[seed];found=predict_centers(rgb,detector,LEARNED_CONFIG)
                a=decode_candidates(*peak_candidates(found['probability_map']),**a_config)['points_xy'];exact_points(a,r['a_points'])
                log=detect_centers(rgb,LOG_CONFIG)['points_xy'];exact_points(log,r['log_points'])
                learned={tuple(v) for v in found['points_xy'].tolist()};classical={tuple(v) for v in log.tolist()}
                union=sorted(learned|classical,key=lambda v:(v[1],v[0]));exact_points(union,r['points'])
                source=[int(v in learned)+2*int(v in classical) for v in union]
                if source!=r['sources']:raise ValueError('Union source bits differ')
                scores=retention_scores(rgb,np.asarray(union).reshape(-1,2),gate)
                if not np.array_equal(scores,selected_scores[offsets[index]:offsets[index+1]]):raise ValueError('Checkpoint scores differ')
                replays+=1
        rows_report.append(dict(seed=seed,eligible=chosen is not None,trials_checked=len(all_trials),diagnostic_epoch=diagnostic['epoch']))
        print('AUDITED',seed,flush=True)
    eligible=[m for m in selection['models'] if m['selected'] is not None]
    if not eligible:
        for tag in ('internal','external'):
            skipped=read_json(root/(tag+'-not-run.json'))
            if skipped['new_inference_images']!=0 or (root/(tag+'-started.json')).exists():raise ValueError('Ineligible run evaluated holdout')
    evaluation_checks=0
    if eligible:
        from pathology_edge.ki67_experiment import summarize
        from pathology_edge.ki67_center_experiment import score_external
        for model in eligible:
            for tag in ('internal','external'):
                for arm in ('A','B','C','C0'):
                    folder=root/f"seed-{model['seed']}"/tag/arm;rs=read_rows(folder/'predictions.json.gz');result=read_json(folder/'results.json')
                    if sha(folder/'predictions.json.gz')!=result['predictions_sha256'] or result['selection_lock_sha256']!=sha(root/'selection-lock.json'):raise ValueError('Evaluation evidence changed')
                    if len(rs)!=(133 if tag=='external' else 407):raise ValueError('Evaluation scope differs')
                    for name,expected in result['classifiers'].items():
                        actual=score_external(rs,name) if tag=='external' else summarize(rs,name)
                        compare_metrics(actual,expected);evaluation_checks+=1
    return dict(all_checks_passed=True,selection_lock_sha256=sha(root/'selection-lock.json'),trial_checks=checks,
        checkpoint_and_proposal_replay_images=replays,evaluation_classifier_summaries=evaluation_checks,seeds=rows_report,
        eligible_seeds=len(eligible),test_external_evaluated=bool(eligible),reference_masks_verified=227*5,
        scope='Validation selection and reused evaluation evidence audit, not clinical or whole-WSI validation')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();report=audit(args.output);fresh_json(args.output/'audit.json',report);print(json.dumps(report),flush=True)
if __name__=='__main__':main()
