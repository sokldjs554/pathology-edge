"""Fixed warm-start detector refit with fresh optimizer, unchanged recall gates."""
import io
from pathlib import Path
import platform
import shutil
import subprocess
import time
import numpy as np
from PIL import Image
import torch
from .ki67_centers import CenterDetector,center_target,center_focal_loss,peak_candidates,predict_centers
from .ki67_union import retain_candidates,summarize_locations,choose_trial,trial_key
from .ki67_union_experiment import SEEDS,DISTANCES,FLOORS,utc,write_rows,read_rows,validate_selection
from .ki67_localization_experiment import stability_summary,test_criteria
from .ki67_center_experiment import loaded_detectors,score_external
from .ki67_experiment import read_json,fresh_json,sha,verify_hashes,validate_manifest,verify_data,load_sample,load_models,summarize
from .ki67_cnn import classify_centers
from .ki67_external import fetch_entry,download_url,validate_external_entries

ROOT=Path(__file__).resolve().parents[2]
THRESHOLDS=(.01,.02,.03,.05,.075,.1,.15,.2,.3,.5,.7,.9)
EPOCHS=24


def refit_optimizer(model):
    if not isinstance(model,CenterDetector) or not all(torch.isfinite(t).all() for t in model.state_dict().values()):
        raise ValueError('Expected finite pretrained CenterDetector')
    return torch.optim.Adam(model.parameters(),lr=.001)


def valid_epoch(epoch):
    if isinstance(epoch,bool) or not isinstance(epoch,(int,np.integer)) or not 0<=epoch<=EPOCHS:
        raise ValueError('Expected integer additional epoch0..24')


def choose_refit(trials,baseline):
    for t in trials:valid_epoch(t['epoch'])
    return choose_trial([t for t in trials if t['epoch']>0],baseline,FLOORS)


def configuration_trials(samples,epoch):
    valid_epoch(epoch)
    if not samples or any(r.get('split')!='validation' for r in samples):raise ValueError('Validation only')
    trials=[]
    for distance in DISTANCES:
        decoded=[retain_candidates(r['points'],r['scores'],THRESHOLDS[0],distance) for r in samples]
        for threshold in THRESHOLDS:
            rows=[{**r,'points':d['points_xy'][d['scores']>=threshold]} for r,d in zip(samples,decoded)]
            trials.append(dict(split='validation',epoch=int(epoch),config=dict(threshold=threshold,min_distance=distance),**summarize_locations(rows)))
    return trials


def prepare(prior,output):
    prior,output=Path(prior).resolve(),Path(output).resolve();old=read_json(prior/'protocol.json');parent=Path(old['parent'])
    detectors=loaded_detectors(prior)
    if tuple(detectors)!=SEEDS:raise ValueError('Expected all three initial detectors')
    original=read_json(prior/'selection.json')['models']
    if any(m['best_epoch']!=16 for m in original):raise ValueError('Expected reviewed epoch16 initial weights')
    rows=read_json(parent/'source-manifest.json');validate_manifest(rows,read_json(parent/'split.json')['assignment'])
    counts={s:sum(r['split']==s for r in rows) for s in ('train','validation','test')}
    if counts!={'train':696,'validation':227,'test':407}:raise ValueError('Unexpected fixed split')
    verify_data(old['data_dir'],[r for r in rows if r['split'] in ('train','validation')])
    if shutil.disk_usage(output.parent).free<80_000_000:raise ValueError('Need80MB for compressed evidence')
    inputs={str(prior/n):sha(prior/n) for n in ('protocol.json','selection.json','selection-lock.json',*(f'detector-{s}.pt' for s in SEEDS))};inputs.update(old['input_hashes'])
    source=[*sorted((ROOT/'src/pathology_edge').glob('*.py')),ROOT/'scripts/run_ki67_center_refit.py']
    output.mkdir(parents=True,exist_ok=False);frozen=output/'frozen_source/pathology_edge';frozen.mkdir(parents=True)
    for path in source:(frozen/path.name).write_bytes(path.read_bytes())
    p=dict(schema='ki67-center-refit.v1',created_utc=utc(),prior=str(prior),parent=str(parent),external=old['external'],data_dir=old['data_dir'],
        input_hashes=inputs,source_hashes={str(s):sha(s) for s in source},source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        seeds=list(SEEDS),epochs=EPOCHS,learning_rate=.001,batch_size=8,torch_threads=2,thresholds=list(THRESHOLDS),distances=list(DISTANCES),floors=FLOORS,image_counts=counts,
        initial_epochs=16,initial_models=original,optimizer='Fresh Adam; original optimizer/RNG unavailable. Not uninterrupted40epoch training.',
        architecture='Unchanged CenterDetector TinyUNet width4/7537params/LeakyReLU.1',loss='Unchanged center_focal_loss, max Gaussian sigma2/radius6',
        augmentation='Same train-only pairedrot90/flips, per-image RGB[.9,1.1]',seed_policy='Fresh torch and NumPy RNG equal each model seed',
        selection='Epoch1..24 only; unchanged jointFPFN/LoG recall floors/.9everycase; F1,recall,earlier epoch,higher threshold,larger spacing. Epoch0 diagnostic control.',
        exposure='Common split/hash manifest metadata read; test labels not used. Only train/validation images and annotations parsed before all three selections lock; inherited holdout files opaque hashed only.',
        scope='Fixed refit on repeatedly used validation, eligible-only reused test407/BCData133; not fresh external, clinical or whole-WSI evidence.',
        classifier_training=False,clinical_validation=False,whole_wsi_validation=False,
        environment=dict(python=platform.python_version(),torch=torch.__version__,numpy=np.__version__,platform=platform.platform()))
    fresh_json(output/'protocol.json',p);(output/'protocol.sha256').write_text(sha(output/'protocol.json')+'\n');return p


