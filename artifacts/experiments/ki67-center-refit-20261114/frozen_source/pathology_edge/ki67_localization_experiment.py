"""Fixed three-seed candidate-native correspondence/localization experiment."""
from collections import defaultdict
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
from .ki67_localization import (LocalizationGate,reflected_context,transform_sample,proxy_targets,localization_loss,predict_localized)
from .ki67_union import merge_proposals,retain_candidates,summarize_locations,choose_trial,trial_key
from .ki67_union_experiment import SEEDS,THRESHOLDS,DISTANCES,FLOORS,LEARNED_CONFIG,LOG_CONFIG,write_rows,read_rows,utc,validate_selection
from .ki67_centers import predict_centers,peak_candidates,decode_candidates
from .ki67_detection import response_map,select_peaks
from .ki67_center_experiment import loaded_detectors,score_external
from .ki67_experiment import read_json,fresh_json,sha,verify_hashes,verify_data,validate_manifest,load_sample,load_models,summarize
from .ki67_cnn import classify_centers
from .ki67_external import fetch_entry,download_url,validate_external_entries

ROOT=Path(__file__).resolve().parents[2]


def prepare(prior,output):
    prior,output=Path(prior).resolve(),Path(output).resolve();old=read_json(prior/'protocol.json');parent=Path(old['parent'])
    if tuple(loaded_detectors(prior))!=SEEDS:raise ValueError('Expected all three proposal seeds')
    rows=read_json(parent/'source-manifest.json');validate_manifest(rows,read_json(parent/'split.json')['assignment'])
    counts={s:sum(r['split']==s for r in rows) for s in ('train','validation','test')}
    if counts!={'train':696,'validation':227,'test':407}:raise ValueError('Unexpected split')
    verify_data(old['data_dir'],[r for r in rows if r['split']!='test'])
    if shutil.disk_usage(output.parent).free<100_000_000:raise ValueError('Need100MB for compressed evidence and model files')
    inputs={str(prior/n):sha(prior/n) for n in ('protocol.json','selection.json','selection-lock.json',*(f'detector-{s}.pt' for s in SEEDS))};inputs.update(old['input_hashes'])
    source=[*sorted((ROOT/'src/pathology_edge').glob('*.py')),ROOT/'scripts/run_ki67_localization.py']
    output.mkdir(parents=True,exist_ok=False);frozen=output/'frozen_source/pathology_edge';frozen.mkdir(parents=True)
    for path in source:(frozen/path.name).write_bytes(path.read_bytes())
    p=dict(schema='ki67-localization.v1',created_utc=utc(),prior=str(prior),parent=str(parent),external=old['external'],data_dir=old['data_dir'],
      input_hashes=inputs,source_hashes={str(s):sha(s) for s in source},source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
      seeds=list(SEEDS),epochs=12,batch_size=64,learning_rate=.001,torch_threads=2,thresholds=list(THRESHOLDS),distances=list(DISTANCES),floors=FLOORS,
      learned_config=LEARNED_CONFIG,log_config=LOG_CONFIG,image_counts=counts,continuous_radius_px=12.,crop_size=32,context_size=33,
      architecture='RGB conv8/16/32 each2x3x3+LeakyReLU.1+pool2; flatten512; metadata4->16; two528->2 heads; zero offset head',
      metadata=['learned_heat','LoG_response','source_learned','source_LoG'],normalization='all training candidates only, per-seed mean/std; constant columns scale1',
      proxy_labels='nearest annotation<=12 positive neighborhood; >12 and interior24 negative proxy max256/image; no empty-GT negatives; not expert background labels',
      sampling='equal binary labels; uniform cases, uniform represented GT for positive, then candidate; no GT-center/jitter crops; fixed negative cap once per seed',
      augmentation='reflect33context centered16; rot90/flips of context and offset then[:32,:32]; RGB[.9,1.1] train only',
      loss='mean CE + positive-only mean SmoothL1(beta.25) on bounded offsets/12',
      rounding='continuous radial bound12; np.rint nearest-even + clip toimage; actual integer displacement may add at mostsqrt(.5)px',
      selection='same original jointFP/FN and LoG recall floors,case>=.9A; corrected centers only; F1,recall,earlier epoch,higher cutoff,larger distance',
      ablation='A existing; U union; S learned scorer at original centers; R same scorer+corrected centers, same checkpoint/cutoff/spacing',
      scope='Exploratory repeatedly used validation; eligible-only reused test407/BCData133; no fresh external/clinical/whole-WSI claim',
      opaque_holdout_hashing_only_before_lock=True,clinical_validation=False,whole_wsi_validation=False,
      environment=dict(python=platform.python_version(),torch=torch.__version__,numpy=np.__version__,platform=platform.platform()))
    fresh_json(output/'protocol.json',p);(output/'protocol.sha256').write_text(sha(output/'protocol.json')+'\n');return p


