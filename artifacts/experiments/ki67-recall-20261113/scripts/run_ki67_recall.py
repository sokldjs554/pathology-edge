#!/usr/bin/env python3
"""Validation-only decoder diagnosis/selection, followed by frozen re-evaluation."""
from collections import defaultdict
from datetime import datetime, timezone
import argparse
import gzip
import io
import json
from pathlib import Path
import subprocess
import sys
import numpy as np
from PIL import Image
import torch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from pathology_edge.ki67_centers import peak_candidates,decode_candidates,predict_centers
from pathology_edge.ki67_center_diagnostics import diagnose_candidates,select_recall_configuration,class_accounting
from pathology_edge.ki67_center_experiment import loaded_detectors,score_external
from pathology_edge.ki67_experiment import read_json,fresh_json,sha,verify_hashes,verify_data,load_sample,load_models,summarize,validate_manifest
from pathology_edge.ki67_detection import detect_centers
from pathology_edge.ki67_evaluation import match_points,count_metrics
from pathology_edge.ki67_external import fetch_entry,download_url,validate_external_entries

THRESHOLDS=(.01,.02,.03,.05,.075,.1,.2,.3,.5)
DISTANCES=(4,6,8)
SEEDS=(20261117,20261118,20261119)
ROOT=Path(__file__).resolve().parents[1]


def utc():return datetime.now(timezone.utc).isoformat()


def write_rows(path,rows):
    with Path(path).open('xb') as f:
        with gzip.GzipFile(fileobj=f,mode='wb',mtime=0) as g:
            g.write(json.dumps(rows,separators=(',',':'),allow_nan=False).encode())


def read_rows(path):
    with gzip.open(path,'rt') as f:return json.load(f)


def prepare(prior,output):
    prior=Path(prior).resolve();output=Path(output).resolve()
    old=read_json(prior/'protocol.json');parent=Path(old['parent'])
    models=loaded_detectors(prior)
    if tuple(models)!=SEEDS:raise ValueError('Expected all three fixed seeds')
    inputs={str(prior/n):sha(prior/n) for n in ('protocol.json','selection.json','selection-lock.json',*(f'detector-{s}.pt' for s in SEEDS))}
    inputs.update(old['input_hashes'])
    sources=[ROOT/'scripts/run_ki67_recall.py',*sorted((ROOT/'src/pathology_edge').glob('*.py'))]
    rows=read_json(parent/'source-manifest.json')
    validate_manifest(rows,read_json(parent/'split.json')['assignment'])
    output.mkdir(parents=True,exist_ok=False)
    p=dict(created_utc=utc(),schema='recall-decoder.v1',prior=str(prior),parent=str(parent),external=old['external'],data_dir=old['data_dir'],
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        input_hashes=inputs,source_hashes={str(s):sha(s) for s in sources},thresholds=list(THRESHOLDS),distances=list(DISTANCES),seeds=list(SEEDS),
        selection='maximum validation case-macro F1 subject to case-macro recall and pooled positive/negative localization recall >= original LoG validation; ties recall,higher threshold,larger distance; no feasible -> no replacement',
        training_run=False,scope='Exploratory reused-validation selection and reused-test/external re-evaluation; no fresh external/clinical/whole-WSI evidence',
        environment=dict(python=sys.version,torch=torch.__version__,numpy=np.__version__,threads=2),image_counts=dict(validation=227,test=407,external=133))
    fresh_json(output/'protocol.json',p)
    return p


def checked(output,selected=False):
    output=Path(output);p=read_json(output/'protocol.json')
    for field in ('input_hashes','source_hashes'):verify_hashes('/',p[field])
    if p['seeds']!=list(SEEDS) or p['thresholds']!=list(THRESHOLDS) or p['distances']!=list(DISTANCES):raise ValueError('Protocol changed')
    if selected:
        lock=read_json(output/'selection-lock.json')
        if lock['protocol_sha256']!=sha(output/'protocol.json') or lock['selection_sha256']!=sha(output/'selection.json'):raise ValueError('Selection changed')
        verify_hashes(output,lock['evidence_hashes'])
    return p