def checked(root,selected=False):
    root=Path(root)
    if sha(root/'protocol.json')!=(root/'protocol.sha256').read_text().strip():raise ValueError('Protocol hash changed')
    p=read_json(root/'protocol.json')
    for field in ('input_hashes','source_hashes'):verify_hashes('/',p[field])
    fixed=dict(schema='ki67-center-refit.v1',seeds=list(SEEDS),epochs=EPOCHS,learning_rate=.001,batch_size=8,torch_threads=2,thresholds=list(THRESHOLDS),distances=list(DISTANCES),floors=FLOORS)
    if any(p.get(k)!=v for k,v in fixed.items()):raise ValueError('Protocol configuration changed')
    if selected:
        lock=read_json(root/'selection-lock.json')
        if lock['protocol_sha256']!=sha(root/'protocol.json') or lock['selection_sha256']!=sha(root/'selection.json'):raise ValueError('Selection hash changed')
        verify_hashes(root,lock['evidence_hashes'])
        for m in validate_selection(read_json(root/'selection.json')):
            valid_epoch(m['selected']['epoch'])
            if m['selected']['epoch']==0 or m['selected']['config']['threshold'] not in THRESHOLDS or m['selected']['config']['min_distance'] not in DISTANCES:raise ValueError('Invalid adopted refit')
    return p


def infer_peaks(rgb,model):
    heat=predict_centers(rgb,model,dict(threshold=.01,min_distance=4))['probability_map']
    points,scores=peak_candidates(heat);keep=scores>=THRESHOLDS[0]
    return dict(points=points[keep],scores=scores[keep])


def tensor(images):return torch.from_numpy(images.transpose(0,3,1,2).copy()).float()/255


def verify_initial_baseline(baseline,expected):
    for key in ('case_macro_f1','case_macro_recall'):
        if not np.isclose(baseline[key],expected['validation_'+key],rtol=0,atol=1e-12):
            raise ValueError('Epoch0 differs from original validation baseline')


