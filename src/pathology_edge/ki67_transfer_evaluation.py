"""Fixed classifiers at actual centers; diagnostic evaluation is not adoption."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import hashlib
import io
import json
import time
import urllib.error
import numpy as np
from PIL import Image
import torch
from .ki67_transfer import TransferCenterDetector
from .ki67_transfer_experiment import checked,primary_models,job_name,infer_peaks,ROOT
from .ki67_centers import predict_centers
from .ki67_center_experiment import loaded_detectors,score_external
from .ki67_union import retain_candidates,summarize_locations
from .ki67_union_experiment import SEEDS,utc,write_rows,read_rows
from .ki67_localization_experiment import test_criteria
from .ki67_normalized_pipeline import classified_row,pipeline_criteria,reference_classifier
from .ki67_experiment import read_json,fresh_json,sha,verify_hashes,verify_data,load_sample,load_models,summarize
from .ki67_external import fetch_entry,download_url,validate_external_entries
from .ki67_deepliif import decode_paired_png,validate_membership,score_rows,paired_fraction
from .ki67_transfer_download import download


def classifier_for_seed(seed):return reference_classifier(seed)


def stability(rows):
    if len(rows)!=3 or {r.get('seed') for r in rows}!=set(SEEDS):raise ValueError('All three unique seeds required')
    return dict(seeds=rows,denominator=3,passes=sum(bool(r['passed']) for r in rows),all_three_passed=all(r['passed'] for r in rows),adopted_seeds=sum(bool(r['eligible']) for r in rows))


def external_comparison(a,b):
    fractions=paired_fraction(a['per_image'],b['per_image'])
    criteria=dict(detection_f1_increase=b['localization']['f1']>a['localization']['f1'],two_class_f1_increase=b['two_class_macro_f1']>a['two_class_macro_f1'],same_population_fraction_mae_nonincrease=fractions['passed'])
    return dict(A={k:v for k,v in a.items() if k!='per_image'},B={k:v for k,v in b.items() if k!='per_image'},fractions=fractions,criteria=criteria,passed=all(criteria.values()))


def evaluation_lock(root):
    root=Path(root);p=checked(root,selected=True)
    target=root/'evaluation-lock.json'
    source=[Path(__file__),ROOT/'src/pathology_edge/ki67_transfer_download.py',ROOT/'scripts/run_ki67_transfer_evaluation.py',ROOT/'scripts/audit_ki67_deepliif.py']
    selection=read_json(Path(p['parent'])/'selection-lock.json')
    classifiers={str(Path(p['parent'])/n):h for n,h in selection['model_hashes'].items()}
    external=Path(p['external']);inputs={str(external/n):sha(external/n) for n in ('private-predictions.json','entries.json','input-manifest.json','input-audit.json','prior-test-pixel-hashes.json')}
    lock=dict(detector_lock_sha256=sha(root/'selection-lock.json'),source_hashes={str(f.resolve()):sha(f) for f in source},classifier_hashes=classifiers,external_hashes=inputs,
              paired_classifiers={str(s):classifier_for_seed(s) for s in SEEDS},diagnostics_included=True)
    if target.exists():
        if read_json(target)!=lock:raise ValueError('Evaluation inputs or source changed')
    else:fresh_json(target,lock)
    verify_hashes('/',classifiers);verify_hashes('/',inputs)
    return p


def networks(root):
    root=Path(root);p=evaluation_lock(root);models=primary_models(read_json(root/'selection.json'));nets={}
    for m in models:
        dest=root/job_name(m['arm'],m['seed']);state=torch.load(dest/'features.pt',map_location='cpu',weights_only=True)
        net=TransferCenterDetector(state);net.decoder.load_state_dict(torch.load(dest/m['evaluation_checkpoint'],map_location='cpu',weights_only=True),strict=True)
        if not all(torch.isfinite(v).all() for v in net.state_dict().values()):raise ValueError('Nonfinite evaluation model')
        nets[m['seed']]=net.eval()
    original=loaded_detectors(p['prior']);classifiers=load_models(p['parent'],read_json(Path(p['parent'])/'selection-lock.json'))
    return p,models,nets,original,classifiers


def predict_pair(rgb,m,nets,original):
    seed=m['seed'];a,config=original[seed]
    torch.set_num_threads(2);aa=predict_centers(rgb,a,config)['points_xy'];torch.set_num_threads(1)
    found=infer_peaks(rgb,nets[seed]);bb=retain_candidates(found['points'],found['scores'],**m['evaluation_trial']['config'])['points_xy']
    return dict(A=aa,B=bb)


def evaluate_existing(root,split):
    if split not in ('validation','test','bcdata'):raise ValueError('Unknown existing set')
    root=Path(root);p,models,nets,original,classifiers=networks(root);out=root/'evaluation'/split;out.mkdir(parents=True,exist_ok=False)
    fresh_json(out/'started.json',dict(created_utc=utc(),evaluation_lock_sha256=sha(root/'evaluation-lock.json'),scope='Reused data; no independent new validation claim'))
    if split=='bcdata':
        external=Path(p['external']);refs=read_json(external/'private-predictions.json');entries={r['name']:r for r in read_json(external/'entries.json')};inputs={r['name']:r for r in read_json(external/'input-manifest.json')}
        names=validate_external_entries(list(entries.values()));refmap={r['image']:r for r in refs}
        if len(refs)!=133 or set(refmap)!=set(names):raise ValueError('External correspondence changed')
        rows=[refmap[n] for n in names];url=download_url()
    else:
        rows=[r for r in read_json(Path(p['parent'])/'source-manifest.json') if r['split']==split];verify_data(p['data_dir'],rows)
        if len(rows)!={'validation':227,'test':407}[split]:raise ValueError('Unexpected image count')
    outputs={m['seed']:{a:[] for a in ('A','B')} for m in models}
    for i,r in enumerate(rows):
        if split=='bcdata':
            raw,meta=fetch_entry(url,entries[r['image']])
            if meta['sha256']!=inputs[r['image']]['sha256']:raise ValueError('BCData RGB hash changed')
            im=Image.open(io.BytesIO(raw))
            if im.mode!='RGB' or im.size!=(640,640):raise ValueError('Expected native640RGB')
            rgb=np.asarray(im);gt=np.asarray(r['gt_points']).reshape(-1,2);gc=np.asarray(r['gt_classes'])
        else:rgb,gt,gc=load_sample(p['data_dir'],r)
        for m in models:
            name=classifier_for_seed(m['seed']);classifier={name:classifiers[name]}
            for arm,xy in predict_pair(rgb,m,nets,original).items():
                outputs[m['seed']][arm].append(classified_row(rgb,xy,gt,gc,classifier,r['image'],None if split=='bcdata' else r['case_id']))
        if (i+1)%25==0:print(split,i+1,'/',len(rows),flush=True)
    decisions=[]
    for m in models:
        seed=m['seed'];name=classifier_for_seed(seed);folder=out/str(seed);folder.mkdir();scores={};locations={}
        for arm,rs in outputs[seed].items():
            write_rows(folder/(arm+'.json.gz'),rs);scores[arm]=score_external(rs,name) if split=='bcdata' else summarize(rs,name)
            if split!='bcdata':locations[arm]=summarize_locations([{**r,'points':np.asarray(r['points']).reshape(-1,2),'gt_points':np.asarray(r['gt_points']).reshape(-1,2)} for r in rs])
        if split=='bcdata':
            converted={a:{**v,'per_image':[dict(image=r['image'],gt_fraction=r['target_fraction']['fraction'],pred_fraction=r['predicted_fraction']['fraction']) for r in v['per_image']]} for a,v in scores.items()}
            comparison=external_comparison(converted['A'],converted['B']);comparison['scope']='Reused BCData133 tumor-only labels; non-tumor sensitivity unmeasured'
        else:
            pc=pipeline_criteria(scores['A'],scores['B'],sorted({r['case_id'] for r in rows}));dc=test_criteria(locations['A'],locations['B'])
            comparison=dict(A=locations['A'],B=locations['B'],pipeline_criteria=pc,detection_criteria=dc,passed=all(pc.values()) and all(dc.values()))
        comparison.update(seed=seed,classifier=name,eligible=m['selected'] is not None,evaluation_mode='eligible' if m['selected'] is not None else 'unadopted diagnostic')
        write_rows(folder/'scores.json.gz',[scores]);fresh_json(folder/'comparison.json',comparison)
        decisions.append(dict(seed=seed,eligible=m['selected'] is not None,passed=comparison['passed']))
    evaluation_lock(root)
    fresh_json(out/'summary.json',dict(**stability(decisions),new_inference_images=len(rows),model_image_predictions=len(rows)*6,scope='Reused '+split,all_checks_passed=True,evidence_hashes={str(f.relative_to(out)):sha(f) for f in out.rglob('*') if f.is_file()}))


def external_source(root):
    p=checked(root);base=ROOT/'work/ki67-capacity-20261114';protocol=base/'prospective-external-protocol.json';index_path=base/'deepliif-test-index.json';ep=read_json(protocol);index=read_json(index_path)
    if sha(protocol)!=protocol.with_suffix('.sha256').read_text().strip() or sha(index_path)!=ep['index_sha256']:raise ValueError('External protocol/index changed')
    names=validate_membership(ep,index)
    if ep['radii_native_px']!=[6,12] or ep['primary_radius']!=6 or ep['source_url']!=index['url'] or ep['archive_bytes']!=index['bytes']:raise ValueError('External scoring/source changed')
    ext=Path(p['external'])
    forbidden={r['pixel_sha256'] for r in read_json(Path(p['parent'])/'source-manifest.json')}|set(read_json(ext/'prior-test-pixel-hashes.json'))|{r['pixel_sha256'] for r in read_json(ext/'input-audit.json')['images']}
    return ep,index,names,forbidden


def external_stream(ep,index,names,forbidden):
    import sys
    if str(ROOT/'scripts') not in sys.path:sys.path.insert(0,str(ROOT/'scripts'))
    from audit_ki67_deepliif import verify_reference_mask
    entries={r['name']:r for r in index['entries']};seen=set();last=-float('inf')
    for i,name in enumerate(names):
        # <=30 requests/minute, no parallel bursts. Retry-After handled globally
        # because only this sequential stream calls the public server.
        time.sleep(max(0,2-(time.monotonic()-last)));last=time.monotonic()
        raw,meta=download(ep['source_url'],entries[name],ep['archive_bytes'])
        rgb,gt,gc,reference=decode_paired_png(raw);pixel=hashlib.sha256(rgb.tobytes()).hexdigest()
        verify_reference_mask(np.asarray(Image.open(io.BytesIO(raw)))[:,2560:3072],gt,gc)
        if pixel in forbidden or pixel in seen:raise ValueError('Exact image overlap; no outcome-based exclusions allowed')
        seen.add(pixel)
        yield i,rgb,gt,gc,dict(image=name,pixel_sha256=pixel,gt_points=gt.tolist(),gt_classes=gc.tolist(),reference=reference,source=meta,independent_reference_checked=True)


def audit_external_inputs(root):
    root=Path(root);ep,index,names,forbidden=external_source(root);dest=root/'external-input-review';dest.mkdir(exist_ok=False);rows=[]
    fresh_json(dest/'started.json',dict(created_utc=utc(),training_protocol_sha256=sha(root/'protocol.json'),new_model_inference_images=0))
    for i,rgb,gt,gc,audit in external_stream(ep,index,names,forbidden):
        rows.append(audit)
        with (dest/'verified-prefix.jsonl').open('a') as f:f.write(json.dumps(audit,separators=(',',':'))+'\n')
        if i in (0,100,200,300,400,596):Image.fromarray(rgb).save(dest/f'{i:03d}.png')
        if (i+1)%25==0:print('REFERENCE',i+1,'/',len(names),flush=True)
    write_rows(dest/'input-audit.json.gz',rows)
    fresh_json(dest/'summary.json',dict(images=len(rows),reference_cells=sum(len(r['gt_points']) for r in rows),all_checks_passed=True,new_model_inference_images=0,exact_image_overlap_count=0,full_archive_checksum_verified=False,source=ep['source_url'],scope=ep['scope'],evidence_hashes={f.name:sha(f) for f in dest.iterdir() if f.is_file()}))


def evaluate_deepliif(root):
    root=Path(root);p,models,nets,original,classifiers=networks(root);ep,index,names,forbidden=external_source(root)
    out=root/'evaluation/deepliif';out.mkdir(parents=True,exist_ok=False)
    fresh_json(out/'started.json',dict(created_utc=utc(),evaluation_lock_sha256=sha(root/'evaluation-lock.json'),before_inference=True,full_archive_checksum_verified=False))
    previous=read_rows(root/'external-input-review/input-audit.json.gz');previous={r['image']:r for r in previous}
    outputs={m['seed']:{a:[] for a in ('A','B')} for m in models};audits=[]
    for i,rgb,gt,gc,audit in external_stream(ep,index,names,forbidden):
        if audit!=previous.get(audit['image']):raise ValueError('External pixels/reference/source differ from prior audit')
        audits.append(audit)
        for m in models:
            name=classifier_for_seed(m['seed']);classifier={name:classifiers[name]}
            for arm,xy in predict_pair(rgb,m,nets,original).items():
                outputs[m['seed']][arm].append(classified_row(rgb,xy,gt,gc,classifier,audit['image']))
        if (i+1)%25==0:print('DEEPLIIF',i+1,'/',len(names),flush=True)
    write_rows(out/'input-audit.json.gz',audits);decisions=[]
    for m in models:
        seed=m['seed'];name=classifier_for_seed(seed);folder=out/str(seed);folder.mkdir();scores={};comparisons={}
        for arm,rs in outputs[seed].items():
            write_rows(folder/(arm+'.json.gz'),rs);scores[arm]={str(radius):score_rows(rs,name,radius) for radius in (6,12)}
        for radius in ('6','12'):comparisons[radius]=external_comparison(scores['A'][radius],scores['B'][radius])
        write_rows(folder/'scores.json.gz',[scores]);fresh_json(folder/'comparison.json',comparisons)
        decisions.append(dict(seed=seed,eligible=m['selected'] is not None,passed=comparisons['6']['passed']))
    evaluation_lock(root)
    fresh_json(out/'summary.json',dict(**stability(decisions),new_inference_images=len(names),model_image_predictions=len(names)*6,all_checks_passed=True,
        primary_radius=6,secondary_radius=12,scope=ep['scope'],clinical_validation=False,whole_wsi_validation=False,
        limitation='Segmentation-derived centroids, native pixels; patient/slide independence and MPP unverified; all-cell staining, not tumor Ki67',
        evidence_hashes={str(f.relative_to(out)):sha(f) for f in out.rglob('*') if f.is_file()}))
