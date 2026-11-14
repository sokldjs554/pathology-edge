"""One final paired frozen-feature study, with diagnostic holdout fallback."""
from pathlib import Path
import hashlib
import json
import platform
import shutil
import subprocess
import time
import numpy as np
import torch
from .ki67_transfer import TransferCenterDetector,balanced_probabilities,WEIGHT_SHA256
from .ki67_centers import center_target,center_focal_loss,peak_candidates,predict_centers
from .ki67_center_refit import configuration_trials,choose_refit,verify_initial_baseline,tensor,THRESHOLDS
from .ki67_center_experiment import loaded_detectors
from .ki67_union import summarize_locations,trial_key
from .ki67_union_experiment import SEEDS,DISTANCES,FLOORS,utc,write_rows
from .ki67_experiment import read_json,fresh_json,sha,verify_hashes,validate_manifest,verify_data,load_sample

ROOT=Path(__file__).resolve().parents[2]
ARMS=('pretrained','random')
FIXED=dict(schema='ki67-final-transfer.v1',seeds=list(SEEDS),arms=list(ARMS),primary_arm='pretrained',epochs=24,
           learning_rate=.001,batch_size=8,torch_threads=1,baseline_threads=2,thresholds=list(THRESHOLDS),distances=list(DISTANCES),floors=FLOORS,
           selection_fallback='diagnostic',classifier_policy='fixed paired CNN13/14/15',weight_sha256=WEIGHT_SHA256)
LEARNER_NAMES=('learner_coordinates.py','learner_losses.py','learner_metrics.py','learner_refinement.py','learner_split.py','learner_wsi.py')


def job_name(arm,seed):
    if arm not in ARMS or type(seed) is not int or seed not in SEEDS:raise ValueError('Unknown arm/seed')
    return f'{arm}-seed{seed}'


def tensor_hashes(state):
    return {k:hashlib.sha256(v.detach().cpu().contiguous().numpy().tobytes()).hexdigest() for k,v in state.items()}


def primary_models(selection):
    rows=selection.get('models',[])
    if len(rows)!=6 or {(r.get('arm'),r.get('seed')) for r in rows}!={(a,s) for a in ARMS for s in SEEDS}:raise ValueError('Require six unique workers')
    for r in rows:
        job_name(r['arm'],r['seed'])
        if r.get('epochs')!=24:raise ValueError('Incomplete worker')
        t=r.get('evaluation_trial',{})
        if (type(t.get('epoch')) is not int or not 1<=t['epoch']<=24 or t.get('split')!='validation'
            or t.get('config',{}).get('threshold') not in THRESHOLDS or t['config'].get('min_distance') not in DISTANCES
            or r.get('evaluation_checkpoint')!=('selected.pt' if r.get('selected') is not None else 'diagnostic.pt')
            or t!=(r['selected'] if r.get('selected') is not None else r.get('diagnostic'))):raise ValueError('Invalid evaluation selection')
    return sorted((r for r in rows if r['arm']=='pretrained'),key=lambda r:r['seed'])


def checked(root,selected=False):
    root=Path(root)
    if sha(root/'protocol.json')!=(root/'protocol.sha256').read_text().strip():raise ValueError('Protocol hash changed')
    p=read_json(root/'protocol.json')
    if any(p.get(k)!=v for k,v in FIXED.items()):raise ValueError('Fixed protocol changed')
    for key in ('source_hashes','input_hashes','learner_hashes'):verify_hashes('/',p[key])
    if sha(root/'official-weights.pth')!=WEIGHT_SHA256:raise ValueError('Official weights changed')
    if selected:
        lock=read_json(root/'selection-lock.json')
        if lock['protocol_sha256']!=sha(root/'protocol.json') or lock['selection_sha256']!=sha(root/'selection.json'):raise ValueError('Selection changed')
        verify_hashes(root,lock['evidence_hashes']);primary_models(read_json(root/'selection.json'))
    return p