def train_seed(model,a_config,train_images,targets,val_images,refs,seed,root,p):
    torch.manual_seed(seed);rng=np.random.default_rng(seed);optimizer=refit_optimizer(model)
    initial=torch.load(Path(p['prior'])/f'detector-{seed}.pt',weights_only=True,map_location='cpu')
    if any(not torch.equal(v,model.state_dict()[k]) for k,v in initial.items()):raise ValueError('Initial weights differ')
    best=diagnostic=baseline=None;history=[];saved={};started=time.perf_counter()
    for epoch in range(EPOCHS+1):
        loss_sum=0.
        if epoch:
            model.train();order=rng.permutation(len(train_images))
            for start in range(0,len(order),p['batch_size']):
                ids=order[start:start+p['batch_size']];x=tensor(train_images[ids]);target=torch.from_numpy(targets[ids,None].copy())
                for i in range(len(ids)):
                    k=int(rng.integers(4));x[i]=torch.rot90(x[i],k,(1,2));target[i]=torch.rot90(target[i],k,(1,2))
                    for dim in (1,2):
                        if rng.random()<.5:x[i]=x[i].flip(dim);target[i]=target[i].flip(dim)
                factors=torch.from_numpy(rng.uniform(.9,1.1,(len(ids),3,1,1)).astype(np.float32));x=(x*factors).clamp(0,1)
                optimizer.zero_grad(set_to_none=True);loss=center_focal_loss(model(x),target)
                if not torch.isfinite(loss):raise ValueError('Nonfinite training loss')
                loss.backward();optimizer.step();loss_sum+=float(loss.detach())*len(ids)
        model.eval();samples=[{**r,**infer_peaks(rgb,model)} for r,rgb in zip(refs,val_images)]
        if epoch==0:
            for r in samples:r['a_points']=retain_candidates(r['points'],r['scores'],**a_config)['points_xy']
            baseline=summarize_locations([{**r,'points':r['a_points']} for r in samples])
            verify_initial_baseline(baseline,next(m for m in p['initial_models'] if m['seed']==seed))
            serial=[{k:(v.tolist() if isinstance(v,np.ndarray) else v) for k,v in r.items() if k not in ('points','scores')} for r in samples]
            write_rows(root/f'validation-{seed}.json.gz',serial)
        saved[f'points_{epoch}']=np.concatenate([r['points'] for r in samples]).astype(np.uint16)
        saved[f'scores_{epoch}']=np.concatenate([r['scores'] for r in samples]).astype(np.float32)
        saved[f'offsets_{epoch}']=np.cumsum([0,*[len(r['points']) for r in samples]],dtype=np.int64)
        trials=configuration_trials(samples,epoch);outcome=choose_refit(trials,baseline);candidate=outcome['selected'];d=max(trials,key=trial_key)
        if diagnostic is None or trial_key(d)>trial_key(diagnostic):diagnostic=d;torch.save(model.state_dict(),root/f'diagnostic-{seed}.pt')
        if candidate is not None and (best is None or trial_key(candidate)>trial_key(best)):best=candidate;torch.save(model.state_dict(),root/f'detector-{seed}.pt')
        history.append(dict(epoch=epoch,train_loss=loss_sum/len(train_images) if epoch else None,feasible_trials=outcome['feasible_trials'],trials=trials))
        print(__import__('json').dumps(dict(seed=seed,additional_epoch=epoch,loss=history[-1]['train_loss'],feasible=outcome['feasible_trials'],best_f1=d['case_macro_f1'],best_recall=d['case_macro_recall'],seconds=time.perf_counter()-started)),flush=True)
    np.savez_compressed(root/f'validation-peaks-{seed}.npz',**saved);write_rows(root/f'trials-{seed}.json.gz',history)
    torch.save(dict(model=model.state_dict(),optimizer=optimizer.state_dict(),torch_rng_state=torch.get_rng_state(),completed_additional_epochs=EPOCHS),root/f'final-resume-{seed}.pt')
    fresh_json(root/f'final-rng-{seed}.json',rng.bit_generator.state)
    return dict(seed=seed,selected=best,diagnostic=diagnostic,baseline=baseline,epoch0_diagnostic=max(history[0]['trials'],key=trial_key),a_config=a_config,
        feasible_trials=sum(h['feasible_trials'] for h in history),checkpoint=f'detector-{seed}.pt' if best else None,diagnostic_checkpoint=f'diagnostic-{seed}.pt',
        initial_checkpoint_sha256=sha(Path(p['prior'])/f'detector-{seed}.pt'),initial_weights_equal=True,additional_epochs=EPOCHS,parameter_count=sum(t.numel() for t in model.parameters()),training_selection_seconds=time.perf_counter()-started)


def fit(root):
    root=Path(root);p=checked(root);fresh_json(root/'fit-started.json',dict(created_utc=utc()))
    torch.set_num_threads(p['torch_threads']);torch.use_deterministic_algorithms(True)
    rows=[r for r in read_json(Path(p['parent'])/'source-manifest.json') if r['split'] in ('train','validation')];verify_data(p['data_dir'],rows)
    train_images=[];targets=[];val_images=[];refs=[]
    for r in rows:
        rgb,gt,gc=load_sample(p['data_dir'],r)
        if rgb.shape!=(224,224,3):raise ValueError('Expected native224RGB')
        if r['split']=='train':train_images.append(rgb);targets.append(center_target(gt,rgb.shape[:2]))
        else:val_images.append(rgb);refs.append(dict(image=r['image'],split='validation',case_id=r['case_id'],gt_points=gt,gt_classes=gc))
    train_images=np.stack(train_images);targets=np.stack(targets)
    models=[train_seed(model,config,train_images,targets,val_images,refs,seed,root,p) for seed,(model,config) in loaded_detectors(p['prior']).items()]
    fresh_json(root/'selection.json',dict(models=models,test_used_for_selection=False,external_used_for_selection=False))
    evidence={f.name:sha(f) for f in root.iterdir() if f.suffix in ('.pt','.npz','.gz') or f.name.startswith('final-rng-')}
    fresh_json(root/'selection-lock.json',dict(created_utc=utc(),protocol_sha256=sha(root/'protocol.json'),selection_sha256=sha(root/'selection.json'),evidence_hashes=evidence))
    checked(root,selected=True);return models