def localization_summary(samples):
    cases=defaultdict(lambda:np.zeros(3,dtype=int));matched=np.zeros(4,dtype=int);reference=np.zeros(4,dtype=int)
    for r in samples:
        gt=np.asarray(r['gt_points']).reshape(-1,2);gc=np.asarray(r['gt_classes'],dtype=int);points=np.asarray(r['points']).reshape(-1,2)
        pairs=match_points(points,gt,6);n=len(pairs)
        cases[r['case_id']]+=[n,len(points)-n,len(gt)-n]
        reference+=np.bincount(gc,minlength=4)
        matched+=np.bincount([gc[j] for _,j in pairs],minlength=4)
    cm={k:count_metrics(*v) for k,v in sorted(cases.items())}
    if np.any(reference[:2]==0):raise ValueError('Validation needs both tumor classes')
    return dict(case_macro_f1=float(np.mean([v['f1'] for v in cm.values()])),case_macro_recall=float(np.mean([v['recall'] for v in cm.values()])),
        tumor_recalls=(matched[:2]/reference[:2]).tolist(),localization=count_metrics(*np.sum(list(cases.values()),axis=0)),cases=cm,
        matched_by_reference_class=matched.tolist(),reference_by_class=reference.tolist())


def validation(output):
    output=Path(output);p=checked(output)
    fresh_json(output/'validation-started.json',dict(created_utc=utc(),protocol_sha256=sha(output/'protocol.json')))
    torch.set_num_threads(2);torch.use_deterministic_algorithms(True)
    rows=[r for r in read_json(Path(p['parent'])/'source-manifest.json') if r['split']=='validation']
    if len(rows)!=227 or len({r['case_id'] for r in rows})!=4:raise ValueError('Validation set mismatch')
    verify_data(p['data_dir'],rows)
    detectors=loaded_detectors(p['prior']);baselines=[];samples={s:[] for s in SEEDS}
    old=read_json(Path(p['parent'])/'selection-lock.json')['detector']['config']
    for i,r in enumerate(rows):
        rgb,gt,gc=load_sample(p['data_dir'],r)
        ref=dict(image=r['image'],case_id=r['case_id'],split='validation',gt_points=gt.tolist(),gt_classes=gc.tolist())
        baselines.append({**ref,'points':detect_centers(rgb,old)['points_xy'].tolist()})
        for seed,(model,config) in detectors.items():
            found=predict_centers(rgb,model,config);peaks,scores=peak_candidates(found['probability_map'])
            samples[seed].append({**ref,'points':peaks.tolist(),'scores':scores.tolist(),
                'diagnosis':diagnose_candidates(peaks,scores,gt,gc,config)})
        if (i+1)%50==0:print('VALIDATION REPLAY',i+1,flush=True)
    baseline=localization_summary(baselines);floors={k:baseline[k] for k in ('case_macro_recall','tumor_recalls')}
    write_rows(output/'validation-log.json.gz',baselines);selected=[]
    for seed in SEEDS:
        write_rows(output/f'validation-peaks-{seed}.json.gz',samples[seed]);trials=[]
        for threshold in THRESHOLDS:
            for distance in DISTANCES:
                config=dict(threshold=threshold,min_distance=distance)
                decoded=[{**r,'points':decode_candidates(np.asarray(r['points']).reshape(-1,2),np.asarray(r['scores']),**config)['points_xy'].tolist()} for r in samples[seed]]
                trials.append(dict(split='validation',config=config,**localization_summary(decoded)))
        outcome=select_recall_configuration(trials,floors)
        old_config=detectors[seed][1]
        old_trial=next(t for t in trials if t['config']==old_config)
        result=dict(seed=seed,old_config=old_config,old_validation=old_trial,**outcome,trials=trials)
        selected.append(result);print('SELECTION',json.dumps({k:v for k,v in result.items() if k not in ('trials','old_validation')}),flush=True)
    fresh_json(output/'selection.json',dict(created_utc=utc(),baseline=baseline,models=selected))
    evidence={f.name:sha(f) for f in output.glob('validation-*.json.gz')}
    fresh_json(output/'selection-lock.json',dict(created_utc=utc(),protocol_sha256=sha(output/'protocol.json'),selection_sha256=sha(output/'selection.json'),evidence_hashes=evidence))


