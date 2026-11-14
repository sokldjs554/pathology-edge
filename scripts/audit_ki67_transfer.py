#!/usr/bin/env python3
"""Independent suppression/selection/aggregation, checkpoint and data audit."""
from collections import defaultdict
import argparse
import json
from pathlib import Path
import sys
import numpy as np
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from audit_ki67_union import independent_decode,_summary,compare_metrics,independent_choice,exact_points
from audit_ki67_center_refit import validate_saved_peaks,verify_reference,replay_peaks
from audit_ki67_normalized import validate_history,cached_summary
from audit_ki67_deepliif import independent_scores
from pathology_edge.ki67_transfer import TransferCenterDetector,balanced_probabilities
from pathology_edge.ki67_transfer_experiment import checked,primary_models,job_name,tensor_hashes,ARMS,SEEDS,FLOORS,DISTANCES
from pathology_edge.ki67_transfer_evaluation import evaluation_lock,classifier_for_seed,external_comparison,stability
from pathology_edge.ki67_union_experiment import read_rows
from pathology_edge.ki67_experiment import read_json,fresh_json,sha,verify_hashes,verify_data,load_sample
from pathology_edge.ki67_evaluation import match_points,count_metrics
from pathology_edge.ki67_external import tumor_only_row
from pathology_edge.ki67_localization_experiment import test_criteria
from pathology_edge.ki67_normalized_pipeline import pipeline_criteria


def cell_summary(rows,name):
    """Recount classes without production evaluate_cells or summarize."""
    if not rows or len({r['image'] for r in rows})!=len(rows):raise ValueError('Nonempty unique images required')
    facts=[];cases=defaultdict(list)
    def fraction(classes):
        positive=sum(c==0 for c in classes);tumor=sum(c in (0,1) for c in classes)
        return dict(positive_tumor_cells=positive,tumor_cells=tumor,fraction=positive/tumor if tumor else None)
    def group(ids):
        loc=np.sum([facts[i]['loc'] for i in ids],axis=0);correct=np.sum([facts[i]['correct'] for i in ids],axis=0)
        pp=[c for i in ids for c in rows[i]['classes'][name]];tt=[c for i in ids for c in rows[i]['gt_classes']]
        pc=np.bincount(pp,minlength=4);tc=np.bincount(tt,minlength=4)
        classes=[count_metrics(correct[c],pc[c]-correct[c],tc[c]-correct[c]) for c in range(4)]
        target,pred=fraction(tt),fraction(pp)
        error=None if target['fraction'] is None or pred['fraction'] is None else abs(target['fraction']-pred['fraction'])*100
        return dict(localization=count_metrics(*loc),classes=classes,macro_f1=float(np.mean([r['f1'] for r in classes])),target_fraction=target,predicted_fraction=pred,ratio_error_pp=error,count_error=len(pp)-len(tt))
    for i,r in enumerate(rows):
        pc=np.asarray(r['classes'][name]);tc=np.asarray(r['gt_classes']);xy=np.asarray(r['points']).reshape(-1,2);gt=np.asarray(r['gt_points']).reshape(-1,2)
        if len(pc)!=len(xy) or len(tc)!=len(gt):raise ValueError('Point/class correspondence differs')
        pairs=match_points(xy,gt,6);good=np.array([sum(pc[k]==tc[j]==c for k,j in pairs) for c in range(4)])
        facts.append(dict(loc=np.array([len(pairs),len(xy)-len(pairs),len(gt)-len(pairs)]),correct=good));cases[r['case_id']].append(i)
    result=group(list(range(len(rows))));images=[dict(image=r['image'],case_id=r['case_id'],**group([i])) for i,r in enumerate(rows)]
    case_rows=[dict(case_id=k,**group(v)) for k,v in sorted(cases.items())]
    result.update(per_image=images,per_case=case_rows,image_count=len(rows),case_count=len(cases))
    for prefix,rs in (('image',images),('case',case_rows)):
        valid=[r['ratio_error_pp'] for r in rs if r['ratio_error_pp'] is not None]
        result[prefix+'_ratio_mae_pp']=float(np.mean(valid)) if valid else None
        result[prefix+'_ratio_valid']=len(valid);result[prefix+'_count_mae']=float(np.mean([abs(r['count_error']) for r in rs]))
    tp=sum(int(f['loc'][0]) for f in facts);correct=sum(int(f['correct'].sum()) for f in facts)
    result['matched_only_accuracy']=correct/tp if tp else None
    return result


