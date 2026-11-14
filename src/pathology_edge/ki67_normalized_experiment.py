"""Fixed normalized-width study: six workers, one prespecified primary arm."""
from pathlib import Path
import json
import platform
import shutil
import subprocess
import time
import numpy as np
import torch
from .ki67_normalized_centers import NormalizedCenterDetector
from .ki67_centers import center_target,center_focal_loss,peak_candidates,predict_centers
from .ki67_center_refit import configuration_trials,choose_refit,verify_initial_baseline,tensor,THRESHOLDS,EPOCHS
from .ki67_center_experiment import loaded_detectors
from .ki67_union import retain_candidates,summarize_locations,trial_key
from .ki67_union_experiment import SEEDS,DISTANCES,FLOORS,utc,write_rows
from .ki67_experiment import read_json,fresh_json,sha,verify_hashes,validate_manifest,verify_data,load_sample

ROOT=Path(__file__).resolve().parents[2]
WIDTHS=(4,16)
FIXED=dict(schema='ki67-normalized.v1',seeds=list(SEEDS),widths=list(WIDTHS),primary_width=16,epochs=24,
           learning_rate=.001,batch_size=8,torch_threads=1,baseline_threads=2,thresholds=list(THRESHOLDS),distances=list(DISTANCES),floors=FLOORS)


def job_name(width,seed):
    if type(width) is not int or width not in WIDTHS or type(seed) is not int or seed not in SEEDS:
        raise ValueError('Unregistered width/seed job')
    return f'width{width}-seed{seed}'


def primary_models(selection):
    records=selection.get('models',[])
    expected={(w,s) for w in WIDTHS for s in SEEDS}
    if len(records)!=6 or {(m.get('width'),m.get('seed')) for m in records}!=expected:
        raise ValueError('Require all six distinct arm/seed records')
    for m in records:
        job_name(m['width'],m['seed'])
        if m.get('additional_epochs')!=EPOCHS:raise ValueError('Incomplete worker')
        selected=m.get('selected')
        if selected is not None:
            if (type(selected.get('epoch')) is not int or not 1<=selected['epoch']<=EPOCHS or selected.get('split')!='validation'
                or selected['config']['threshold'] not in THRESHOLDS or selected['config']['min_distance'] not in DISTANCES
                or m.get('checkpoint')!='selected.pt'):
                raise ValueError('Invalid selected normalized model')
        elif m.get('checkpoint') is not None:raise ValueError('Unselected checkpoint')
    return sorted((r for r in records if r['width']==16),key=lambda r:r['seed'])


def checked(root,selected=False):
    root=Path(root)
    if sha(root/'protocol.json')!=(root/'protocol.sha256').read_text().strip():raise ValueError('Protocol hash changed')
    p=read_json(root/'protocol.json')
    if any(p.get(k)!=v for k,v in FIXED.items()):raise ValueError('Fixed protocol changed')
    for key in ('source_hashes','input_hashes'):verify_hashes('/',p[key])
    if selected:
        lock=read_json(root/'selection-lock.json')
        if lock['protocol_sha256']!=sha(root/'protocol.json') or lock['selection_sha256']!=sha(root/'selection.json'):raise ValueError('Selection hash changed')
        verify_hashes(root,lock['evidence_hashes']);primary_models(read_json(root/'selection.json'))
    return p


