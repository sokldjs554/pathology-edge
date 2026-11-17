#!/usr/bin/env python3
"""Independent complete-grid selection and original-pixel/checkpoint audit."""
import argparse
from collections import defaultdict
import hashlib
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
from audit_ki67_center_refit import validate_saved_peaks,verify_reference,replay_peaks
from audit_ki67_localization import independent_test_pass
from pathology_edge.ki67_normalized_experiment import checked,primary_models,job_name,WIDTHS,SEEDS,THRESHOLDS,DISTANCES,FLOORS,EPOCHS
from pathology_edge.ki67_normalized_centers import NormalizedCenterDetector
from pathology_edge.ki67_normalized_pipeline import checked_pipeline,ARMS
from pathology_edge.ki67_center_experiment import loaded_detectors,score_external
from pathology_edge.ki67_union_experiment import read_rows
from pathology_edge.ki67_experiment import read_json,fresh_json,sha,verify_hashes,load_sample,verify_data,load_models,summarize
from pathology_edge.ki67_cnn import classify_centers
from pathology_edge.ki67_evaluation import match_points,count_metrics
from pathology_edge.ki67_external import fetch_entry,download_url,validate_external_entries


def independent_classifier_choice(a,scores,reference,ids):
    def valid(s):
        cases=s['per_case'];seen=[r['case_id'] for r in cases]
        return (len(seen)==len(ids) and len(set(seen))==len(seen) and set(seen)==set(ids) and s['case_ratio_valid']==len(ids)
            and all(r['ratio_error_pp'] is not None and np.isfinite(r['ratio_error_pp']) for r in cases)
            and np.isfinite(s['macro_f1']) and s['case_ratio_mae_pp'] is not None and np.isfinite(s['case_ratio_mae_pp']))
    candidates=[n for n in ARMS if ids and valid(a) and valid(scores[n]) and scores[n]['macro_f1']>a['macro_f1'] and scores[n]['case_ratio_mae_pp']<=a['case_ratio_mae_pp']]
    return (sorted(candidates,key=lambda n:(-scores[n]['macro_f1'],scores[n]['case_ratio_mae_pp'],ARMS.index(n)))[0],True) if candidates else (reference,False)


def validate_history(history):
    if [h['epoch'] for h in history]!=list(range(1,25)):raise ValueError('Expected all24 completed epochs')
    expected={(t,d) for t in THRESHOLDS for d in DISTANCES}
    for h in history:
        trials=h['trials']
        if not np.isfinite(h['train_loss']) or len(trials)!=36 or {(t['config']['threshold'],t['config']['min_distance']) for t in trials}!=expected or any(t['epoch']!=h['epoch'] or t['split']!='validation' for t in trials):raise ValueError('Epoch trial grid/loss changed')


def cached_summary(rows,points,cache):
    cases=defaultdict(lambda:np.zeros(3,dtype=np.int64));matches=np.zeros(4,dtype=np.int64);totals=np.zeros(4,dtype=np.int64)
    for i,(r,xy) in enumerate(zip(rows,points)):
        xy=np.asarray(xy).reshape(-1,2);key=(i,xy.astype(np.int64).tobytes())
        if key not in cache:
            gt=np.asarray(r['gt_points']).reshape(-1,2);gc=np.asarray(r['gt_classes'],dtype=int);pairs=match_points(xy,gt,6)
            cache[key]=(np.array([len(pairs),len(xy)-len(pairs),len(gt)-len(pairs)]),np.bincount([gc[j] for _,j in pairs],minlength=4),np.bincount(gc,minlength=4))
        counts,matched,total=cache[key];cases[r['case_id']]+=counts;matches+=matched;totals+=total
    cc={k:count_metrics(*v) for k,v in sorted(cases.items())}
    return dict(localization=count_metrics(*np.sum(list(cases.values()),axis=0)),cases=cc,case_macro_f1=float(np.mean([v['f1'] for v in cc.values()])),case_macro_recall=float(np.mean([v['recall'] for v in cc.values()])),tumor_recalls=[float(matches[k]/totals[k]) if totals[k] else 0. for k in (0,1)],matched_by_true_class=matches.tolist(),true_class_counts=totals.tolist())