def checked(root,selected=False):
    root=Path(root)
    if sha(root/'protocol.json')!=(root/'protocol.sha256').read_text().strip():raise ValueError('Protocol hash changed')
    p=read_json(root/'protocol.json')
    for field in ('input_hashes','source_hashes'):verify_hashes('/',p[field])
    if p['seeds']!=list(SEEDS) or p['epochs']!=12 or p['thresholds']!=list(THRESHOLDS) or p['distances']!=list(DISTANCES) or p['floors']!=FLOORS or p['continuous_radius_px']!=12.:raise ValueError('Protocol configuration changed')
    if selected:
        lock=read_json(root/'selection-lock.json')
        if lock['protocol_sha256']!=sha(root/'protocol.json') or lock['selection_sha256']!=sha(root/'selection.json'):raise ValueError('Selection hash changed')
        verify_hashes(root,lock['evidence_hashes']);validate_selection(read_json(root/'selection.json'))
    return p


def image_proposals(rgb,detector,a_config):
    found=predict_centers(rgb,detector,LEARNED_CONFIG);heat=found['probability_map'];response=response_map(rgb)
    log,_=select_peaks(response,**LOG_CONFIG);union=merge_proposals(found['points_xy'],log,rgb.shape[:2]);points=union['points_xy'];x,y=points.T
    metadata=np.column_stack([heat[y,x],response[y,x],(union['sources']&1)!=0,(union['sources']&2)!=0]).astype(np.float32)
    a=decode_candidates(*peak_candidates(heat),**a_config)['points_xy']
    return dict(points=points,sources=union['sources'],metadata=metadata,a_points=a)


def make_local_pools(samples,rng):
    if not samples or any(r['split']!='train' for r in samples):raise ValueError('Train-only pools')
    negative=defaultdict(list);positive=defaultdict(dict)
    for i,r in enumerate(samples):
        t=proxy_targets(r['points'],r['gt_points'],r['rgb'].shape[:2]);r['targets']=t
        for j in np.flatnonzero(t['labels']==1):positive[r['case_id']].setdefault((i,int(t['nearest'][j])),[]).append((i,int(j)))
        ids=np.flatnonzero(t['labels']==0)
        if len(ids)>256:ids=np.sort(rng.choice(ids,256,replace=False))
        negative[r['case_id']].extend((i,int(j)) for j in ids)
    return {0:{k:v for k,v in negative.items() if v},1:{k:list(v.values()) for k,v in positive.items() if v}}