def prepare(prior,weights,output):
    prior,weights,output=map(lambda x:Path(x).resolve(),(prior,weights,output));old=read_json(prior/'protocol.json');parent=Path(old['parent'])
    if sha(weights)!=WEIGHT_SHA256 or tuple(loaded_detectors(prior))!=SEEDS:raise ValueError('Frozen starting inputs differ')
    rows=read_json(parent/'source-manifest.json');validate_manifest(rows,read_json(parent/'split.json')['assignment'])
    counts={s:sum(r['split']==s for r in rows) for s in ('train','validation','test')}
    if counts!={'train':696,'validation':227,'test':407}:raise ValueError('Split changed')
    seen=[r for r in rows if r['split'] in ('train','validation')];verify_data(old['data_dir'],seen)
    audit={}
    for split in ('train','validation'):
        rr=[r for r in seen if r['split']==split];cases={};near_border=close=0
        for r in rr:
            rgb,gt,gc=load_sample(old['data_dir'],r)
            if rgb.shape!=(224,224,3):raise ValueError('Expected native224RGB')
            c=cases.setdefault(r['case_id'],dict(images=0,class_counts=[0]*4));c['images']+=1
            c['class_counts']=(np.array(c['class_counts'])+np.bincount(gc,minlength=4)).tolist()
            near_border+=int(np.any((gt<6)|(gt>217),axis=1).sum())
            if len(gt)>1:
                from scipy.spatial import cKDTree
                close+=int((cKDTree(gt).query(gt,k=2)[0][:,1]<6).sum())
        audit[split]=dict(images=len(rr),cases=cases,centers_within6px_border=near_border,centers_with_neighbor_under6px=close)
    train=[r for r in rows if r['split']=='train'];prob=balanced_probabilities(train)
    audit['sampling']=dict(image_probabilities=prob.tolist(),images=[r['image'] for r in train],case_probability={c:float(sum(prob[i] for i,r in enumerate(train) if r['case_id']==c)) for c in audit['train']['cases']},draws_per_epoch=696,with_replacement=True)
    inputs={str(prior/n):sha(prior/n) for n in ('protocol.json','selection.json','selection-lock.json',*(f'detector-{s}.pt' for s in SEEDS))};inputs.update(old['input_hashes'])
    inputs.update({str(parent/n):sha(parent/n) for n in ('source-manifest.json','split.json','selection-lock.json')})
    inputs.update({str(ROOT/'work/ki67-capacity-20261114'/n):sha(ROOT/'work/ki67-capacity-20261114'/n) for n in ('deepliif-test-index.json','prospective-external-protocol.json')})
    source=[*sorted((ROOT/'src/pathology_edge').glob('*.py')),ROOT/'scripts/run_ki67_transfer.py']
    learner=[*(ROOT/'src/pathology_edge'/n for n in LEARNER_NAMES),ROOT/'tests/learner/test_merge_counterexample.py']
    output.mkdir(parents=True,exist_ok=False);shutil.copyfile(weights,output/'official-weights.pth');fresh_json(output/'data-audit.json',audit)
    frozen=output/'frozen_source/pathology_edge';frozen.mkdir(parents=True)
    for f in source:shutil.copyfile(f,frozen/f.name)
    p={**FIXED,'created_utc':utc(),'prior':str(prior),'parent':str(parent),'external':old['external'],'data_dir':old['data_dir'],
       'input_hashes':inputs,'source_hashes':{str(f):sha(f) for f in source},'learner_hashes':{str(f):sha(f) for f in learner},
       'data_audit_sha256':sha(output/'data-audit.json'),'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
       'initial_models':read_json(prior/'selection.json')['models'],'image_counts':counts,
       'sampling':'Equal case probability, uniform image within case,696 replacement draws/epoch',
       'encoder':'Frozen torchvision SqueezeNet1.1 ImageNet1K_V1 vs paired random frozen features; native size/ImageNet mean/std',
       'decoder':'16channel FPN+8channel native RGB;21665 trainable parameters',
       'loss':'unchanged sigma2radius6 maxGaussian center focal','augmentation':'pairedrot90/flips+RGB.9~1.1',
       'holdout_policy':'Always evaluate three prespecified primary selections, even unadopted diagnostics; never retune on heldout',
       'clinical_validation':False,'whole_wsi_validation':False,
       'environment':dict(python=platform.python_version(),torch=torch.__version__,numpy=np.__version__,platform=platform.platform())}
    fresh_json(output/'protocol.json',p);(output/'protocol.sha256').write_text(sha(output/'protocol.json')+'\n');return p


