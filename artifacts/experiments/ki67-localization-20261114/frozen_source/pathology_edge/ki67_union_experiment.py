"""Three paired frozen proposal seeds and a separately trained RGB retention CNN."""
from collections import defaultdict
from datetime import datetime, timezone
import gzip
import io
import json
from pathlib import Path
import platform
import shutil
import subprocess
import time
import numpy as np
from PIL import Image
import torch
from .ki67_union import (CandidateRejector, merge_proposals, negative_proxy_indices,
    retention_scores, retain_candidates, summarize_locations, choose_trial, trial_key)
from .ki67_centers import predict_centers, decode_candidates
from .ki67_detection import detect_centers
from .ki67_center_experiment import loaded_detectors, score_external
from .ki67_cnn import cell_crops, classify_centers
from .ki67_evaluation import match_points
from .ki67_experiment import (read_json, fresh_json, sha, verify_hashes, verify_data,
    validate_manifest, load_sample, load_models, summarize)
from .ki67_external import fetch_entry, download_url, validate_external_entries

SEEDS=(20261117,20261118,20261119)
THRESHOLDS=(0,.05,.1,.2,.3,.4,.5,.6,.7,.8,.9,.95,.99,1)
DISTANCES=(4,6,8)
FLOORS=dict(case_macro_recall=.4797951648158369,tumor_recalls=[270/483,439/1292])
LEARNED_CONFIG=dict(threshold=.01,min_distance=4)
LOG_CONFIG=dict(min_response=.1,min_distance=8)
ROOT=Path(__file__).resolve().parents[2]


def utc():return datetime.now(timezone.utc).isoformat()


def write_rows(path,rows):
    with Path(path).open('xb') as f:
        with gzip.GzipFile(fileobj=f,mode='wb',mtime=0) as g:
            g.write(json.dumps(rows,separators=(',',':'),allow_nan=False).encode())


def read_rows(path):
    with gzip.open(path,'rt') as f:return json.load(f)


def prepare(prior,output):
    prior,output=Path(prior).resolve(),Path(output).resolve()
    old=read_json(prior/'protocol.json');parent=Path(old['parent'])
    detectors=loaded_detectors(prior)
    if tuple(detectors)!=SEEDS:raise ValueError('Expected fixed three detector seeds')
    rows=read_json(parent/'source-manifest.json')
    validate_manifest(rows,read_json(parent/'split.json')['assignment'])
    counts={s:sum(r['split']==s for r in rows) for s in ('train','validation','test')}
    if counts!={'train':696,'validation':227,'test':407}:raise ValueError('Unexpected fixed split')
    verify_data(old['data_dir'],[r for r in rows if r['split']!='test'])
    if shutil.disk_usage(output.parent).free<20_000_000:raise ValueError('Need 20 MB free for compressed evidence')
    inputs={str(prior/n):sha(prior/n) for n in ('protocol.json','selection.json','selection-lock.json',*(f'detector-{s}.pt' for s in SEEDS))}
    inputs.update(old['input_hashes'])
    source=[*sorted((ROOT/'src/pathology_edge').glob('*.py')),ROOT/'scripts/run_ki67_union.py']
    output.mkdir(parents=True,exist_ok=False)
    frozen=output/'frozen_source/pathology_edge';frozen.mkdir(parents=True)
    for path in source:
        (frozen/path.name).write_bytes(path.read_bytes())
    p=dict(schema='ki67-union.v1',created_utc=utc(),prior=str(prior),parent=str(parent),external=old['external'],data_dir=old['data_dir'],
        input_hashes=inputs,source_hashes={str(s):sha(s) for s in source},
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        seeds=list(SEEDS),epochs=12,batch_size=64,learning_rate=.001,torch_threads=2,
        thresholds=list(THRESHOLDS),distances=list(DISTANCES),floors=FLOORS,
        learned_config=LEARNED_CONFIG,log_config=LOG_CONFIG,image_counts=counts,
        architecture='native32 RGB; two 3x3 convs per block 8/16/32, LeakyReLU .1, pool2, flatten512->2',
        training='case balanced within each binary label; balanced batches; 2*train_GT per epoch; matched candidate .5 else GT+jitter[-3,3]; train-only rotations/flips/RGB[.9,1.1]',
        negative_proxy='union centers >12px from all annotations, interior24px, <=256/image; none from GT-empty image; not expert-confirmed background',
        selection='joint FP/FN <= same-seed A, one strict; fixed LoG recall floors; every case recall >=.9*A; case-macro F1, recall, earlier epoch, higher threshold, larger spacing',
        scope='Exploratory reused-validation selection; eligible models only on reused test407/BCData133. Not fresh external, clinical or whole-WSI validation.',
        pairing='Frozen detector seed paired with new gate seed; not detector retraining or isolated gate-seed variability',
        classifier_training=False,clinical_validation=False,whole_wsi_validation=False,
        environment=dict(python=platform.python_version(),torch=torch.__version__,numpy=np.__version__,platform=platform.platform()))
    fresh_json(output/'protocol.json',p)
    (output/'protocol.sha256').write_text(sha(output/'protocol.json')+'\n')
    return p