def prepare(prior,output):
    prior,output=Path(prior).resolve(),Path(output).resolve();old=read_json(prior/'protocol.json');parent=Path(old['parent'])
    if tuple(loaded_detectors(prior))!=SEEDS:raise ValueError('Expected all original seeds')
    original=read_json(prior/'selection.json')['models']
    rows=read_json(parent/'source-manifest.json');validate_manifest(rows,read_json(parent/'split.json')['assignment'])
    counts={s:sum(r['split']==s for r in rows) for s in ('train','validation','test')}
    if counts!={'train':696,'validation':227,'test':407}:raise ValueError('Fixed split changed')
    verify_data(old['data_dir'],[r for r in rows if r['split'] in ('train','validation')])
    if shutil.disk_usage(output.parent).free<150_000_000:raise ValueError('Need150MB evidence space')
    inputs={str(prior/n):sha(prior/n) for n in ('protocol.json','selection.json','selection-lock.json',*(f'detector-{s}.pt' for s in SEEDS))};inputs.update(old['input_hashes'])
    source=[*sorted((ROOT/'src/pathology_edge').glob('*.py')),ROOT/'scripts/run_ki67_normalized.py']
    output.mkdir(parents=True,exist_ok=False);frozen=output/'frozen_source/pathology_edge';frozen.mkdir(parents=True)
    for f in source:(frozen/f.name).write_bytes(f.read_bytes())
    p={**FIXED,'created_utc':utc(),'prior':str(prior),'parent':str(parent),'external':old['external'],'data_dir':old['data_dir'],
       'input_hashes':inputs,'source_hashes':{str(f):sha(f) for f in source},'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
       'initial_models':original,'image_counts':counts,'architecture':'TinyUNet width4/16, GroupNorm groups=max(1,channels//4) before LeakyReLU.1; headbias−2.19',
       'initialization':'From scratch same seed; primarywidth16 fixed before validation; width4 diagnostic ablation',
       'loss':'existing maxGaussian sigma2radius6 and center focal loss','augmentation':'pairedrot90/flips and per-imageRGB[.9,1.1]',
       'optimizer':'fresh Adam.001,24epochs,batch8; final optimizer and RNG retained','selection':'unchanged FP/FN and recall floors; all6lock before holdout',
       'scope':'Repeatedly used Patherea validation; eligible primary only reused test407/BCData133, separate prospective DeepLIIF study',
       'clinical_validation':False,'whole_wsi_validation':False,'environment':dict(python=platform.python_version(),torch=torch.__version__,numpy=np.__version__,platform=platform.platform())}
    fresh_json(output/'protocol.json',p);(output/'protocol.sha256').write_text(sha(output/'protocol.json')+'\n');return p


def infer_peaks(rgb,model):
    from .ki67_detection import validate_rgb
    validate_rgb(rgb)
    if not isinstance(model,NormalizedCenterDetector) or not all(torch.isfinite(v).all() for v in model.state_dict().values()):raise ValueError('Expected finite normalized model')
    model.eval()
    with torch.inference_mode():heat=torch.sigmoid(model(tensor(rgb[None])))[0,0].cpu().numpy()
    pt,sc=peak_candidates(heat);keep=sc>=THRESHOLDS[0]
    return dict(points=pt[keep],scores=sc[keep])