def infer_peaks(rgb,model):
    from .ki67_detection import validate_rgb
    validate_rgb(rgb);model.eval()
    with torch.inference_mode():heat=torch.sigmoid(model(tensor(rgb[None])))[0,0].numpy()
    if not np.isfinite(heat).all():raise ValueError('Nonfinite model output')
    xy,scores=peak_candidates(heat);keep=scores>=THRESHOLDS[0]
    return dict(points=xy[keep],scores=scores[keep])


def fit_worker(root,arm,seed):
    root=Path(root);p=checked(root);dest=root/job_name(arm,seed);dest.mkdir(exist_ok=False)
    fresh_json(dest/'started.json',dict(arm=arm,seed=seed,utc=utc(),protocol_sha256=sha(root/'protocol.json')))
    torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
    rows=[r for r in read_json(Path(p['parent'])/'source-manifest.json') if r['split'] in ('train','validation')];verify_data(p['data_dir'],rows)
    train=[];targets=[];val=[];refs=[];train_rows=[]
    for r in rows:
        rgb,gt,gc=load_sample(p['data_dir'],r)
        if r['split']=='train':train.append(rgb);targets.append(center_target(gt,rgb.shape[:2]));train_rows.append(r)
        else:val.append(rgb);refs.append(dict(image=r['image'],split='validation',case_id=r['case_id'],gt_points=gt,gt_classes=gc))
    train=np.stack(train);targets=np.stack(targets);prob=balanced_probabilities(train_rows)
    original,aconfig=loaded_detectors(p['prior'])[seed];torch.set_num_threads(2)
    for rgb,r in zip(val,refs):r['a_points']=predict_centers(rgb,original,aconfig)['points_xy']
    torch.set_num_threads(1);baseline=summarize_locations([{**r,'points':r['a_points']} for r in refs]);verify_initial_baseline(baseline,next(m for m in p['initial_models'] if m['seed']==seed))
    write_rows(dest/'validation.json.gz',[{k:(v.tolist() if isinstance(v,np.ndarray) else v) for k,v in r.items()} for r in refs]);del original
    torch.manual_seed(seed);rng=np.random.default_rng(seed)
    official=torch.load(root/'official-weights.pth',weights_only=True,map_location='cpu');state={k.removeprefix('features.'):v for k,v in official.items() if k.startswith('features.')}
    model=TransferCenterDetector(state if arm=='pretrained' else None);optimizer=torch.optim.Adam(model.decoder.parameters(),lr=.001)
    features=tensor_hashes(model.features.state_dict());head=tensor_hashes(model.decoder.state_dict())
    if arm=='pretrained' and features!=tensor_hashes(state):raise ValueError('Pretrained tensors differ')
    torch.save(model.features.state_dict(),dest/'features.pt')
    fresh_json(dest/'initial-tensors.json',dict(features=features,decoder=head,official_equal=features==tensor_hashes(state)))
    best=diagnostic=None;history=[];saved={};orders=[];start=time.perf_counter()
    for epoch in range(1,25):
        model.train();order=rng.choice(len(train),size=len(train),replace=True,p=prob);orders.append(order);loss_sum=0.
        for offset in range(0,len(order),8):
            ids=order[offset:offset+8];x=tensor(train[ids]);target=torch.from_numpy(targets[ids,None].copy())
            for i in range(len(ids)):
                k=int(rng.integers(4));x[i]=torch.rot90(x[i],k,(1,2));target[i]=torch.rot90(target[i],k,(1,2))
                for dim in (1,2):
                    if rng.random()<.5:x[i]=x[i].flip(dim);target[i]=target[i].flip(dim)
            x=(x*torch.from_numpy(rng.uniform(.9,1.1,(len(ids),3,1,1)).astype(np.float32))).clamp(0,1)
            optimizer.zero_grad(set_to_none=True);loss=center_focal_loss(model(x),target)
            if not torch.isfinite(loss):raise ValueError('Nonfinite loss')
            loss.backward();optimizer.step();loss_sum+=float(loss.detach())*len(ids)
        samples=[{**r,**infer_peaks(rgb,model)} for r,rgb in zip(refs,val)]
        saved[f'points_{epoch}']=np.concatenate([r['points'] for r in samples]).astype(np.uint16)
        saved[f'scores_{epoch}']=np.concatenate([r['scores'] for r in samples]).astype(np.float32)
        saved[f'offsets_{epoch}']=np.cumsum([0,*[len(r['points']) for r in samples]],dtype=np.int64)
        trials=configuration_trials(samples,epoch);outcome=choose_refit(trials,baseline);candidate=outcome['selected'];d=max(trials,key=trial_key)
        if diagnostic is None or trial_key(d)>trial_key(diagnostic):diagnostic=d;torch.save(model.decoder.state_dict(),dest/'diagnostic.pt')
        if candidate is not None and (best is None or trial_key(candidate)>trial_key(best)):best=candidate;torch.save(model.decoder.state_dict(),dest/'selected.pt')
        if tensor_hashes(model.features.state_dict())!=features:raise ValueError('Frozen encoder changed')
        history.append(dict(epoch=epoch,train_loss=loss_sum/len(train),feasible_trials=outcome['feasible_trials'],trials=trials))
        print(json.dumps(dict(arm=arm,seed=seed,epoch=epoch,loss=loss_sum/len(train),feasible=outcome['feasible_trials'],best_f1=d['case_macro_f1'],seconds=time.perf_counter()-start)),flush=True)
    np.savez_compressed(dest/'validation-peaks.npz',**saved);np.savez_compressed(dest/'training-orders.npz',orders=np.stack(orders));write_rows(dest/'trials.json.gz',history)
    torch.save(dict(decoder=model.decoder.state_dict(),optimizer=optimizer.state_dict(),torch_rng_state=torch.get_rng_state(),epochs=24),dest/'final-resume.pt');fresh_json(dest/'final-rng.json',rng.bit_generator.state)
    result=dict(arm=arm,seed=seed,epochs=24,selected=best,diagnostic=diagnostic,evaluation_trial=best if best is not None else diagnostic,
        evaluation_checkpoint='selected.pt' if best is not None else 'diagnostic.pt',baseline=baseline,a_config=aconfig,
        parameter_count=sum(t.numel() for t in model.parameters()),trainable_parameters=sum(t.numel() for t in model.parameters() if t.requires_grad),
        feature_tensors_unchanged=True,feasible_trials=sum(h['feasible_trials'] for h in history),training_selection_seconds=time.perf_counter()-start)
    fresh_json(dest/'result.json',result);checked(root)
    fresh_json(dest/'complete.json',dict(protocol_sha256=sha(root/'protocol.json'),evidence_hashes={f.name:sha(f) for f in dest.iterdir() if f.is_file()}));return result