def network(path,width):
    model=NormalizedCenterDetector(width);model.load_state_dict(torch.load(path,weights_only=True,map_location='cpu'),strict=True);return model.eval()


def audit_worker(root,width,seed):
    root=Path(root);p=checked(root);dest=root/job_name(width,seed);complete=read_json(dest/'complete.json')
    if complete['protocol_sha256']!=sha(root/'protocol.json'):raise ValueError('Worker protocol differs')
    verify_hashes(dest,complete['evidence_hashes']);m=read_json(dest/'result.json')
    if (m['width'],m['seed'],m['additional_epochs'])!=(width,seed,24):raise ValueError('Worker identity/completion differs')
    torch.set_num_threads(1);torch.manual_seed(seed);initial=NormalizedCenterDetector(width)
    hashes={k:hashlib.sha256(v.detach().numpy().tobytes()).hexdigest() for k,v in initial.state_dict().items()}
    if hashes!=read_json(dest/'initial-tensors.json'):raise ValueError('Fresh initialization differs')
    if sum(t.numel() for t in initial.parameters())!=m['parameter_count']:raise ValueError('Parameter count differs')
    manifest={r['image']:r for r in read_json(Path(p['parent'])/'source-manifest.json') if r['split']=='validation'}
    verify_data(p['data_dir'],list(manifest.values()));images={name:load_sample(p['data_dir'],r) for name,r in manifest.items()}
    rows=read_rows(dest/'validation.json.gz');history=read_rows(dest/'trials.json.gz');validate_history(history);saved=np.load(dest/'validation-peaks.npz',allow_pickle=False)
    if len(rows)!=227 or {r['image'] for r in rows}!=set(manifest) or any(r['split']!='validation' for r in rows):raise ValueError('Validation membership differs')
    if set(saved.files)!={f'{k}_{e}' for e in range(1,25) for k in ('points','scores','offsets')}:raise ValueError('Missing raw epoch evidence')
    for r in rows:
        _,gt,gc=images[r['image']];verify_reference(r,manifest[r['image']],gt,gc)
    baseline=_summary(rows,[np.asarray(r['a_points']).reshape(-1,2) for r in rows]);compare_metrics(baseline,m['baseline'])
    old=next(v for v in p['initial_models'] if v['seed']==seed)
    for key in ('case_macro_f1','case_macro_recall'):
        if not np.isclose(baseline[key],old['validation_'+key],rtol=0,atol=1e-12):raise ValueError('Original baseline differs')
    all_trials=[]
    for h in history:
        epoch=h['epoch'];points=saved[f'points_{epoch}'];scores=saved[f'scores_{epoch}'].astype(np.float64);offsets=saved[f'offsets_{epoch}'];validate_saved_peaks(points,scores,offsets,len(rows),(224,224))
        pieces=[(points[a:b],scores[a:b]) for a,b in zip(offsets[:-1],offsets[1:])];cache={}
        decoded={d:[independent_decode(xy,sc,dict(threshold=.01,min_distance=d)) for xy,sc in pieces] for d in DISTANCES}
        for t in h['trials']:
            cfg=t['config'];pts=[xy[sc>=cfg['threshold']] for xy,sc in decoded[cfg['min_distance']]];compare_metrics(cached_summary(rows,pts,cache),t);all_trials.append(t)
        if sum(independent_choice([t],baseline,FLOORS) is not None for t in h['trials'])!=h['feasible_trials']:raise ValueError('Epoch feasibility differs')
    chosen=independent_choice(all_trials,baseline,FLOORS)
    if chosen!=m['selected'] or sum(h['feasible_trials'] for h in history)!=m['feasible_trials']:raise ValueError('Selected epoch/config differs')
    diagnostic=max(all_trials,key=lambda t:(t['case_macro_f1'],t['case_macro_recall'],-t['epoch'],t['config']['threshold'],t['config']['min_distance']))
    if diagnostic!=m['diagnostic']:raise ValueError('Diagnostic selection differs')
    original,config=loaded_detectors(p['prior'])[seed]
    if config!=m['a_config']:raise ValueError('Original config differs')
    replays=0
    for i,r in enumerate(rows):
        torch.set_num_threads(2);xy,sc=replay_peaks(images[r['image']][0],original);exact_points(independent_decode(xy,sc,config)[0],r['a_points']);replays+=1
    torch.set_num_threads(1)
    targets=[(diagnostic,'diagnostic.pt')]+([(chosen,'selected.pt')] if chosen is not None else [])
    for target,filename in targets:
        model=network(dest/filename,width);epoch=target['epoch']
        for i,r in enumerate(rows):
            xy,sc=replay_peaks(images[r['image']][0],model);a,b=saved[f'offsets_{epoch}'][i:i+2];exact_points(xy,saved[f'points_{epoch}'][a:b])
            if not np.array_equal(sc,saved[f'scores_{epoch}'][a:b].astype(np.float64)):raise ValueError('Checkpoint scores differ')
            replays+=1
    resume=torch.load(dest/'final-resume.pt',weights_only=True,map_location='cpu')
    if resume['epochs']!=24 or not resume['optimizer']['state'] or any(float(s['step'])!=24*87 for s in resume['optimizer']['state'].values()) or resume['optimizer']['param_groups'][0]['lr']!=.001:raise ValueError('Final optimizer history differs')
    if not all(torch.isfinite(t).all() for t in resume['model'].values()) or resume['torch_rng_state'].dtype!=torch.uint8:raise ValueError('Invalid final state')
    rng=np.random.default_rng();rng.bit_generator.state=read_json(dest/'final-rng.json');verify_hashes(dest,complete['evidence_hashes']);checked(root)
    sources=[Path(__file__),Path(__file__).with_name('audit_ki67_union.py'),Path(__file__).with_name('audit_ki67_center_refit.py')]
    report=dict(width=width,seed=seed,all_checks_passed=True,trials=len(all_trials),checkpoint_replay_images=replays,eligible=chosen is not None,complete_sha256=sha(dest/'complete.json'),protocol_sha256=sha(root/'protocol.json'),audit_sources={str(f.resolve()):sha(f) for f in sources})
    fresh_json(dest/'audit-worker.json',report);(dest/'audit-worker.sha256').write_text(sha(dest/'audit-worker.json')+'\n');print('AUDITED',width,seed,flush=True);return report