def evaluate(output,external=False):
    output=Path(output);p=checked(output,selected=True);tag='external' if external else 'internal'
    fresh_json(output/(tag+'-started.json'),dict(created_utc=utc(),selection_lock_sha256=sha(output/'selection-lock.json')))
    torch.set_num_threads(2);torch.use_deterministic_algorithms(True)
    selected=read_json(output/'selection.json')['models'];detectors=loaded_detectors(p['prior'])
    configs={r['seed']:r['selected']['config'] for r in selected if r['selected'] is not None}
    classifiers=load_models(p['parent'],read_json(Path(p['parent'])/'selection-lock.json'))
    from pathology_edge.ki67_cnn import classify_centers
    predictions={s:[] for s in configs}
    if external:
        previous=Path(p['external']);refs=read_json(previous/'private-predictions.json')
        entries={r['name']:r for r in read_json(previous/'entries.json')};inputs={r['name']:r for r in read_json(previous/'input-manifest.json')}
        names=validate_external_entries(list(entries.values()));refmap={r['image']:r for r in refs}
        if len(refs)!=133 or set(refmap)!=set(names):raise ValueError('External set mismatch')
        url=download_url();rows=[refmap[name] for name in names]
    else:
        rows=[r for r in read_json(Path(p['parent'])/'source-manifest.json') if r['split']=='test'];verify_data(p['data_dir'],rows)
        if len(rows)!=407:raise ValueError('Test set mismatch')
    if not configs:
        fresh_json(output/(tag+'-not-run.json'),dict(reason='No feasible validation configuration',new_inference_images=0));return
    for i,r in enumerate(rows):
        if external:
            raw,meta=fetch_entry(url,entries[r['image']])
            if meta['sha256']!=inputs[r['image']]['sha256']:raise ValueError('External image hash changed')
            image=Image.open(io.BytesIO(raw))
            if image.mode!='RGB' or image.size!=(640,640):raise ValueError('Expected native640RGB')
            rgb=np.asarray(image);gt=np.asarray(r['gt_points']).reshape(-1,2);gc=np.asarray(r['gt_classes'])
        else:rgb,gt,gc=load_sample(p['data_dir'],r)
        for seed,config in configs.items():
            found=predict_centers(rgb,detectors[seed][0],config);points=found['points_xy']
            row=dict(image=r['image'],points=points.tolist(),scores=found['scores'].tolist(),gt_points=gt.tolist(),gt_classes=gc.tolist(),classes={})
            if not external:row['case_id']=r['case_id']
            for arm,model in classifiers.items():row['classes'][arm]=classify_centers(rgb,points,model).argmax(1).tolist()
            predictions[seed].append(row)
        if (i+1)%25==0:print(tag.upper(),i+1,flush=True)
    for seed,rs in predictions.items():
        folder=output/f'seed-{seed}'/tag;folder.mkdir(parents=True,exist_ok=False)
        write_rows(folder/'predictions.json.gz',rs)
        arms={a:(score_external(rs,a) if external else summarize(rs,a)) for a in classifiers}
        accounting={a:[dict(image=r['image'],**class_accounting(np.asarray(r['points']).reshape(-1,2),r['classes'][a],np.asarray(r['gt_points']).reshape(-1,2),r['gt_classes'])) for r in rs] for a in classifiers}
        fresh_json(folder/'results.json',dict(seed=seed,config=configs[seed],image_count=len(rs),arms=arms,predictions_sha256=sha(folder/'predictions.json.gz'),selection_lock_sha256=sha(output/'selection-lock.json'),training_run=False,inference_uses_gt_centers=False,scope=p['scope']))
        write_rows(folder/'class-accounting.json.gz',accounting)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('stage',choices=['prepare','validation','internal','external']);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--prior',type=Path)
    args=parser.parse_args()
    if args.stage=='prepare':
        if args.prior is None:parser.error('prepare requires --prior')
        prepare(args.prior,args.output)
    elif args.stage=='validation':validation(args.output)
    else:evaluate(args.output,args.stage=='external')


if __name__=='__main__':main()