def seal(root):
    root=Path(root);checked(root);rows=[];hashes={}
    for arm in ARMS:
        for seed in SEEDS:
            name=job_name(arm,seed);dest=root/name
            if not (dest/'complete.json').exists():raise ValueError('Missing worker '+name)
            c=read_json(dest/'complete.json')
            if c['protocol_sha256']!=sha(root/'protocol.json'):raise ValueError('Worker protocol differs')
            verify_hashes(dest,c['evidence_hashes']);r=read_json(dest/'result.json')
            if (r['arm'],r['seed'])!=(arm,seed):raise ValueError('Worker identity differs')
            rows.append(r);hashes.update({name+'/'+n:h for n,h in c['evidence_hashes'].items()});hashes[name+'/complete.json']=sha(dest/'complete.json')
    primary_models(dict(models=rows))
    for seed in SEEDS:
        a=root/job_name('pretrained',seed);b=root/job_name('random',seed)
        if read_json(a/'initial-tensors.json')['decoder']!=read_json(b/'initial-tensors.json')['decoder'] or not np.array_equal(np.load(a/'training-orders.npz')['orders'],np.load(b/'training-orders.npz')['orders']):raise ValueError('Unpaired initial head or sampled images')
    fresh_json(root/'selection.json',dict(models=rows,test_used_for_selection=False,external_used_for_selection=False))
    fresh_json(root/'selection-lock.json',dict(created_utc=utc(),protocol_sha256=sha(root/'protocol.json'),selection_sha256=sha(root/'selection.json'),evidence_hashes=hashes))
    checked(root,selected=True);return rows
