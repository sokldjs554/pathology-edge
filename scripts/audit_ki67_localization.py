#!/usr/bin/env python3
"""Independent saved-coordinate, selection and checkpoint replay audit."""
import argparse
import json
from pathlib import Path
import sys
import numpy as np
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from audit_ki67_union import independent_decode,_summary,compare_metrics,independent_choice,exact_points
from pathology_edge.ki67_localization_experiment import checked,SEEDS,THRESHOLDS,DISTANCES,read_rows,image_proposals
from pathology_edge.ki67_localization import LocalizationGate,predict_localized
from pathology_edge.ki67_center_experiment import loaded_detectors,score_external
from pathology_edge.ki67_experiment import read_json,fresh_json,sha,load_sample,verify_data,summarize


def validate_corrected(original,corrected,shape_hw):
    a=np.asarray(original).reshape(-1,2);b=np.asarray(corrected)
    if b.shape!=a.shape or b.dtype.kind not in 'iuf' or not np.isfinite(b).all() or np.any(b!=np.floor(b)) or np.any(b<0) or np.any(b[:,0]>=shape_hw[1]) or np.any(b[:,1]>=shape_hw[0]):raise ValueError('Invalid corrected coordinate array')
    if np.any(np.linalg.norm(b.astype(np.float64)-a,axis=1)>12+np.sqrt(.5)+1e-8):raise ValueError('Correction exceeds continuous bound and lattice rounding slack')


def independent_test_pass(a,r):
    ac,rc=a['localization'],r['localization']
    if rc['fp']>ac['fp'] or rc['fn']>ac['fn'] or (rc['fp'],rc['fn'])==(ac['fp'],ac['fn']):return False
    if set(a['cases'])!=set(r['cases']):raise ValueError('Case sets differ')
    if any(r['cases'][k]['recall']<.9*v['recall'] for k,v in a['cases'].items()):return False
    return bool(all(r['tumor_recalls'][i]>=a['tumor_recalls'][i] for i in (0,1)))