def validate_selection(selection):
    models=selection['models']
    if [m['seed'] for m in models]!=list(SEEDS):raise ValueError('All three ordered seed outcomes required')
    return [m for m in models if m['selected'] is not None]


def checked(root,selected=False):
    root=Path(root)
    if sha(root/'protocol.json')!=(root/'protocol.sha256').read_text().strip():raise ValueError('Protocol hash changed')
    p=read_json(root/'protocol.json')
    for field in ('input_hashes','source_hashes'):verify_hashes('/',p[field])
    if p['seeds']!=list(SEEDS) or p['epochs']!=12 or p['thresholds']!=list(THRESHOLDS) or p['distances']!=list(DISTANCES) or p['floors']!=FLOORS:
        raise ValueError('Protocol configuration changed')
    if selected:
        lock=read_json(root/'selection-lock.json')
        if lock['protocol_sha256']!=sha(root/'protocol.json') or lock['selection_sha256']!=sha(root/'selection.json'):raise ValueError('Selection hash changed')
        verify_hashes(root,lock['evidence_hashes'])
        validate_selection(read_json(root/'selection.json'))
    return p


def make_pools(samples,rng):
    if not samples or any(r['split']!='train' for r in samples):raise ValueError('Training pools accept train only')
    pools={0:defaultdict(list),1:defaultdict(list)}
    for i,r in enumerate(samples):
        for j in range(len(r['gt_points'])):pools[1][r['case_id']].append((i,j))
        negatives=negative_proxy_indices(r['points'],r['gt_points'],r['rgb'].shape[:2])
        if len(negatives)>256:negatives=np.sort(rng.choice(negatives,256,replace=False))
        for j in negatives:pools[0][r['case_id']].append((i,int(j)))
    return pools