def replay_orders(seed,probabilities,epochs=24,draws=696,batch=8):
    rng=np.random.default_rng(seed);orders=[]
    for _ in range(epochs):
        order=rng.choice(len(probabilities),size=draws,replace=True,p=probabilities);orders.append(order)
        for start in range(0,draws,batch):
            n=len(order[start:start+batch])
            for _ in range(n):rng.integers(4);rng.random();rng.random()
            rng.uniform(.9,1.1,(n,3,1,1))
    return np.stack(orders)


def audit_worker(root,arm,seed):
    root=Path(root);p=checked(root);dest=root/job_name(arm,seed);complete=read_json(dest/'complete.json');verify_hashes(dest,complete['evidence_hashes'])
    if complete['protocol_sha256']!=sha(root/'protocol.json'):raise ValueError('Worker protocol differs')
    m=read_json(dest/'result.json')
    if (m['arm'],m['seed'],m['epochs'])!=(arm,seed,24):raise ValueError('Worker identity differs')
    torch.set_num_threads(1);torch.manual_seed(seed)
    official=torch.load(root/'official-weights.pth',weights_only=True,map_location='cpu');state={k.removeprefix('features.'):v for k,v in official.items() if k.startswith('features.')}
    model=TransferCenterDetector(state if arm=='pretrained' else None);initial=read_json(dest/'initial-tensors.json')
    if initial['features']!=tensor_hashes(model.features.state_dict()) or initial['decoder']!=tensor_hashes(model.decoder.state_dict()):raise ValueError('Initialization differs')
    saved_features=torch.load(dest/'features.pt',weights_only=True,map_location='cpu')
    if tensor_hashes(saved_features)!=initial['features'] or initial['official_equal']!=(arm=='pretrained'):raise ValueError('Frozen feature evidence differs')
    manifest=read_json(Path(p['parent'])/'source-manifest.json');train=[r for r in manifest if r['split']=='train'];refs={r['image']:r for r in manifest if r['split']=='validation'}
    if not np.array_equal(np.load(dest/'training-orders.npz')['orders'],replay_orders(seed,balanced_probabilities(train))):raise ValueError('Sampling/augmentation RNG schedule differs')
    verify_data(p['data_dir'],list(refs.values()));images={n:load_sample(p['data_dir'],r) for n,r in refs.items()}
    rows=read_rows(dest/'validation.json.gz');history=read_rows(dest/'trials.json.gz');validate_history(history);saved=np.load(dest/'validation-peaks.npz',allow_pickle=False)
    if len(rows)!=227 or {r['image'] for r in rows}!=set(refs):raise ValueError('Validation membership differs')
    if set(saved.files)!={f'{k}_{e}' for e in range(1,25) for k in ('points','scores','offsets')}:raise ValueError('Raw epoch evidence missing')
    for r in rows:verify_reference(r,refs[r['image']],*images[r['image']][1:])
    baseline=_summary(rows,[np.asarray(r['a_points']).reshape(-1,2) for r in rows]);compare_metrics(baseline,m['baseline']);trials=[]
    for h in history:
        epoch=h['epoch'];xy=saved[f'points_{epoch}'];sc=saved[f'scores_{epoch}'].astype(np.float64);off=saved[f'offsets_{epoch}'];validate_saved_peaks(xy,sc,off,len(rows),(224,224))
        pieces=[(xy[a:b],sc[a:b]) for a,b in zip(off[:-1],off[1:])];cache={}
        decoded={d:[independent_decode(x,s,dict(threshold=.01,min_distance=d)) for x,s in pieces] for d in DISTANCES}
        for t in h['trials']:
            cfg=t['config'];pts=[x[s>=cfg['threshold']] for x,s in decoded[cfg['min_distance']]]
            compare_metrics(cached_summary(rows,pts,cache),t);trials.append(t)
        if sum(independent_choice([t],baseline,FLOORS) is not None for t in h['trials'])!=h['feasible_trials']:raise ValueError('Feasible trial count differs')
    chosen=independent_choice(trials,baseline,FLOORS);diagnostic=max(trials,key=lambda t:(t['case_macro_f1'],t['case_macro_recall'],-t['epoch'],t['config']['threshold'],t['config']['min_distance']))
    if chosen!=m['selected'] or diagnostic!=m['diagnostic'] or m['evaluation_trial']!=(chosen if chosen is not None else diagnostic):raise ValueError('Selected/diagnostic choice differs')
    targets=[(diagnostic,'diagnostic.pt')]+([(chosen,'selected.pt')] if chosen is not None else []);replays=0
    for trial,filename in targets:
        model.decoder.load_state_dict(torch.load(dest/filename,weights_only=True,map_location='cpu'),strict=True);epoch=trial['epoch']
        for i,r in enumerate(rows):
            xy,sc=replay_peaks(images[r['image']][0],model);lo,hi=saved[f'offsets_{epoch}'][i:i+2]
            exact_points(xy,saved[f'points_{epoch}'][lo:hi])
            if not np.array_equal(sc,saved[f'scores_{epoch}'][lo:hi].astype(np.float64)):raise ValueError('Checkpoint replay score differs')
            replays+=1
    resume=torch.load(dest/'final-resume.pt',weights_only=True,map_location='cpu')
    if resume['epochs']!=24 or not resume['optimizer']['state'] or any(float(s['step'])!=2088 for s in resume['optimizer']['state'].values()):raise ValueError('Optimizer step history differs')
    if not all(torch.isfinite(v).all() for v in resume['decoder'].values()):raise ValueError('Final decoder not finite')
    verify_hashes(dest,complete['evidence_hashes']);checked(root)
    result=dict(arm=arm,seed=seed,all_checks_passed=True,trials=len(trials),checkpoint_replay_images=replays,official_feature_match=arm=='pretrained',sampling_epochs_checked=24,eligible=chosen is not None,complete_sha256=sha(dest/'complete.json'))
    fresh_json(dest/'audit-worker.json',result);print(json.dumps(result),flush=True);return result