def audit(root):
    root=Path(root);p=checked(root,selected=True);selection=read_json(root/'selection.json');models=selection['models']
    if [m['seed'] for m in models]!=list(SEEDS):raise ValueError('Missing seed outcome')
    manifest={r['image']:r for r in read_json(Path(p['parent'])/'source-manifest.json') if r['split']=='validation'}
    if len(manifest)!=227:raise ValueError('Validation image count differs')
    verify_data(p['data_dir'],list(manifest.values()));detectors=loaded_detectors(p['prior']);torch.set_num_threads(2)
    trial_count=0;replays=0;outcomes=[]
    for m in models:
        seed=m['seed'];rows=read_rows(root/f'validation-{seed}.json.gz');history=read_rows(root/f'trials-{seed}.json.gz')
        if len(rows)!=227 or {r['image'] for r in rows}!=set(manifest) or any(r['split']!='validation' for r in rows):raise ValueError('Validation scope changed')
        if [h['epoch'] for h in history]!=list(range(1,13)):raise ValueError('Missing epoch')
        lengths=[len(r['points']) for r in rows];offsets=np.cumsum([0,*lengths]);saved=np.load(root/f'validation-output-{seed}.npz',allow_pickle=False)
        if set(saved.files)!={f'{key}_{epoch}' for key in ('scores','xy') for epoch in range(1,13)}:raise ValueError('Missing epoch outputs')
        baseline=_summary(rows,[np.asarray(r['a_points']).reshape(-1,2) for r in rows]);compare_metrics(baseline,m['baseline'])
        compare_metrics(_summary(rows,[np.asarray(r['points']).reshape(-1,2) for r in rows]),m['union'])
        all_trials=[]
        for h in history:
            epoch=h['epoch'];scores=saved[f'scores_{epoch}'].astype(np.float64);xy=saved[f'xy_{epoch}']
            if scores.shape!=(sum(lengths),) or xy.shape!=(sum(lengths),2):raise ValueError('Output lengths differ')
            pieces=[(scores[a:b],xy[a:b]) for a,b in zip(offsets[:-1],offsets[1:])]
            for r,(_,changed) in zip(rows,pieces):validate_corrected(r['points'],changed,(224,224))
            if len(h['trials'])!=42 or {(t['config']['threshold'],t['config']['min_distance']) for t in h['trials']}!={(t,d) for t in THRESHOLDS for d in DISTANCES}:raise ValueError('Trial grid changed')
            cached={d:[independent_decode(changed,s,dict(threshold=0,min_distance=d)) for s,changed in pieces] for d in DISTANCES}
            for trial in h['trials']:
                cfg=trial['config'];decoded=[pts[sc>=cfg['threshold']] for pts,sc in cached[cfg['min_distance']]]
                compare_metrics(_summary(rows,decoded),trial);all_trials.append(trial);trial_count+=1
            if sum(independent_choice([t],baseline,p['floors']) is not None for t in h['trials'])!=h['feasible_trials']:raise ValueError('Epoch eligibility differs')
        selected=independent_choice(all_trials,baseline,p['floors'])
        if selected!=m['selected']:raise ValueError('Selected configuration differs')
        if m['feasible_trials']!=sum(h['feasible_trials'] for h in history):raise ValueError('Seed eligibility differs')
        diagnostic=max(all_trials,key=lambda t:(t['case_macro_f1'],t['case_macro_recall'],-t['epoch'],t['config']['threshold'],t['config']['min_distance']))
        if diagnostic!=m['diagnostic']:raise ValueError('Diagnostic configuration differs')
        target=selected or diagnostic;epoch=target['epoch'];gate=LocalizationGate();gate.load_state_dict(torch.load(root/(m['checkpoint'] or m['diagnostic_checkpoint']),weights_only=True,map_location='cpu'))
        pool=read_json(root/f'pools-{seed}.json')
        if pool['normalization_split']!='train' or not np.array_equal(gate.meta_mean.numpy(),np.asarray(pool['metadata_mean'],dtype=np.float32)) or not np.array_equal(gate.meta_scale.numpy(),np.asarray(pool['metadata_scale'],dtype=np.float32)):raise ValueError('Training normalizer differs')
        original_decoded=[]
        for index,r in enumerate(rows):
            rgb,gt,gc=load_sample(p['data_dir'],manifest[r['image']]);exact_points(gt,r['gt_points'])
            if gc.tolist()!=r['gt_classes']:raise ValueError('Ground truth classes differ')
            found=image_proposals(rgb,*detectors[seed]);exact_points(found['points'],r['points']);exact_points(found['a_points'],r['a_points'])
            if found['sources'].tolist()!=r['sources'] or not np.array_equal(found['metadata'],np.asarray(r['metadata'],dtype=np.float32)):raise ValueError('Image-only proposal metadata differs')
            prediction=predict_localized(rgb,found['points'],found['metadata'],gate);a,b=offsets[index:index+2]
            if not np.array_equal(prediction['scores'],saved[f'scores_{epoch}'][a:b].astype(np.float64)):raise ValueError('Checkpoint scores differ')
            exact_points(prediction['corrected_xy'],saved[f'xy_{epoch}'][a:b])
            if np.any(np.linalg.norm(prediction['offsets'],axis=1)>12+1e-5):raise ValueError('Continuous correction out of bounds')
            independent=np.rint(found['points'].astype(np.float64)+prediction['offsets']);independent[:,0]=np.clip(independent[:,0],0,223);independent[:,1]=np.clip(independent[:,1],0,223);exact_points(independent,prediction['corrected_xy'])
            original_decoded.append(independent_decode(found['points'],prediction['scores'],target['config'])[0]);replays+=1
        compare_metrics(_summary(rows,original_decoded),m['scorer_without_offsets'])
        outcomes.append(dict(seed=seed,eligible=selected is not None,trials=504));print('AUDITED',seed,flush=True)
    eligible=[m for m in models if m['selected'] is not None];evaluations=0;test_decisions={}
    if not eligible:
        for tag in ('internal','external'):
            skipped=read_json(root/(tag+'-not-run.json'))
            if skipped['new_inference_images']!=0 or (root/(tag+'-started.json')).exists():raise ValueError('Ineligible model evaluated holdout')
    for m in eligible:
        for tag in ('internal','external'):
            folder=root/f"seed-{m['seed']}"/tag;proposals=read_rows(folder/'proposals.json.gz');arms={}
            for arm in ('A','U','S','R'):
                dest=folder/arm;rows=read_rows(dest/'predictions.json.gz');result=read_json(dest/'results.json');arms[arm]=rows
                if len(rows)!=(133 if tag=='external' else 407) or sha(dest/'predictions.json.gz')!=result['predictions_sha256'] or result['selection_lock_sha256']!=sha(root/'selection-lock.json'):raise ValueError('Evaluation scope/hash mismatch')
                if len(proposals)!=len(rows) or [r['image'] for r in rows]!=[r['image'] for r in proposals]:raise ValueError('Proposal correspondence differs')
                for r,pr in zip(rows,proposals):
                    validate_corrected(pr['points'],np.asarray(pr['corrected_xy']).reshape(-1,2),(640,640) if tag=='external' else (224,224))
                    if arm=='U':exact_points(r['points'],pr['points'])
                    if arm in ('S','R'):
                        point=pr['points'] if arm=='S' else pr['corrected_xy'];exact_points(r['points'],independent_decode(point,np.asarray(pr['scores']),m['selected']['config'])[0])
                for name,expected in result['classifiers'].items():compare_metrics(score_external(rows,name) if tag=='external' else summarize(rows,name),expected);evaluations+=1
            if tag=='internal':
                a=_summary(arms['A'],[np.asarray(r['points']).reshape(-1,2) for r in arms['A']]);r=_summary(arms['R'],[np.asarray(v['points']).reshape(-1,2) for v in arms['R']]);test_decisions[m['seed']]=independent_test_pass(a,r)
    stability=read_json(root/'stability.json');expected=[bool(test_decisions.get(seed,False)) for seed in SEEDS]
    if [r['seed'] for r in stability['seeds']]!=list(SEEDS) or [r['test_passed'] for r in stability['seeds']]!=expected or stability['test_passes']!=sum(expected) or stability['denominator']!=3 or stability['all_three_test_passed']!=all(expected):raise ValueError('Stability denominator/decision differs')
    return dict(all_checks_passed=True,trial_checks=trial_count,checkpoint_and_proposal_replay_images=replays,evaluation_classifier_summaries=evaluations,eligible_seeds=len(eligible),test_passes=sum(expected),stability_denominator=3,seeds=outcomes,selection_lock_sha256=sha(root/'selection-lock.json'),scope=p['scope'])

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);a=parser.parse_args();report=audit(a.output);fresh_json(a.output/'audit.json',report);print(json.dumps(report),flush=True)