def local_draws(pools,count,rng):
    if count<=0 or count%2 or not pools[0] or not pools[1]:raise ValueError('Both labels and even count required')
    draws=[]
    for label in (0,1):
        cases=sorted(pools[label])
        for _ in range(count//2):
            units=pools[label][cases[int(rng.integers(len(cases)))]];unit=units[int(rng.integers(len(units)))]
            item=unit[int(rng.integers(len(unit)))] if label else unit
            draws.append((label,item))
    return [draws[i] for i in rng.permutation(len(draws))]


def batch(samples,pools,count,rng):
    crops,meta,labels,targets=[],[],[],[]
    for label,(i,j) in local_draws(pools,count,rng):
        r=samples[i];crop,target=transform_sample(r['contexts'][j],r['targets']['offsets'][j],int(rng.integers(4)),bool(rng.integers(2)),bool(rng.integers(2)))
        crops.append(crop);meta.append(r['metadata'][j]);labels.append(label);targets.append(target)
    x=torch.from_numpy(np.stack(crops).transpose(0,3,1,2).copy()).float()/255
    factors=torch.from_numpy(rng.uniform(.9,1.1,(count,3,1,1)).astype(np.float32))
    return (x*factors).clamp(0,1),torch.from_numpy(np.stack(meta).astype(np.float32)),torch.tensor(labels,dtype=torch.long),torch.from_numpy(np.stack(targets))


def configuration_trials(samples,epoch):
    if not samples or any(r['split']!='validation' for r in samples):raise ValueError('Validation only')
    trials=[]
    for distance in DISTANCES:
        cached=[retain_candidates(r['corrected_xy'],r['scores'],0,distance) for r in samples]
        for threshold in THRESHOLDS:
            decoded=[{**r,'points':c['points_xy'][c['scores']>=threshold]} for r,c in zip(samples,cached)]
            trials.append(dict(split='validation',epoch=epoch,config=dict(threshold=threshold,min_distance=distance),**summarize_locations(decoded)))
    return trials


def train_seed(samples,seed,root,p):
    rng=np.random.default_rng(seed);torch.manual_seed(seed)
    training=[r for r in samples if r['split']=='train'];validation=[r for r in samples if r['split']=='validation']
    pools=make_local_pools(training,rng)
    if not pools[0] or not pools[1]:raise ValueError('Missing proxy label pool')
    metadata=np.concatenate([r['metadata'] for r in training]).astype(np.float64);mean=metadata.mean(0);scale=metadata.std(0);scale[scale==0]=1
    model=LocalizationGate(mean,scale);optimizer=torch.optim.Adam(model.parameters(),lr=p['learning_rate'])
    baseline=summarize_locations([{**r,'points':r['a_points']} for r in validation]);union=summarize_locations(validation)
    serial=lambda r:{k:(v.tolist() if isinstance(v,np.ndarray) else v) for k,v in r.items() if k!='rgb'}
    write_rows(root/f'validation-{seed}.json.gz',[serial(r) for r in validation])
    fresh_json(root/f'pools-{seed}.json',dict(seed=seed,positive_gt_units_by_case={k:len(v) for k,v in pools[1].items()},positive_candidate_counts_by_case={k:sum(len(u) for u in v) for k,v in pools[1].items()},negative_proxy_by_case={k:len(v) for k,v in pools[0].items()},metadata_mean=mean.tolist(),metadata_scale=scale.tolist(),normalization_split='train'))
    for r in training:r['contexts']=reflected_context(r['rgb'],r['points'])
    best,diagnostic,history=None,None,[];started=time.perf_counter();saved={};epoch_count=2*sum(len(r['gt_points']) for r in training)
    for epoch in range(1,13):
        model.train();loss_sum=0.
        for start in range(0,epoch_count,p['batch_size']):
            count=min(p['batch_size'],epoch_count-start);x,meta,y,targets=batch(training,pools,count,rng)
            optimizer.zero_grad(set_to_none=True);logits,delta=model(x,meta);loss=localization_loss(logits,delta,y,targets)
            if not torch.isfinite(loss):raise ValueError('Nonfinite training loss')
            loss.backward();optimizer.step();loss_sum+=float(loss.detach())*count
        for r in validation:r.update(predict_localized(r['rgb'],r['points'],r['metadata'],model))
        saved[f'scores_{epoch}']=np.concatenate([r['scores'] for r in validation]).astype(np.float32)
        saved[f'xy_{epoch}']=np.concatenate([r['corrected_xy'] for r in validation]).astype(np.uint16)
        trials=configuration_trials(validation,epoch);outcome=choose_trial(trials,baseline,p['floors']);candidate=outcome['selected'];d=max(trials,key=trial_key)
        if diagnostic is None or trial_key(d)>trial_key(diagnostic):diagnostic=d;torch.save(model.state_dict(),root/f'diagnostic-{seed}.pt')
        if candidate is not None and (best is None or trial_key(candidate)>trial_key(best)):best=candidate;torch.save(model.state_dict(),root/f'gate-{seed}.pt')
        history.append(dict(epoch=epoch,train_loss=loss_sum/epoch_count,feasible_trials=outcome['feasible_trials'],trials=trials))
        print(json.dumps(dict(seed=seed,epoch=epoch,loss=loss_sum/epoch_count,feasible=outcome['feasible_trials'],best_f1=d['case_macro_f1'],best_recall=d['case_macro_recall'],seconds=time.perf_counter()-started)),flush=True)
    np.savez_compressed(root/f'validation-output-{seed}.npz',**saved);write_rows(root/f'trials-{seed}.json.gz',history)
    selected=best or diagnostic;offset=0;scorer_rows=[]
    values=saved[f"scores_{selected['epoch']}"].astype(np.float64)
    for r in validation:
        scores=values[offset:offset+len(r['points'])];offset+=len(r['points'])
        scorer_rows.append({**r,'points':retain_candidates(r['points'],scores,**selected['config'])['points_xy']})
    return dict(seed=seed,selected=best,diagnostic=diagnostic,baseline=baseline,union=union,scorer_without_offsets=summarize_locations(scorer_rows),feasible_trials=sum(h['feasible_trials'] for h in history),training_selection_seconds=time.perf_counter()-started,parameter_count=sum(t.numel() for t in model.parameters()),checkpoint=f'gate-{seed}.pt' if best else None,diagnostic_checkpoint=f'diagnostic-{seed}.pt',epochs=12)


def fit(root):
    root=Path(root);p=checked(root);fresh_json(root/'fit-started.json',dict(created_utc=utc()))
    torch.set_num_threads(p['torch_threads']);torch.use_deterministic_algorithms(True)
    rows=[r for r in read_json(Path(p['parent'])/'source-manifest.json') if r['split'] in ('train','validation')];verify_data(p['data_dir'],rows)
    base=[]
    for r in rows:
        rgb,gt,gc=load_sample(p['data_dir'],r)
        if rgb.shape!=(224,224,3):raise ValueError('Expected native224RGB')
        base.append(dict(image=r['image'],split=r['split'],case_id=r['case_id'],rgb=rgb,gt_points=gt,gt_classes=gc))
    models=[]
    for seed,(detector,config) in loaded_detectors(p['prior']).items():
        samples=[{**r,**image_proposals(r['rgb'],detector,config)} for r in base]
        models.append(train_seed(samples,seed,root,p))
    fresh_json(root/'selection.json',dict(models=models,test_used_for_selection=False,external_used_for_selection=False))
    evidence={f.name:sha(f) for f in root.iterdir() if f.suffix in ('.gz','.npz','.pt') or f.name.startswith('pools-')}
    fresh_json(root/'selection-lock.json',dict(created_utc=utc(),protocol_sha256=sha(root/'protocol.json'),selection_sha256=sha(root/'selection.json'),evidence_hashes=evidence))
    checked(root,selected=True);return models


def stability_summary(rows):
    if [r['seed'] for r in rows]!=list(SEEDS):raise ValueError('All three seed outcomes required')
    count=sum(bool(r['eligible'] and r['test_passed']) for r in rows)
    return dict(denominator=3,test_passes=count,all_three_test_passed=count==3,seeds=rows,scope='Reused test, not unseen/clinical/whole-WSI proof')


def test_criteria(a,r):
    ac,rc=a['localization'],r['localization']
    return dict(joint_fp_fn=rc['fp']<=ac['fp'] and rc['fn']<=ac['fn'] and (rc['fp']<ac['fp'] or rc['fn']<ac['fn']),
        every_case_recall=all(r['cases'][k]['recall']>=.9*v['recall'] for k,v in a['cases'].items()),
        tumor_class_recalls=all(x>=y for x,y in zip(r['tumor_recalls'],a['tumor_recalls'])))


def evaluate(root,external=False):
    root=Path(root);p=checked(root,selected=True);tag='external' if external else 'internal';models=read_json(root/'selection.json')['models'];eligible=validate_selection({'models':models})
    if not eligible:
        fresh_json(root/(tag+'-not-run.json'),dict(reason='No eligible seed; do not evaluate holdout',new_inference_images=0))
        if not external:fresh_json(root/'stability.json',stability_summary([dict(seed=m['seed'],eligible=False,test_passed=False) for m in models]))
        return
    fresh_json(root/(tag+'-started.json'),dict(created_utc=utc(),selection_lock_sha256=sha(root/'selection-lock.json')))
    torch.set_num_threads(p['torch_threads']);detectors=loaded_detectors(p['prior']);classifiers=load_models(p['parent'],read_json(Path(p['parent'])/'selection-lock.json'));gates={}
    for m in eligible:
        gate=LocalizationGate();gate.load_state_dict(torch.load(root/m['checkpoint'],weights_only=True,map_location='cpu'));gates[m['seed']]=gate.eval()
    if external:
        previous=Path(p['external']);refs=read_json(previous/'private-predictions.json');entries={r['name']:r for r in read_json(previous/'entries.json')};inputs={r['name']:r for r in read_json(previous/'input-manifest.json')}
        names=validate_external_entries(list(entries.values()));refmap={r['image']:r for r in refs}
        if len(refs)!=133 or set(refmap)!=set(names):raise ValueError('External image set changed')
        url=download_url();rows=[refmap[n] for n in names]
    else:
        rows=[r for r in read_json(Path(p['parent'])/'source-manifest.json') if r['split']=='test'];verify_data(p['data_dir'],rows)
    outputs={m['seed']:{arm:[] for arm in ('A','U','S','R')} for m in eligible};proposals={m['seed']:[] for m in eligible}
    for index,r in enumerate(rows):
        if external:
            raw,meta=fetch_entry(url,entries[r['image']])
            if meta['sha256']!=inputs[r['image']]['sha256']:raise ValueError('External raw image hash changed')
            im=Image.open(io.BytesIO(raw))
            if im.mode!='RGB' or im.size!=(640,640):raise ValueError('Expected native640RGB')
            rgb=np.asarray(im);gt=np.asarray(r['gt_points']).reshape(-1,2);gc=np.asarray(r['gt_classes'])
        else:rgb,gt,gc=load_sample(p['data_dir'],r)
        for m in eligible:
            seed=m['seed'];found=image_proposals(rgb,*detectors[seed]);pred=predict_localized(rgb,found['points'],found['metadata'],gates[seed]);config=m['selected']['config']
            arms=dict(A=found['a_points'],U=found['points'],S=retain_candidates(found['points'],pred['scores'],**config)['points_xy'],R=retain_candidates(pred['corrected_xy'],pred['scores'],**config)['points_xy'])
            proposals[seed].append(dict(image=r['image'],points=found['points'].tolist(),scores=pred['scores'].tolist(),corrected_xy=pred['corrected_xy'].tolist(),sources=found['sources'].tolist()))
            for arm,xy in arms.items():
                row=dict(image=r['image'],points=xy.tolist(),gt_points=gt.tolist(),gt_classes=gc.tolist(),classes={})
                if not external:row['case_id']=r['case_id']
                for name,classifier in classifiers.items():row['classes'][name]=classify_centers(rgb,xy,classifier).argmax(1).tolist()
                outputs[seed][arm].append(row)
        if (index+1)%25==0:print(tag,index+1,flush=True)
    decisions={}
    for seed,arms in outputs.items():
        folder=root/f'seed-{seed}'/tag;folder.mkdir(parents=True,exist_ok=False);write_rows(folder/'proposals.json.gz',proposals[seed])
        for arm,rs in arms.items():
            dest=folder/arm;dest.mkdir();write_rows(dest/'predictions.json.gz',rs)
            scores={name:(score_external(rs,name) if external else summarize(rs,name)) for name in classifiers}
            fresh_json(dest/'results.json',dict(seed=seed,arm=arm,image_count=len(rs),classifiers=scores,predictions_sha256=sha(dest/'predictions.json.gz'),selection_lock_sha256=sha(root/'selection-lock.json'),scope=p['scope']))
        if not external:
            a=summarize_locations(arms['A']);r=summarize_locations(arms['R']);criteria=test_criteria(a,r);decisions[seed]=dict(seed=seed,eligible=True,test_passed=all(criteria.values()),criteria=criteria,A=a,R=r)
    if not external:fresh_json(root/'stability.json',stability_summary([decisions.get(m['seed'],dict(seed=m['seed'],eligible=False,test_passed=False)) for m in models]))
    checked(root,selected=True)
