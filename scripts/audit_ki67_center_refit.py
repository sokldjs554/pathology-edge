#!/usr/bin/env python3
"""Independent refit selection, raw references and native checkpoint replay audit."""
import argparse
import io
import json
from pathlib import Path
import sys
import numpy as np
from PIL import Image
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from audit_ki67_union import independent_decode,_summary,compare_metrics,independent_choice,exact_points
from audit_ki67_localization import independent_test_pass
from pathology_edge.ki67_center_refit import checked,SEEDS,THRESHOLDS,DISTANCES,FLOORS,EPOCHS
from pathology_edge.ki67_centers import CenterDetector,peak_candidates
from pathology_edge.ki67_center_experiment import loaded_detectors,score_external
from pathology_edge.ki67_union_experiment import read_rows
from pathology_edge.ki67_experiment import read_json,fresh_json,sha,load_sample,verify_data,load_models,summarize
from pathology_edge.ki67_cnn import classify_centers
from pathology_edge.ki67_external import fetch_entry,download_url,validate_external_entries


def validate_saved_peaks(points,scores,offsets,images,shape):
    points,scores,offsets=map(np.asarray,(points,scores,offsets))
    if points.ndim!=2 or points.shape[1]!=2 or points.dtype.kind not in 'iuf' or not np.isfinite(points).all() or np.any(points!=np.floor(points)) or np.any(points<0) or np.any(points[:,0]>=shape[1]) or np.any(points[:,1]>=shape[0]):raise ValueError('Invalid native peak coordinates')
    if scores.shape!=(len(points),) or scores.dtype.kind not in 'iuf' or not np.isfinite(scores).all() or np.any(scores.astype(np.float64)<.01) or np.any(scores>1):raise ValueError('Invalid peak scores')
    if offsets.shape!=(images+1,) or offsets.dtype.kind not in 'iu' or offsets[0]!=0 or offsets[-1]!=len(points) or np.any(offsets[1:]<offsets[:-1]):raise ValueError('Invalid image peak offsets')
    for a,b in zip(offsets[:-1],offsets[1:]):
        if len(np.unique(points[a:b],axis=0))!=b-a:raise ValueError('Duplicate peaks inside one image')


def verify_reference(row,metadata,gt,gc):
    if row['image']!=metadata['image'] or ('case_id' in metadata and row.get('case_id')!=metadata['case_id']):raise ValueError('Reference image/case differs')
    exact_points(row['gt_points'],gt)
    if row['gt_classes']!=np.asarray(gc).tolist():raise ValueError('Reference class differs')


def refit_choice(trials,baseline):
    return independent_choice([t for t in trials if t['epoch']>0],baseline,FLOORS)


def replay_peaks(rgb,model):
    model.eval()
    if not all(torch.isfinite(t).all() for t in model.state_dict().values()):raise ValueError('Nonfinite checkpoint')
    inputs=torch.from_numpy(rgb.transpose(2,0,1).copy()).float().unsqueeze(0)/255
    with torch.inference_mode():heat=torch.sigmoid(model(inputs))[0,0].cpu().numpy()
    points,scores=peak_candidates(heat);keep=scores>=.01
    return points[keep],scores[keep]


def load_checkpoint(path):
    model=CenterDetector();model.load_state_dict(torch.load(path,weights_only=True,map_location='cpu'));return model.eval()