def audit_pipeline(root):
    root=Path(root);p,models,choices=checked_pipeline(root);workers=[]
    for width in WIDTHS:
        for seed in SEEDS:
            dest=root/job_name(width,seed);a=read_json(dest/'audit-worker.json')
            if sha(dest/'audit-worker.json')!=(dest/'audit-worker.sha256').read_text().strip() or a['complete_sha256']!=sha(dest/'complete.json') or a['protocol_sha256']!=sha(root/'protocol.json') or (a['width'],a['seed'])!=(width,seed) or not a['all_checks_passed']:raise ValueError('Worker audit changed')
            verify_hashes('/',a['audit_sources']);workers.append(a)
    eligible=[m for m in models if m['selected'] is not None];checks=replays=0;decisions={}
    if not eligible:
        for tag in ('internal','external'):
            if read_json(root/(tag+'-not-run.json'))['new_inference_images']!=0 or (root/(tag+'-started.json')).exists():raise ValueError('Ineligible holdout was evaluated')
    else:
        original=loaded_detectors(p['prior']);networks={m['seed']:network(root/job_name(16,m['seed'])/'selected.pt',16) for m in eligible};classifiers=load_models(p['parent'],read_json(Path(p['parent'])/'selection-lock.json'))
        for tag in ('validation','internal','external'):
            stored={};scores={}
            for m in eligible:
                seed=m['seed'];folder=root/'pipeline-validation'/str(seed) if tag=='validation' else root/'pipeline-heldout'/str(seed)/tag
                stored[seed]={arm:read_rows(folder/(arm+'.json.gz')) for arm in ('A','B')};scores[seed]=read_json(folder/'scores.json')
            if tag!='external':
                refs=[r for r in read_json(Path(p['parent'])/'source-manifest.json') if r['split']==('validation' if tag=='validation' else 'test')];verify_data(p['data_dir'],refs)
            else:
                previous=Path(p['external']);refmap={r['image']:r for r in read_json(previous/'private-predictions.json')};entries={r['name']:r for r in read_json(previous/'entries.json')};inputs={r['name']:r for r in read_json(previous/'input-manifest.json')};refs=[refmap[n] for n in validate_external_entries(list(entries.values()))];url=download_url()
            for seed,arms in stored.items():
                if any([r['image'] for r in rows]!=[r['image'] for r in refs] for rows in arms.values()):raise ValueError('Actual evaluation membership/order differs')
            for i,ref in enumerate(refs):
                if tag!='external':rgb,gt,gc=load_sample(p['data_dir'],ref)
                else:
                    raw,meta=fetch_entry(url,entries[ref['image']])
                    if meta['sha256']!=inputs[ref['image']]['sha256']:raise ValueError('External original changed')
                    image=Image.open(io.BytesIO(raw))
                    if image.mode!='RGB' or image.size!=(640,640):raise ValueError('External geometry changed')
                    rgb=np.asarray(image);gt=np.asarray(ref['gt_points']).reshape(-1,2);gc=np.asarray(ref['gt_classes'])
                for m in eligible:
                    seed=m['seed']
                    for arm,model,config in [('A',original[seed][0],original[seed][1]),('B',networks[seed],m['selected']['config'])]:
                        torch.set_num_threads(2 if arm=='A' else 1);xy,sc=replay_peaks(rgb,model);pts=independent_decode(xy,sc,config)[0];row=stored[seed][arm][i];verify_reference(row,ref,gt,gc);exact_points(pts,row['points']);torch.set_num_threads(1)
                        if set(row['classes'])!=set(ARMS):raise ValueError('Classifier set changed')
                        for name,classifier in classifiers.items():
                            if classify_centers(rgb,pts,classifier).argmax(1).tolist()!=row['classes'][name]:raise ValueError('Actual-center classifier replay differs')
                        replays+=1
            for seed,arms in stored.items():
                for arm,rows in arms.items():
                    for name in ARMS:compare_metrics(score_external(rows,name) if tag=='external' else summarize(rows,name),scores[seed][arm][name]);checks+=1
                c=choices[seed];reference=ARMS[1+list(SEEDS).index(seed)];ids=sorted({r['case_id'] for r in refs}) if tag!='external' else []
                if tag=='validation':
                    picked,passed=independent_classifier_choice(scores[seed]['A'][reference],scores[seed]['B'],reference,ids)
                    if picked!=c['selected_classifier'] or passed!=c['validation_pipeline_passed']:raise ValueError('Validation classifier choice differs')
                if tag=='internal':
                    detection=independent_test_pass(_summary(arms['A'],[np.asarray(r['points']).reshape(-1,2) for r in arms['A']]),_summary(arms['B'],[np.asarray(r['points']).reshape(-1,2) for r in arms['B']]))
                    a=scores[seed]['A'][reference];b=scores[seed]['B'][c['selected_classifier']];_,pipe=independent_classifier_choice(a,{n:b for n in ARMS},reference,ids);decisions[seed]=(detection,pipe)
    stability=read_json(root/'stability.json');expected=[decisions.get(seed,(False,False)) for seed in SEEDS]
    if [r['seed'] for r in stability['seeds']]!=list(SEEDS) or [(r['test_passed'],r['pipeline_passed']) for r in stability['seeds']]!=expected or stability['denominator']!=3 or stability['test_passes']!=sum(r[0] for r in expected) or stability['pipeline_passes']!=sum(r[1] for r in expected):raise ValueError('Three-seed stability summary differs')
    checked_pipeline(root)
    return dict(all_checks_passed=True,trial_checks=sum(w['trials'] for w in workers),validation_checkpoint_replay_images=sum(w['checkpoint_replay_images'] for w in workers),actual_center_pipeline_replay_images=replays,classifier_summaries=checks,eligible_seeds=len(eligible),denominator=3,workers=workers,
                test_passes=stability['test_passes'],pipeline_passes=stability['pipeline_passes'],selection_lock_sha256=sha(root/'selection-lock.json'),classifier_lock_sha256=sha(root/'classifier-lock.json'))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True,type=Path);parser.add_argument('--worker',nargs=2,type=int,metavar=('WIDTH','SEED'));args=parser.parse_args()
    if args.worker:result=audit_worker(args.output,*args.worker)
    else:result=audit_pipeline(args.output);fresh_json(args.output/'audit.json',result)
    print(json.dumps(result),flush=True)
