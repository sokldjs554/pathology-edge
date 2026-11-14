"""Frozen learned-center experiment stages."""
from __future__ import annotations
import argparse
from collections import defaultdict
from datetime import datetime,timezone
import io
import json
import os
from pathlib import Path
import platform
import time
import numpy as np
from PIL import Image
import torch
from .ki67_centers import CenterDetector,center_target,center_focal_loss,peak_candidates,decode_candidates,predict_centers
from .ki67_experiment import read_json,fresh_json,sha,verify_hashes,validate_manifest,verify_data,load_sample,load_models,summarize
from .ki67_evaluation import match_points,count_metrics
from .ki67_cnn import classify_centers
from .ki67_external import fetch_entry,download_url,validate_external_entries,tumor_only_row

SEEDS=(20261117,20261118,20261119)
THRESHOLDS=(.1,.2,.3,.5)
DISTANCES=(4,6,8)
SOURCE_NAMES=('model.py','ihc_baseline.py','ki67_detection.py','ki67_evaluation.py',
              'ki67_cnn.py','ki67_experiment.py','ki67_external.py',
              'ki67_centers.py','ki67_center_experiment.py')


def utc():return datetime.now(timezone.utc).isoformat()


def start_stage(root,stage):
    fresh_json(Path(root)/(stage+'-started.json'),{'created_utc':utc()})


def select_configuration(samples):
    if not samples or any(s['split']!='validation' for s in samples):
        raise ValueError('Configuration selection accepts validation only')
    trials=[]
    for threshold in THRESHOLDS:
        for distance in DISTANCES:
            counts=defaultdict(lambda:np.zeros(3,dtype=np.int64))
            for s in samples:
                points=decode_candidates(s['points'],s['scores'],threshold,distance)['points_xy']
                n=len(match_points(points,s['gt_points'],6))
                counts[s['case_id']]+=[n,len(points)-n,len(s['gt_points'])-n]
            cases={case:count_metrics(*v) for case,v in sorted(counts.items())}
            trials.append(dict(config=dict(threshold=threshold,min_distance=distance),cases=cases,
                case_macro_f1=float(np.mean([v['f1'] for v in cases.values()])),
                case_macro_recall=float(np.mean([v['recall'] for v in cases.values()]))))
    chosen=max(trials,key=lambda r:(r['case_macro_f1'],r['case_macro_recall'],r['config']['threshold'],r['config']['min_distance']))
    return {**chosen,'trials':trials}


def verify_selection(root):
    root=Path(root);lock=read_json(root/'selection-lock.json')
    if sha(root/'protocol.json')!=lock['protocol_sha256'] or sha(root/'selection.json')!=lock['selection_sha256']:
        raise ValueError('Selection protocol hash mismatch')
    if not lock['model_hashes']:raise ValueError('No frozen model hashes')
    verify_hashes(root,lock['model_hashes'])
    return lock