def audit(root):
    root=Path(root);p=checked(root,selected=True);models=read_json(root/'selection.json')['models'];torch.set_num_threads(2)
    if [m['seed'] for m in models]!=list(SEEDS):raise ValueError('All three seed outcomes required')
    manifest={r['image']:r for r in read_json(Path(p['parent'])/'source-manifest.json') if r['split']=='validation'}
    if len(manifest)!=227:raise ValueError('Validation scope changed')
    verify_data(p['data_dir'],list(manifest.values()));images={name:load_sample(p['data_dir'],r) for name,r in manifest.items()};initial=loaded_detectors(p['prior'])
    trials_checked=0;replays=0;outcomes=[]
    for m in models:
        seed=m['seed'];rows=read_rows(root/f'validation-{seed}.json.gz');history=read_rows(root/f'trials-{seed}.json.gz');saved=np.load(root/f'validation-peaks-{seed}.npz',allow_pickle=False)
        if len(rows)!=227 or {r['image'] for r in rows}!=set(manifest) or any(r['split']!='validation' for r in rows):raise ValueError('Validation set changed')
        if [h['epoch'] for h in history]!=list(range(EPOCHS+1)) or set(saved.files)!={f'{k}_{e}' for e in range(EPOCHS+1) for k in ('points','scores','offsets')}:raise ValueError('Missing epoch evidence')
        for r in rows:
            _,gt,gc=images[r['image']];verify_reference(r,manifest[r['image']],gt,gc)
        baseline=_summary(rows,[np.asarray(r['a_points']).reshape(-1,2) for r in rows]);compare_metrics(baseline,m['baseline'])
        old=next(v for v in p['initial_models'] if v['seed']==seed)
        if not np.isclose(baseline['case_macro_f1'],old['validation_case_macro_f1'],rtol=0,atol=1e-12) or not np.isclose(baseline['case_macro_recall'],old['validation_case_macro_recall'],rtol=0,atol=1e-12):raise ValueError('Original baseline differs')
        all_trials=[]
        for h in history:
            epoch=h['epoch'];points=saved[f'points_{epoch}'];scores=saved[f'scores_{epoch}'].astype(np.float64);offsets=saved[f'offsets_{epoch}'];validate_saved_peaks(points,scores,offsets,len(rows),(224,224))
            pieces=[(points[a:b],scores[a:b]) for a,b in zip(offsets[:-1],offsets[1:])]
            if len(h['trials'])!=36 or any(t['epoch']!=epoch or t['split']!='validation' for t in h['trials']) or {(t['config']['threshold'],t['config']['min_distance']) for t in h['trials']}!={(t,d) for t in THRESHOLDS for d in DISTANCES}:raise ValueError('Trial grid changed')
            cache={d:[independent_decode(xy,sc,dict(threshold=.01,min_distance=d)) for xy,sc in pieces] for d in DISTANCES}
            for t in h['trials']:
                cfg=t['config'];decoded=[xy[sc>=cfg['threshold']] for xy,sc in cache[cfg['min_distance']]];compare_metrics(_summary(rows,decoded),t);trials_checked+=1;all_trials.append(t)
            if sum(refit_choice([t],baseline) is not None for t in h['trials'])!=h['feasible_trials']:raise ValueError('Epoch eligibility differs')
        chosen=refit_choice(all_trials,baseline)
        if chosen!=m['selected'] or sum(h['feasible_trials'] for h in history)!=m['feasible_trials']:raise ValueError('Chosen refit/feasibility differs')
        key=lambda t:(t['case_macro_f1'],t['case_macro_recall'],-t['epoch'],t['config']['threshold'],t['config']['min_distance'])
        diagnostic=max(all_trials,key=key)
        if diagnostic!=m['diagnostic'] or max(history[0]['trials'],key=key)!=m['epoch0_diagnostic']:raise ValueError('Diagnostic choice differs')
        target=chosen or diagnostic;model=load_checkpoint(root/(m['checkpoint'] or m['diagnostic_checkpoint']));original,config=initial[seed]
        if sha(Path(p['prior'])/f'detector-{seed}.pt')!=m['initial_checkpoint_sha256'] or config!=m['a_config']:raise ValueError('Initial detector changed')
        for index,r in enumerate(rows):
            rgb,_,_=images[r['image']]
            for epoch,network in ((0,original),(target['epoch'],model)):
                xy,sc=replay_peaks(rgb,network);a,b=saved[f'offsets_{epoch}'][index:index+2];exact_points(xy,saved[f'points_{epoch}'][a:b])
                if not np.array_equal(sc,saved[f'scores_{epoch}'][a:b].astype(np.float64)):raise ValueError('Native checkpoint score replay differs')
                if epoch==0:exact_points(independent_decode(xy,sc,config)[0],r['a_points'])
                replays+=1
        resume=torch.load(root/f'final-resume-{seed}.pt',weights_only=True,map_location='cpu')
        if resume['completed_additional_epochs']!=EPOCHS or not resume['optimizer']['state'] or any(float(s['step'])!=EPOCHS*87 for s in resume['optimizer']['state'].values()) or resume['optimizer']['param_groups'][0]['lr']!=.001:raise ValueError('Final optimizer history differs')
        if not all(torch.isfinite(t).all() for t in resume['model'].values()) or resume['torch_rng_state'].dtype!=torch.uint8:raise ValueError('Invalid saved final state')
        rng=np.random.default_rng();rng.bit_generator.state=read_json(root/f'final-rng-{seed}.json')
        outcomes.append(dict(seed=seed,eligible=chosen is not None,trials=900,epoch0_control_trials=36,eligible_epoch_trials=864));print('AUDITED',seed,flush=True)
    eligible=[m for m in models if m['selected'] is not None];evaluation_summaries=0;holdout_replays=0;decisions={}
    if not eligible:
        for tag in ('internal','external'):
            if read_json(root/(tag+'-not-run.json'))['new_inference_images']!=0 or (root/(tag+'-started.json')).exists():raise ValueError('Ineligible run accessed holdouts')
    else:
        classifiers=load_models(p['parent'],read_json(Path(p['parent'])/'selection-lock.json'));b_models={m['seed']:load_checkpoint(root/m['checkpoint']) for m in eligible}
        for tag in ('internal','external'):
            if read_json(root/(tag+'-started.json'))['selection_lock_sha256']!=sha(root/'selection-lock.json'):raise ValueError('Evaluation lock differs')
            stored={};results={}
            for m in eligible:
                seed=m['seed'];stored[seed]={};results[seed]={}
                for arm in ('A','B'):
                    folder=root/f'seed-{seed}'/tag/arm;rows=read_rows(folder/'predictions.json.gz');r=read_json(folder/'results.json')
                    if sha(folder/'predictions.json.gz')!=r['predictions_sha256'] or r['selection_lock_sha256']!=sha(root/'selection-lock.json') or len(rows)!=(133 if tag=='external' else 407):raise ValueError('Evaluation counts/hash differ')
                    if len({v['image'] for v in rows})!=len(rows) or set(r['classifiers'])!=set(classifiers):raise ValueError('Evaluation IDs/classifiers differ')
                    stored[seed][arm]=rows;results[seed][arm]=r
            if tag=='internal':
                refs=[r for r in read_json(Path(p['parent'])/'source-manifest.json') if r['split']=='test'];verify_data(p['data_dir'],refs)
            else:
                previous=Path(p['external']);refs=read_json(previous/'private-predictions.json');entries={r['name']:r for r in read_json(previous/'entries.json')};inputs={r['name']:r for r in read_json(previous/'input-manifest.json')};names=validate_external_entries(list(entries.values()));refmap={r['image']:r for r in refs}
                if len(refs)!=133 or set(refmap)!=set(names):raise ValueError('External canonical reference differs')
                refs=[refmap[n] for n in names];url=download_url()
            for seed,arms in stored.items():
                if any([r['image'] for r in rows]!=[r['image'] for r in refs] for rows in arms.values()):raise ValueError('Authoritative evaluation image correspondence differs')
            for index,ref in enumerate(refs):
                if tag=='internal':rgb,gt,gc=load_sample(p['data_dir'],ref)
                else:
                    raw,meta=fetch_entry(url,entries[ref['image']])
                    if meta['sha256']!=inputs[ref['image']]['sha256']:raise ValueError('External image bytes differ')
                    image=Image.open(io.BytesIO(raw))
                    if image.mode!='RGB' or image.size!=(640,640):raise ValueError('External geometry differs')
                    rgb=np.asarray(image);gt=np.asarray(ref['gt_points']).reshape(-1,2);gc=np.asarray(ref['gt_classes'])
                for m in eligible:
                    seed=m['seed']
                    for arm,network,config in [('A',initial[seed][0],initial[seed][1]),('B',b_models[seed],m['selected']['config'])]:
                        row=stored[seed][arm][index];verify_reference(row,ref,gt,gc);xy,sc=replay_peaks(rgb,network);points=independent_decode(xy,sc,config)[0];exact_points(points,row['points'])
                        if set(row['classes'])!=set(classifiers):raise ValueError('Classifier set differs')
                        for name,classifier in classifiers.items():
                            if classify_centers(rgb,points,classifier).argmax(1).tolist()!=row['classes'][name]:raise ValueError('New-center classification replay differs')
                        holdout_replays+=1
            for seed,arms in stored.items():
                for arm,rows in arms.items():
                    for name,expected in results[seed][arm]['classifiers'].items():compare_metrics(score_external(rows,name) if tag=='external' else summarize(rows,name),expected);evaluation_summaries+=1
                if tag=='internal':decisions[seed]=independent_test_pass(_summary(arms['A'],[np.asarray(r['points']).reshape(-1,2) for r in arms['A']]),_summary(arms['B'],[np.asarray(r['points']).reshape(-1,2) for r in arms['B']]))
    stability=read_json(root/'stability.json');expected=[bool(decisions.get(seed,False)) for seed in SEEDS]
    if [r['seed'] for r in stability['seeds']]!=list(SEEDS) or [r['test_passed'] for r in stability['seeds']]!=expected or stability['denominator']!=3 or stability['test_passes']!=sum(expected) or stability['all_three_test_passed']!=all(expected):raise ValueError('Three-seed stability differs')
    return dict(all_checks_passed=True,trial_checks=trials_checked,validation_checkpoint_replay_images=replays,holdout_pipeline_replay_images=holdout_replays,evaluation_classifier_summaries=evaluation_summaries,eligible_seeds=len(eligible),test_passes=sum(expected),stability_denominator=3,seeds=outcomes,selection_lock_sha256=sha(root/'selection-lock.json'),external_reference_scope='Bound to previously verified/hash-locked canonical points, not a new HDF5 annotation audit',scope=p['scope'])

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);a=parser.parse_args();report=audit(a.output);fresh_json(a.output/'audit.json',report);print(json.dumps(report),flush=True)