def audit_evaluations(root):
    root=Path(root);p=evaluation_lock(root);models=primary_models(read_json(root/'selection.json'));workers=[]
    for arm in ARMS:
        for seed in SEEDS:
            dest=root/job_name(arm,seed);r=read_json(dest/'audit-worker.json')
            if not r['all_checks_passed'] or r['complete_sha256']!=sha(dest/'complete.json'):raise ValueError('Worker audit invalid')
            workers.append(r)
    checks=0
    for split in ('validation','test','bcdata','deepliif'):
        folder=root/'evaluation'/split;summary=read_json(folder/'summary.json');verify_hashes(folder,summary['evidence_hashes']);decisions=[]
        if split in ('validation','test'):
            refs=[r for r in read_json(Path(p['parent'])/'source-manifest.json') if r['split']==split];verify_data(p['data_dir'],refs)
            gtmap={r['image']:load_sample(p['data_dir'],r)[1:] for r in refs}
        elif split=='bcdata':
            refs=read_json(Path(p['external'])/'private-predictions.json');refs=sorted(refs,key=lambda r:r['image']);gtmap={r['image']:(r['gt_points'],r['gt_classes']) for r in refs}
        else:
            refs=read_rows(folder/'input-audit.json.gz');gtmap={r['image']:(r['gt_points'],r['gt_classes']) for r in refs}
        names=[r['image'] for r in refs]
        if len(names)!={'validation':227,'test':407,'bcdata':133,'deepliif':597}[split] or len(set(names))!=len(names):raise ValueError('Audit membership count differs')
        for m in models:
            seed=m['seed'];name=classifier_for_seed(seed);dest=folder/str(seed);stored=read_rows(dest/'scores.json.gz')[0];comparison=read_json(dest/'comparison.json');actual={};locations={}
            for arm in ('A','B'):
                rows=read_rows(dest/(arm+'.json.gz'))
                if [r['image'] for r in rows]!=names or any(set(r['classes'])!={name} for r in rows):raise ValueError('Evaluation membership/classifier differs')
                for r in rows:
                    exact_points(r['gt_points'],gtmap[r['image']][0])
                    if r['gt_classes']!=np.asarray(gtmap[r['image']][1]).tolist():raise ValueError('Reference classes differ')
                if split=='deepliif':
                    actual[arm]={str(radius):independent_scores(rows,name,radius) for radius in (6,12)}
                elif split=='bcdata':
                    score=cell_summary([tumor_only_row(r,name) for r in rows],name)
                    for k in list(score):
                        if k.startswith('case_') or k=='per_case':del score[k]
                    for r in [score,*score['per_image']]:r['two_class_macro_f1']=float(np.mean([c['f1'] for c in r['classes'][:2]]));r['classes']=r['classes'][:2];r.pop('macro_f1');r.pop('case_id',None)
                    actual[arm]=score
                else:
                    actual[arm]=cell_summary(rows,name);locations[arm]=_summary(rows,[np.asarray(r['points']).reshape(-1,2) for r in rows])
                compare_metrics(actual[arm],stored[arm]);checks+=2 if split=='deepliif' else 1
            if split=='deepliif':
                for radius in ('6','12'):compare_metrics(external_comparison(stored['A'][radius],stored['B'][radius]),comparison[radius])
                passed=comparison['6']['passed']
            elif split=='bcdata':
                converted={a:{**v,'per_image':[dict(image=r['image'],gt_fraction=r['target_fraction']['fraction'],pred_fraction=r['predicted_fraction']['fraction']) for r in v['per_image']]} for a,v in actual.items()}
                result=external_comparison(converted['A'],converted['B']);compare_metrics(result,comparison);passed=result['passed']
            else:
                dc=test_criteria(locations['A'],locations['B']);pc=pipeline_criteria(actual['A'],actual['B'],sorted({r['case_id'] for r in refs}))
                compare_metrics(dict(A=locations['A'],B=locations['B'],detection_criteria=dc,pipeline_criteria=pc,passed=all(dc.values()) and all(pc.values())),comparison);passed=comparison['passed']
            decisions.append(dict(seed=seed,eligible=m['selected'] is not None,passed=passed))
        compare_metrics(stability(decisions),summary)
    result=dict(all_checks_passed=True,trial_checks=sum(r['trials'] for r in workers),checkpoint_replay_images=sum(r['checkpoint_replay_images'] for r in workers),metric_summaries=checks,workers=workers,
        scope='Independent NMS/selection/metric accumulation; shared tested matching and peak primitives. Full selected validation checkpoint replay; heldout saved outputs recounted, not full heldout model replay.',
        learner_files_preserved=True,evaluation_lock_sha256=sha(root/'evaluation-lock.json'))
    evaluation_lock(root);fresh_json(root/'audit.json',result);return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--run',required=True);parser.add_argument('--worker',nargs=2,metavar=('ARM','SEED'));a=parser.parse_args()
    if a.worker:audit_worker(a.run,a.worker[0],int(a.worker[1]))
    else:print(json.dumps(audit_evaluations(a.run)),flush=True)