def prepare(data,parent,external,output):
    data,parent,external,output=[Path(p).resolve() for p in (data,parent,external,output)]
    previous=read_json(parent/'protocol.json');selection=read_json(parent/'selection-lock.json')
    if sha(parent/'protocol.json')!=selection['protocol_sha256']:raise ValueError('Parent protocol hash mismatch')
    verify_hashes(parent,previous['input_hashes']);verify_hashes(parent,selection['model_hashes'])
    rows=read_json(parent/'source-manifest.json');split=read_json(parent/'split.json')
    validate_manifest(rows,split['assignment'])
    counts={s:sum(r['split']==s for r in rows) for s in ('train','validation','test')}
    if counts!={'train':696,'validation':227,'test':407}:raise ValueError('Unexpected fixed split')
    for folder,name,key in [(parent,'predictions.json','predictions_sha256'),(external,'private-predictions.json','private_predictions_sha256')]:
        if sha(folder/name)!=read_json(folder/'results.json')[key]:raise ValueError('Baseline predictions changed')
    images=validate_external_entries(read_json(external/'entries.json'))
    refs=read_json(external/'private-predictions.json')
    if len(refs)!=133 or {r['image'] for r in refs}!=set(images):raise ValueError('External image set mismatch')
    verify_data(data,rows) # hashes only, no test scoring at preparation
    output.mkdir(parents=True,exist_ok=False)
    source=Path(__file__).parent;(output/'frozen_source/pathology_edge').mkdir(parents=True)
    for name in SOURCE_NAMES:(output/'frozen_source/pathology_edge'/name).write_bytes((source/name).read_bytes())
    (output/'frozen_source/pathology_edge/__init__.py').write_text('"""Frozen learned-center research source."""\n')
    inputs={str(parent/n):sha(parent/n) for n in ('protocol.json','selection-lock.json','source-manifest.json','split.json','model.json','predictions.json','results.json',*selection['model_hashes'])}
    inputs.update({str(external/n):sha(external/n) for n in ('private-predictions.json','results.json','entries.json','input-manifest.json','input-audit.json')})
    p=dict(schema='learned-centers.v1',created_utc=utc(),data_dir=str(data),parent=str(parent),external=str(external),
        input_hashes=inputs,source_hashes={n:sha(source/n) for n in SOURCE_NAMES},
        seeds=list(SEEDS),epochs=16,batch_size=8,learning_rate=.001,torch_threads=2,
        architecture='TinyUNet width4, LeakyReLU slope0.1, head bias -2.19; 7537 parameters',
        target=dict(sigma_px=2,radius_px=6,aggregation='maximum; not nuclear mask or count density'),
        thresholds=list(THRESHOLDS),min_distances=list(DISTANCES),matching_radius_px=6,image_counts=counts,
        selection='validation case-macro localization F1; ties recall,earlier epoch,higher threshold,larger distance',
        augmentation='train only: pairedrot90/flips; per-imageRGBmultipliers uniform[.9,1.1]',
        classification='four fixed classifiers re-inferred at NEW centers, no classifier fitting',
        exposure='Patherea407 and BCData133 previously exposed: re-evaluations, not fresh holdouts',
        reference_limits='point-derived supervision; original annotation polygon support unavailable; unannotated pixels are not expert-proven non-cells',
        external_scope='native640 RGB, canonical tumor-only points from prior hash-locked acquisition, no MPP/patient independence claim',
        clinical_validation=False,whole_wsi_validation=False,
        environment=dict(python=platform.python_version(),torch=torch.__version__,numpy=np.__version__,platform=platform.platform(),
                         logical_cpu_count=os.cpu_count(),cpu_affinity_count=len(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else None,cuda=torch.cuda.is_available()))
    fresh_json(output/'protocol.json',p);return p


def checked(root):
    root=Path(root);p=read_json(root/'protocol.json')
    for path,digest in p['input_hashes'].items():
        if sha(path)!=digest:raise ValueError('Frozen input hash mismatch: '+path)
    verify_hashes(Path(__file__).parent,p['source_hashes'])
    if p['seeds']!=list(SEEDS) or p['epochs']!=16 or p['thresholds']!=list(THRESHOLDS) or p['min_distances']!=list(DISTANCES):
        raise ValueError('Protocol configuration mismatch')
    return root,p


def _tensor(images):
    return torch.from_numpy(images.transpose(0,3,1,2).copy()).float()/255


def train_seed(train_images,targets,val_images,val_refs,seed,root,p):
    torch.manual_seed(seed);rng=np.random.default_rng(seed)
    model=CenterDetector();optimizer=torch.optim.Adam(model.parameters(),lr=p['learning_rate'])
    best_key=None;best_state=None;chosen=None;history=[];started=time.perf_counter()
    for epoch in range(1,p['epochs']+1):
        model.train();order=rng.permutation(len(train_images));loss_sum=0.
        for start in range(0,len(order),p['batch_size']):
            ids=order[start:start+p['batch_size']]
            x=_tensor(train_images[ids]);target=torch.from_numpy(targets[ids,None].copy())
            for i in range(len(ids)):
                k=int(rng.integers(4));x[i]=torch.rot90(x[i],k,(1,2));target[i]=torch.rot90(target[i],k,(1,2))
                for dim in (1,2):
                    if rng.random()<.5:x[i]=x[i].flip(dim);target[i]=target[i].flip(dim)
            factors=torch.from_numpy(rng.uniform(.9,1.1,(len(ids),3,1,1)).astype(np.float32))
            x=(x*factors).clamp(0,1);optimizer.zero_grad(set_to_none=True)
            loss=center_focal_loss(model(x),target);loss.backward();optimizer.step()
            loss_sum+=float(loss.detach())*len(ids)
        model.eval();samples=[]
        with torch.inference_mode():
            for start in range(0,len(val_images),p['batch_size']):
                maps=torch.sigmoid(model(_tensor(val_images[start:start+p['batch_size']]))).cpu().numpy()[:,0]
                for j,heat in enumerate(maps):
                    points,scores=peak_candidates(heat)
                    samples.append({**val_refs[start+j],'points':points,'scores':scores})
        selected=select_configuration(samples)
        entry=dict(epoch=epoch,train_loss=loss_sum/len(train_images),**selected);history.append(entry)
        key=(selected['case_macro_f1'],selected['case_macro_recall'],-epoch,selected['config']['threshold'],selected['config']['min_distance'])
        if best_key is None or key>best_key:
            best_key=key;chosen=entry;best_state={k:v.detach().clone() for k,v in model.state_dict().items()}
        print(json.dumps({'seed':seed,'epoch':epoch,'loss':entry['train_loss'],'val_f1':selected['case_macro_f1'],'config':selected['config']}),flush=True)
    filename=f'detector-{seed}.pt';torch.save(best_state,root/filename)
    report=dict(seed=seed,best_epoch=chosen['epoch'],config=chosen['config'],validation_case_macro_f1=chosen['case_macro_f1'],
                validation_case_macro_recall=chosen['case_macro_recall'],checkpoint=filename,sha256=sha(root/filename),
                parameter_count=sum(v.numel() for v in model.parameters()),training_selection_seconds=time.perf_counter()-started,history=history)
    fresh_json(root/f'training-{seed}.json',report)
    return {k:v for k,v in report.items() if k!='history'}


def fit(root):
    root,p=checked(root);start_stage(root,'fit');torch.set_num_threads(p['torch_threads']);torch.use_deterministic_algorithms(True)
    rows=[r for r in read_json(Path(p['parent'])/'source-manifest.json') if r['split'] in ('train','validation')]
    verify_data(p['data_dir'],rows);images=defaultdict(list);targets=[];val_refs=[]
    for r in rows:
        rgb,points,_=load_sample(p['data_dir'],r)
        if rgb.shape!=(224,224,3):raise ValueError('Training/validation requires native224RGB')
        images[r['split']].append(rgb)
        if r['split']=='train':targets.append(center_target(points,rgb.shape[:2]))
        else:val_refs.append(dict(split='validation',case_id=r['case_id'],gt_points=points))
    images={s:np.stack(v) for s,v in images.items()};targets=np.stack(targets)
    models=[train_seed(images['train'],targets,images['validation'],val_refs,seed,root,p) for seed in p['seeds']]
    fresh_json(root/'selection.json',{'models':models,'test_used_for_selection':False,'external_used_for_selection':False})
    fresh_json(root/'selection-lock.json',dict(created_utc=utc(),protocol_sha256=sha(root/'protocol.json'),selection_sha256=sha(root/'selection.json'),
                model_hashes={m['checkpoint']:m['sha256'] for m in models},evaluation_started=False))
    return models


def loaded_detectors(root):
    verify_selection(root);result={}
    for item in read_json(Path(root)/'selection.json')['models']:
        model=CenterDetector();model.load_state_dict(torch.load(Path(root)/item['checkpoint'],map_location='cpu',weights_only=True),strict=True)
        if not all(torch.isfinite(v).all() for v in model.state_dict().values()):raise ValueError('Nonfinite detector checkpoint')
        result[item['seed']]=(model.eval(),item['config'])
    return result


def score_external(rows,arm):
    r=summarize([tumor_only_row(v,arm) for v in rows],arm)
    for key in list(r):
        if key.startswith('case_') or key=='per_case':del r[key]
    for item in [r,*r['per_image']]:
        item['two_class_macro_f1']=float(np.mean([c['f1'] for c in item['classes'][:2]]))
        item['classes']=item['classes'][:2];item.pop('macro_f1');item.pop('case_id',None)
    return r


def evaluate(root,external=False):
    root,p=checked(root);verify_selection(root);tag='external' if external else 'internal';start_stage(root,tag)
    torch.set_num_threads(p['torch_threads']);detectors=loaded_detectors(root)
    parent=Path(p['parent']);classifiers=load_models(parent,read_json(parent/'selection-lock.json'))
    outputs={seed:[] for seed in detectors}
    if external:
        previous=Path(p['external']);refs=read_json(previous/'private-predictions.json')
        entries={r['name']:r for r in read_json(previous/'entries.json')};inputs={r['name']:r for r in read_json(previous/'input-manifest.json')}
        names=validate_external_entries(list(entries.values()));refmap={r['image']:r for r in refs}
        if len(refs)!=133 or set(refmap)!=set(names):raise ValueError('External reference image set mismatch')
        url=download_url();rows=[refmap[name] for name in names]
    else:
        rows=[r for r in read_json(parent/'source-manifest.json') if r['split']=='test'];verify_data(p['data_dir'],rows)
    for i,r in enumerate(rows):
        if external:
            raw,meta=fetch_entry(url,entries[r['image']])
            if meta['sha256']!=inputs[r['image']]['sha256']:raise ValueError('External image byte hash changed')
            image=Image.open(io.BytesIO(raw))
            if image.mode!='RGB' or image.size!=(640,640):raise ValueError('Expected native640RGB')
            rgb=np.asarray(image);gt=np.asarray(r['gt_points']).reshape(-1,2);gc=r['gt_classes']
        else:rgb,gt,gc=load_sample(p['data_dir'],r)
        for seed,(model,config) in detectors.items():
            detected=predict_centers(rgb,model,config);points=detected['points_xy']
            row=dict(image=r['image'],gt_points=gt.tolist(),gt_classes=np.asarray(gc).tolist(),points=points.tolist(),scores=detected['scores'].tolist(),classes={})
            if not external:row['case_id']=r['case_id']
            for arm,classifier in classifiers.items():row['classes'][arm]=classify_centers(rgb,points,classifier).argmax(1).tolist()
            outputs[seed].append(row)
        if (i+1)%25==0:print(tag.upper()+' '+str(i+1),flush=True)
    results={}
    for seed,predictions in outputs.items():
        folder=root/f'seed-{seed}'/tag;folder.mkdir(parents=True,exist_ok=False)
        filename='private-predictions.json' if external else 'predictions.json'
        with (folder/filename).open('x') as f:json.dump(predictions,f,separators=(',',':'),allow_nan=False)
        arms={a:(score_external(predictions,a) if external else summarize(predictions,a)) for a in classifiers}
        result=dict(schema='learned-centers-results.v1',seed=seed,image_count=len(rows),arms=arms,
                    selection_lock_sha256=sha(root/'selection-lock.json'),scope=p['exposure'],
                    new_detector_and_classifier_inference_images=len(rows),inference_uses_gt_centers=False,
                    fresh_external_validation=False,clinical_validation=False,whole_wsi_validation=False)
        result['private_predictions_sha256' if external else 'predictions_sha256']=sha(folder/filename)
        fresh_json(folder/'results.json',result);results[seed]=result
    return results


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    prep=sub.add_parser('prepare')
    for name in ('data-dir','parent','external'):prep.add_argument('--'+name,type=Path,required=True)
    for name in ('fit','evaluate','external'):sub.add_parser(name)
    for child in sub.choices.values():child.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.command=='prepare':prepare(a.data_dir,a.parent,a.external,a.output)
    elif a.command=='fit':fit(a.output)
    else:evaluate(a.output,external=a.command=='external')
    print('DONE '+a.command,flush=True)


if __name__=='__main__':main()