def balanced_draws(pools,count,rng):
    if count<=0 or count%2 or not pools[0] or not pools[1]:raise ValueError('Need both labels and an even sample count')
    result=[]
    for label in (0,1):
        cases=sorted(k for k,v in pools[label].items() if v)
        if not cases:raise ValueError('Missing nonempty label pool')
        for _ in range(count//2):
            case=cases[int(rng.integers(len(cases)))];items=pools[label][case]
            result.append((label,items[int(rng.integers(len(items)))]))
    return [result[i] for i in rng.permutation(len(result))]


def training_batch(samples,pools,count,rng):
    crops,labels=[],[]
    for label,(i,j) in balanced_draws(pools,count,rng):
        r=samples[i]
        if label:
            center=r['gt_points'][j].copy()
            if j in r['matched'] and rng.random()<.5:center=r['points'][r['matched'][j]].copy()
            else:
                shifted=center+rng.integers(-3,4,2)
                if np.all(shifted>=0) and shifted[0]<r['rgb'].shape[1] and shifted[1]<r['rgb'].shape[0]:center=shifted
        else:center=r['points'][j]
        # The padded image is cached in RAM; no derived dataset is written to disk.
        x,y=center.astype(int);crop=r['padded'][y:y+32,x:x+32]
        crop=np.rot90(crop,int(rng.integers(4)))
        if rng.random()<.5:crop=np.flip(crop,axis=0)
        if rng.random()<.5:crop=np.flip(crop,axis=1)
        crops.append(crop);labels.append(label)
    x=torch.from_numpy(np.stack(crops).transpose(0,3,1,2).copy()).float()/255
    factors=torch.from_numpy(rng.uniform(.9,1.1,(count,3,1,1)).astype(np.float32))
    return (x*factors).clamp(0,1),torch.tensor(labels,dtype=torch.long)


def validation_trials(samples,epoch):
    if any(r['split']!='validation' for r in samples):raise ValueError('Validation only')
    trials=[]
    for distance in DISTANCES:
        cached=[retain_candidates(r['points'],r['scores'],0,distance) for r in samples]
        for threshold in THRESHOLDS:
            decoded=[{**r,'points':c['points_xy'][c['scores']>=threshold]} for r,c in zip(samples,cached)]
            trials.append(dict(split='validation',epoch=epoch,config=dict(threshold=threshold,min_distance=distance),**summarize_locations(decoded)))
    return trials


def _serial_sample(r):
    return {k:(v.tolist() if isinstance(v,np.ndarray) else v) for k,v in r.items() if k not in ('rgb','padded','matched','scores')}


def train_seed(samples,seed,root,p):
    rng=np.random.default_rng(seed);torch.manual_seed(seed)
    training=[r for r in samples if r['split']=='train'];validation=[r for r in samples if r['split']=='validation']
    pools=make_pools(training,rng)
    if not pools[0] or not pools[1]:raise ValueError('No eligible negative/positive proxies')
    model=CandidateRejector();optimizer=torch.optim.Adam(model.parameters(),lr=p['learning_rate'])
    baseline=summarize_locations([{**r,'points':r['a_points']} for r in validation])
    union=summarize_locations(validation)
    write_rows(root/f'validation-{seed}.json.gz',[_serial_sample(r) for r in validation])
    fresh_json(root/f'pools-{seed}.json',dict(positive_by_case={k:len(v) for k,v in pools[1].items()},negative_proxy_by_case={k:len(v) for k,v in pools[0].items()},seed=seed))
    for r in training:
        r['matched']={j:i for i,j in match_points(r['points'],r['gt_points'])}
        r['padded']=np.pad(r['rgb'],((16,16),(16,16),(0,0)),constant_values=255)
    best,diagnostic,history=None,None,[];started=time.perf_counter();score_epochs={}
    epoch_count=2*sum(len(r['gt_points']) for r in training)
    for epoch in range(1,p['epochs']+1):
        model.train();loss_sum=0.
        for start in range(0,epoch_count,p['batch_size']):
            count=min(p['batch_size'],epoch_count-start)
            x,y=training_batch(training,pools,count,rng);optimizer.zero_grad(set_to_none=True)
            loss=torch.nn.functional.cross_entropy(model(x),y)
            if not torch.isfinite(loss):raise ValueError('Nonfinite training loss')
            loss.backward();optimizer.step();loss_sum+=float(loss.detach())*count
        for r in validation:r['scores']=retention_scores(r['rgb'],r['points'],model)
        score_epochs[f'epoch_{epoch}']=np.concatenate([r['scores'] for r in validation]).astype(np.float32)
        trials=validation_trials(validation,epoch);outcome=choose_trial(trials,baseline,p['floors'])
        candidate=outcome['selected'];d=max(trials,key=trial_key)
        if diagnostic is None or trial_key(d)>trial_key(diagnostic):
            diagnostic=d;torch.save(model.state_dict(),root/f'diagnostic-{seed}.pt')
        if candidate is not None and (best is None or trial_key(candidate)>trial_key(best)):
            best=candidate;torch.save(model.state_dict(),root/f'gate-{seed}.pt')
        history.append(dict(epoch=epoch,train_loss=loss_sum/epoch_count,feasible_trials=outcome['feasible_trials'],trials=trials))
        print(json.dumps(dict(seed=seed,epoch=epoch,train_loss=loss_sum/epoch_count,feasible=outcome['feasible_trials'],best_f1=d['case_macro_f1'],best_recall=d['case_macro_recall'],seconds=time.perf_counter()-started)),flush=True)
    np.savez_compressed(root/f'validation-scores-{seed}.npz',**score_epochs)
    write_rows(root/f'trials-{seed}.json.gz',history)
    return dict(seed=seed,selected=best,diagnostic=diagnostic,baseline=baseline,union=union,
        feasible_trials=sum(h['feasible_trials'] for h in history),training_selection_seconds=time.perf_counter()-started,
        parameter_count=sum(t.numel() for t in model.parameters()),checkpoint=f'gate-{seed}.pt' if best else None,
        diagnostic_checkpoint=f'diagnostic-{seed}.pt',epochs=p['epochs'])


def fit(root):
    root=Path(root);p=checked(root);fresh_json(root/'fit-started.json',dict(created_utc=utc()))
    torch.set_num_threads(p['torch_threads']);torch.use_deterministic_algorithms(True)
    rows=[r for r in read_json(Path(p['parent'])/'source-manifest.json') if r['split'] in ('train','validation')]
    verify_data(p['data_dir'],rows);base=[]
    for r in rows:
        rgb,gt,gc=load_sample(p['data_dir'],r)
        if rgb.shape!=(224,224,3):raise ValueError('Expected native224')
        base.append(dict(image=r['image'],split=r['split'],case_id=r['case_id'],rgb=rgb,gt_points=gt,gt_classes=gc,
            log_points=detect_centers(rgb,LOG_CONFIG)['points_xy']))
    models=[]
    for seed,(detector,a_config) in loaded_detectors(p['prior']).items():
        samples=[]
        for r in base:
            found=predict_centers(r['rgb'],detector,LEARNED_CONFIG)
            from .ki67_centers import peak_candidates
            a=decode_candidates(*peak_candidates(found['probability_map']),**a_config)['points_xy']
            union=merge_proposals(found['points_xy'],r['log_points'],r['rgb'].shape[:2])
            samples.append({**r,'points':union['points_xy'],'sources':union['sources'],'a_points':a})
        models.append(train_seed(samples,seed,root,p))
    fresh_json(root/'selection.json',dict(models=models,test_used_for_selection=False,external_used_for_selection=False))
    evidence={f.name:sha(f) for f in root.iterdir() if f.suffix in ('.gz','.npz','.pt') or f.name.startswith('pools-')}
    fresh_json(root/'selection-lock.json',dict(created_utc=utc(),protocol_sha256=sha(root/'protocol.json'),selection_sha256=sha(root/'selection.json'),evidence_hashes=evidence))
    checked(root,selected=True)
    return models


def evaluate(root,external=False):
    root=Path(root);p=checked(root,selected=True);tag='external' if external else 'internal'
    eligible=validate_selection(read_json(root/'selection.json'))
    if not eligible:
        fresh_json(root/(tag+'-not-run.json'),dict(reason='No feasible seed; protocol forbids further evaluation',new_inference_images=0))
        return
    fresh_json(root/(tag+'-started.json'),dict(created_utc=utc(),selection_lock_sha256=sha(root/'selection-lock.json')))
    torch.set_num_threads(p['torch_threads']);detectors=loaded_detectors(p['prior'])
    classifiers=load_models(p['parent'],read_json(Path(p['parent'])/'selection-lock.json'))
    gates={}
    for m in eligible:
        gate=CandidateRejector();gate.load_state_dict(torch.load(root/m['checkpoint'],weights_only=True,map_location='cpu'));gates[m['seed']]=gate.eval()
    if external:
        previous=Path(p['external']);refs=read_json(previous/'private-predictions.json')
        entries={r['name']:r for r in read_json(previous/'entries.json')};inputs={r['name']:r for r in read_json(previous/'input-manifest.json')}
        names=validate_external_entries(list(entries.values()));refmap={r['image']:r for r in refs}
        if len(refs)!=133 or set(refmap)!=set(names):raise ValueError('External set changed')
        url=download_url();rows=[refmap[n] for n in names]
    else:
        rows=[r for r in read_json(Path(p['parent'])/'source-manifest.json') if r['split']=='test'];verify_data(p['data_dir'],rows)
    outputs={m['seed']:{arm:[] for arm in ('A','B','C','C0')} for m in eligible}
    for index,r in enumerate(rows):
        if external:
            raw,meta=fetch_entry(url,entries[r['image']])
            if meta['sha256']!=inputs[r['image']]['sha256']:raise ValueError('External raw hash changed')
            im=Image.open(io.BytesIO(raw))
            if im.mode!='RGB' or im.size!=(640,640):raise ValueError('Expected native640RGB')
            rgb=np.asarray(im);gt=np.asarray(r['gt_points']).reshape(-1,2);gc=np.asarray(r['gt_classes'])
        else:rgb,gt,gc=load_sample(p['data_dir'],r)
        log=detect_centers(rgb,LOG_CONFIG)['points_xy']
        for item in eligible:
            seed=item['seed'];detector,a_config=detectors[seed]
            found=predict_centers(rgb,detector,LEARNED_CONFIG)
            from .ki67_centers import peak_candidates
            a=decode_candidates(*peak_candidates(found['probability_map']),**a_config)['points_xy']
            union=merge_proposals(found['points_xy'],log,rgb.shape[:2])
            points=union['points_xy'];scores=retention_scores(rgb,points,gates[seed]);config=item['selected']['config']
            arms=dict(A=a,B=points,C=retain_candidates(points,scores,**config)['points_xy'],
                      C0=retain_candidates(points,scores,0,config['min_distance'])['points_xy'])
            for arm,xy in arms.items():
                row=dict(image=r['image'],points=xy.tolist(),gt_points=gt.tolist(),gt_classes=gc.tolist(),classes={})
                if not external:row['case_id']=r['case_id']
                for name,classifier in classifiers.items():row['classes'][name]=classify_centers(rgb,xy,classifier).argmax(1).tolist()
                outputs[seed][arm].append(row)
        if (index+1)%25==0:print(tag,index+1,flush=True)
    for seed,arms in outputs.items():
        for arm,rs in arms.items():
            folder=root/f'seed-{seed}'/tag/arm;folder.mkdir(parents=True,exist_ok=False)
            write_rows(folder/'predictions.json.gz',rs)
            results={name:(score_external(rs,name) if external else summarize(rs,name)) for name in classifiers}
            fresh_json(folder/'results.json',dict(seed=seed,arm=arm,image_count=len(rows),classifiers=results,predictions_sha256=sha(folder/'predictions.json.gz'),selection_lock_sha256=sha(root/'selection-lock.json'),scope=p['scope']))
    checked(root,selected=True)