def fit_worker(root,width,seed):
    root=Path(root);p=checked(root);name=job_name(width,seed);dest=root/name;dest.mkdir(exist_ok=False)
    fresh_json(dest/'started.json',dict(width=width,seed=seed,utc=utc(),protocol_sha256=sha(root/'protocol.json')))
    torch.set_num_threads(p['torch_threads']);torch.use_deterministic_algorithms(True)
    rows=[r for r in read_json(Path(p['parent'])/'source-manifest.json') if r['split'] in ('train','validation')];verify_data(p['data_dir'],rows)
    train=[];targets=[];val=[];refs=[]
    for r in rows:
        rgb,gt,gc=load_sample(p['data_dir'],r)
        if rgb.shape!=(224,224,3):raise ValueError('Expected native224RGB')
        if r['split']=='train':train.append(rgb);targets.append(center_target(gt,rgb.shape[:2]))
        else:val.append(rgb);refs.append(dict(image=r['image'],split='validation',case_id=r['case_id'],gt_points=gt,gt_classes=gc))
    train=np.stack(train);targets=np.stack(targets)
    original,aconfig=loaded_detectors(p['prior'])[seed]
    torch.set_num_threads(p['baseline_threads'])
    for rgb,r in zip(val,refs):r['a_points']=predict_centers(rgb,original,aconfig)['points_xy']
    torch.set_num_threads(p['torch_threads'])
    baseline=summarize_locations([{**r,'points':r['a_points']} for r in refs])
    verify_initial_baseline(baseline,next(m for m in p['initial_models'] if m['seed']==seed))
    write_rows(dest/'validation.json.gz',[{k:(v.tolist() if isinstance(v,np.ndarray) else v) for k,v in r.items()} for r in refs])
    del original
    torch.manual_seed(seed);rng=np.random.default_rng(seed);model=NormalizedCenterDetector(width);optimizer=torch.optim.Adam(model.parameters(),lr=p['learning_rate'])
    initial_hashes={k:__import__('hashlib').sha256(v.detach().numpy().tobytes()).hexdigest() for k,v in model.state_dict().items()}
    fresh_json(dest/'initial-tensors.json',initial_hashes)
    best=diagnostic=None;history=[];saved={};start=time.perf_counter()
    for epoch in range(1,EPOCHS+1):
        model.train();order=rng.permutation(len(train));loss_sum=0.
        for offset in range(0,len(order),p['batch_size']):
            ids=order[offset:offset+p['batch_size']];x=tensor(train[ids]);target=torch.from_numpy(targets[ids,None].copy())
            for i in range(len(ids)):
                k=int(rng.integers(4));x[i]=torch.rot90(x[i],k,(1,2));target[i]=torch.rot90(target[i],k,(1,2))
                for dim in (1,2):
                    if rng.random()<.5:x[i]=x[i].flip(dim);target[i]=target[i].flip(dim)
            factors=torch.from_numpy(rng.uniform(.9,1.1,(len(ids),3,1,1)).astype(np.float32));x=(x*factors).clamp(0,1)
            optimizer.zero_grad(set_to_none=True);loss=center_focal_loss(model(x),target)
            if not torch.isfinite(loss):raise ValueError('Nonfinite loss')
            loss.backward();optimizer.step();loss_sum+=float(loss.detach())*len(ids)
        samples=[{**r,**infer_peaks(rgb,model)} for r,rgb in zip(refs,val)]
        saved[f'points_{epoch}']=np.concatenate([r['points'] for r in samples]).astype(np.uint16)
        saved[f'scores_{epoch}']=np.concatenate([r['scores'] for r in samples]).astype(np.float32)
        saved[f'offsets_{epoch}']=np.cumsum([0,*[len(r['points']) for r in samples]],dtype=np.int64)
        trials=configuration_trials(samples,epoch);outcome=choose_refit(trials,baseline);candidate=outcome['selected'];d=max(trials,key=trial_key)
        if diagnostic is None or trial_key(d)>trial_key(diagnostic):diagnostic=d;torch.save(model.state_dict(),dest/'diagnostic.pt')
        if candidate is not None and (best is None or trial_key(candidate)>trial_key(best)):best=candidate;torch.save(model.state_dict(),dest/'selected.pt')
        history.append(dict(epoch=epoch,train_loss=loss_sum/len(train),feasible_trials=outcome['feasible_trials'],trials=trials))
        print(json.dumps(dict(width=width,seed=seed,epoch=epoch,loss=loss_sum/len(train),feasible=outcome['feasible_trials'],best_f1=d['case_macro_f1'],best_recall=d['case_macro_recall'],seconds=time.perf_counter()-start)),flush=True)
    np.savez_compressed(dest/'validation-peaks.npz',**saved);write_rows(dest/'trials.json.gz',history)
    torch.save(dict(model=model.state_dict(),optimizer=optimizer.state_dict(),torch_rng_state=torch.get_rng_state(),epochs=EPOCHS),dest/'final-resume.pt');fresh_json(dest/'final-rng.json',rng.bit_generator.state)
    result=dict(width=width,seed=seed,additional_epochs=EPOCHS,selected=best,diagnostic=diagnostic,baseline=baseline,a_config=aconfig,
                feasible_trials=sum(v['feasible_trials'] for v in history),checkpoint='selected.pt' if best else None,diagnostic_checkpoint='diagnostic.pt',
                parameter_count=sum(t.numel() for t in model.parameters()),training_selection_seconds=time.perf_counter()-start)
    fresh_json(dest/'result.json',result);checked(root)
    fresh_json(dest/'complete.json',dict(protocol_sha256=sha(root/'protocol.json'),evidence_hashes={f.name:sha(f) for f in dest.iterdir() if f.is_file()}));return result


def seal(root):
    root=Path(root);checked(root);records=[];hashes={}
    # Complete verification precedes writing either selection artifact.
    for width in WIDTHS:
        for seed in SEEDS:
            name=job_name(width,seed);dest=root/name
            if not (dest/'complete.json').exists():raise ValueError('Missing completed worker: '+name)
            complete=read_json(dest/'complete.json')
            if complete['protocol_sha256']!=sha(root/'protocol.json'):raise ValueError('Worker protocol differs')
            verify_hashes(dest,complete['evidence_hashes']);r=read_json(dest/'result.json')
            if (r['width'],r['seed'])!=(width,seed):raise ValueError('Worker identity differs')
            records.append(r);hashes.update({name+'/'+n:h for n,h in complete['evidence_hashes'].items()});hashes[name+'/complete.json']=sha(dest/'complete.json')
    primary_models({'models':records})
    fresh_json(root/'selection.json',dict(models=records,primary_width=16,test_used_for_selection=False,external_used_for_selection=False))
    fresh_json(root/'selection-lock.json',dict(created_utc=utc(),protocol_sha256=sha(root/'protocol.json'),selection_sha256=sha(root/'selection.json'),evidence_hashes=hashes))
    checked(root,selected=True);return records