def evaluate(root,external=False):
    root=Path(root);p=checked(root,selected=True);models=read_json(root/'selection.json')['models'];eligible=validate_selection({'models':models});tag='external' if external else 'internal'
    if not eligible:
        fresh_json(root/(tag+'-not-run.json'),dict(reason='No eligible seed; no holdout inference',new_inference_images=0))
        if not external:fresh_json(root/'stability.json',stability_summary([dict(seed=m['seed'],eligible=False,test_passed=False) for m in models]))
        return
    fresh_json(root/(tag+'-started.json'),dict(created_utc=utc(),selection_lock_sha256=sha(root/'selection-lock.json')))
    torch.set_num_threads(p['torch_threads']);a_models=loaded_detectors(p['prior']);b_models={}
    for m in eligible:
        model=CenterDetector();model.load_state_dict(torch.load(root/m['checkpoint'],weights_only=True,map_location='cpu'));b_models[m['seed']]=model.eval()
    classifiers=load_models(p['parent'],read_json(Path(p['parent'])/'selection-lock.json'))
    if external:
        previous=Path(p['external']);refs=read_json(previous/'private-predictions.json');entries={r['name']:r for r in read_json(previous/'entries.json')};inputs={r['name']:r for r in read_json(previous/'input-manifest.json')}
        names=validate_external_entries(list(entries.values()));refmap={r['image']:r for r in refs}
        if len(refs)!=133 or set(refmap)!=set(names):raise ValueError('External correspondence changed')
        url=download_url();rows=[refmap[n] for n in names]
    else:rows=[r for r in read_json(Path(p['parent'])/'source-manifest.json') if r['split']=='test'];verify_data(p['data_dir'],rows)
    outputs={m['seed']:{arm:[] for arm in ('A','B')} for m in eligible}
    for index,r in enumerate(rows):
        if external:
            raw,meta=fetch_entry(url,entries[r['image']])
            if meta['sha256']!=inputs[r['image']]['sha256']:raise ValueError('External RGB hash changed')
            image=Image.open(io.BytesIO(raw))
            if image.mode!='RGB' or image.size!=(640,640):raise ValueError('Expected native640RGB')
            rgb=np.asarray(image);gt=np.asarray(r['gt_points']).reshape(-1,2);gc=np.asarray(r['gt_classes'])
        else:rgb,gt,gc=load_sample(p['data_dir'],r)
        for m in eligible:
            seed=m['seed'];a,config=a_models[seed];arms=dict(A=predict_centers(rgb,a,config)['points_xy'])
            peaks=infer_peaks(rgb,b_models[seed]);arms['B']=retain_candidates(peaks['points'],peaks['scores'],**m['selected']['config'])['points_xy']
            for arm,xy in arms.items():
                row=dict(image=r['image'],points=xy.tolist(),gt_points=gt.tolist(),gt_classes=gc.tolist(),classes={})
                if not external:row['case_id']=r['case_id']
                for name,classifier in classifiers.items():row['classes'][name]=classify_centers(rgb,xy,classifier).argmax(1).tolist()
                outputs[seed][arm].append(row)
        if (index+1)%25==0:print(tag,index+1,flush=True)
    decisions={}
    for seed,arms in outputs.items():
        folder=root/f'seed-{seed}'/tag;folder.mkdir(parents=True,exist_ok=False)
        for arm,rs in arms.items():
            dest=folder/arm;dest.mkdir();write_rows(dest/'predictions.json.gz',rs)
            scores={name:(score_external(rs,name) if external else summarize(rs,name)) for name in classifiers}
            fresh_json(dest/'results.json',dict(seed=seed,arm=arm,image_count=len(rs),classifiers=scores,predictions_sha256=sha(dest/'predictions.json.gz'),selection_lock_sha256=sha(root/'selection-lock.json'),scope=p['scope']))
        if not external:
            normalized=lambda rs:[{**r,'points':np.asarray(r['points']).reshape(-1,2),'gt_points':np.asarray(r['gt_points']).reshape(-1,2)} for r in rs]
            a=summarize_locations(normalized(arms['A']));b=summarize_locations(normalized(arms['B']));criteria=test_criteria(a,b);decisions[seed]=dict(seed=seed,eligible=True,test_passed=all(criteria.values()),criteria=criteria,A=a,B=b)
    if not external:fresh_json(root/'stability.json',stability_summary([decisions.get(m['seed'],dict(seed=m['seed'],eligible=False,test_passed=False)) for m in models]))
    checked(root,selected=True)
