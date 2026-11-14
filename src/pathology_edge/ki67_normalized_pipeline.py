"""Actual-center classifier selection and reused held-out pipeline evaluation."""
import io
import math
from pathlib import Path
import numpy as np
from PIL import Image
import torch
from .ki67_normalized_experiment import checked,primary_models,job_name,infer_peaks,ROOT
from .ki67_normalized_centers import NormalizedCenterDetector
from .ki67_centers import predict_centers
from .ki67_center_experiment import loaded_detectors,score_external
from .ki67_union import retain_candidates,summarize_locations
from .ki67_union_experiment import SEEDS,utc,write_rows,read_rows
from .ki67_localization_experiment import stability_summary,test_criteria
from .ki67_experiment import read_json,fresh_json,sha,verify_hashes,verify_data,load_sample,load_models,summarize
from .ki67_cnn import classify_centers
from .ki67_external import fetch_entry,download_url,validate_external_entries

ARMS=('lr','cnn-20261113','cnn-20261114','cnn-20261115')


def reference_classifier(seed):
    if type(seed) is not int or seed not in SEEDS:raise ValueError('Unknown detector seed')
    return ARMS[1+SEEDS.index(seed)]


def valid_summary(score,case_ids):
    try:
        cases=score['per_case'];ids=[r['case_id'] for r in cases]
        return (len(ids)==len(set(ids)) and set(ids)==set(case_ids) and score['case_ratio_valid']==len(case_ids)
                and all(r['ratio_error_pp'] is not None and math.isfinite(r['ratio_error_pp']) and 0<=r['ratio_error_pp']<=100 for r in cases)
                and math.isfinite(score['macro_f1']) and 0<=score['macro_f1']<=1
                and score['case_ratio_mae_pp'] is not None and math.isfinite(score['case_ratio_mae_pp']) and 0<=score['case_ratio_mae_pp']<=100)
    except (KeyError,TypeError):return False


def pipeline_criteria(a,b,case_ids):
    valid=bool(case_ids) and valid_summary(a,case_ids) and valid_summary(b,case_ids)
    return dict(same_full_case_coverage=valid,
                end_to_end_f1_increase=valid and b['macro_f1']>a['macro_f1'],
                case_fraction_mae_nonincrease=valid and b['case_ratio_mae_pp']<=a['case_ratio_mae_pp'])


def choose_classifier(baseline,scores,reference,case_ids):
    if set(scores)!=set(ARMS) or reference not in ARMS:raise ValueError('Four frozen classifiers required')
    criteria={name:pipeline_criteria(baseline,scores[name],case_ids) for name in ARMS}
    feasible=[name for name in ARMS if all(criteria[name].values())]
    selected=max(feasible,key=lambda n:(scores[n]['macro_f1'],-scores[n]['case_ratio_mae_pp'],-ARMS.index(n))) if feasible else reference
    return dict(selected_classifier=selected,reference_classifier=reference,validation_pipeline_passed=bool(feasible),criteria=criteria)


def classified_row(rgb,xy,gt,gc,classifiers,image,case_id=None):
    row=dict(image=image,points=np.asarray(xy).reshape(-1,2).tolist(),gt_points=np.asarray(gt).reshape(-1,2).tolist(),gt_classes=np.asarray(gc).tolist(),classes={})
    if case_id is not None:row['case_id']=case_id
    for name,model in classifiers.items():row['classes'][name]=classify_centers(rgb,xy,model).argmax(1).tolist()
    return row


def selected_networks(root,models):
    networks={}
    for m in models:
        if m['selected'] is None:continue
        network=NormalizedCenterDetector(16);network.load_state_dict(torch.load(Path(root)/job_name(16,m['seed'])/m['checkpoint'],map_location='cpu',weights_only=True),strict=True)
        if not all(torch.isfinite(v).all() for v in network.state_dict().values()):raise ValueError('Nonfinite selected model')
        networks[m['seed']]=network.eval()
    return networks


def predict_pair(rgb,seed,selected,original,networks):
    a,config=original[seed];torch.set_num_threads(2);xy_a=predict_centers(rgb,a,config)['points_xy'];torch.set_num_threads(1)
    found=infer_peaks(rgb,networks[seed]);xy_b=retain_candidates(found['points'],found['scores'],**selected['config'])['points_xy']
    return {'A':xy_a,'B':xy_b}


def select_classifiers(root):
    root=Path(root);p=checked(root,selected=True);models=primary_models(read_json(root/'selection.json'));eligible=[m for m in models if m['selected'] is not None]
    fresh_json(root/'classifier-selection-started.json',dict(created_utc=utc(),selection_lock_sha256=sha(root/'selection-lock.json')))
    results=[];evidence={}
    if eligible:
        torch.set_num_threads(1);classifiers=load_models(p['parent'],read_json(Path(p['parent'])/'selection-lock.json'))
        if tuple(classifiers)!=ARMS:raise ValueError('Classifier set/order changed')
        manifest={r['image']:r for r in read_json(Path(p['parent'])/'source-manifest.json') if r['split']=='validation'}
        case_ids=sorted({r['case_id'] for r in manifest.values()});verify_data(p['data_dir'],list(manifest.values()))
        for m in eligible:
            dest=root/job_name(16,m['seed']);refs=read_rows(dest/'validation.json.gz');saved=np.load(dest/'validation-peaks.npz',allow_pickle=False);epoch=m['selected']['epoch'];offsets=saved[f'offsets_{epoch}'];outputs={k:[] for k in ('A','B')}
            if len(refs)!=227 or {r['image'] for r in refs}!=set(manifest):raise ValueError('Validation membership changed')
            for i,r in enumerate(refs):
                rgb,gt,gc=load_sample(p['data_dir'],manifest[r['image']]);lo,hi=offsets[i:i+2]
                xy=retain_candidates(saved[f'points_{epoch}'][lo:hi],saved[f'scores_{epoch}'][lo:hi].astype(np.float64),**m['selected']['config'])['points_xy']
                for arm,pts in (('A',np.asarray(r['a_points']).reshape(-1,2)),('B',xy)):
                    outputs[arm].append(classified_row(rgb,pts,gt,gc,classifiers,r['image'],r['case_id']))
            summaries={arm:{name:summarize(rows,name) for name in ARMS} for arm,rows in outputs.items()}
            reference=reference_classifier(m['seed']);choice=choose_classifier(summaries['A'][reference],summaries['B'],reference,case_ids)
            folder=root/'pipeline-validation'/str(m['seed']);folder.mkdir(parents=True,exist_ok=False)
            for arm,rows in outputs.items():write_rows(folder/(arm+'.json.gz'),rows)
            fresh_json(folder/'scores.json',summaries)
            evidence.update({str(f.relative_to(root)):sha(f) for f in folder.iterdir() if f.is_file()})
            results.append(dict(seed=m['seed'],detector_eligible=True,**choice))
            print('CLASSIFIER SELECTED',m['seed'],choice['selected_classifier'],choice['validation_pipeline_passed'],flush=True)
    found={r['seed']:r for r in results}
    results=[found.get(m['seed'],dict(seed=m['seed'],detector_eligible=False,reference_classifier=reference_classifier(m['seed']),selected_classifier=None,validation_pipeline_passed=False)) for m in models]
    fresh_json(root/'classifier-selection.json',dict(models=results,selection_data='validation227/4cases',classifiers_refit=False,test_used_for_selection=False,external_used_for_selection=False))
    source=[Path(__file__).resolve(),ROOT/'scripts/run_ki67_normalized_pipeline.py']
    fresh_json(root/'classifier-lock.json',dict(created_utc=utc(),detector_lock_sha256=sha(root/'selection-lock.json'),classifier_selection_sha256=sha(root/'classifier-selection.json'),evidence_hashes=evidence,source_hashes={str(f):sha(f) for f in source}))
    checked_pipeline(root);return results


def checked_pipeline(root):
    root=Path(root);p=checked(root,selected=True);lock=read_json(root/'classifier-lock.json')
    if lock['detector_lock_sha256']!=sha(root/'selection-lock.json') or lock['classifier_selection_sha256']!=sha(root/'classifier-selection.json'):raise ValueError('Classifier selection lock changed')
    verify_hashes(root,lock['evidence_hashes']);verify_hashes('/',lock['source_hashes'])
    models=primary_models(read_json(root/'selection.json'));choices=read_json(root/'classifier-selection.json')['models']
    if [r['seed'] for r in choices]!=list(SEEDS):raise ValueError('All three classifier decisions required')
    for m,c in zip(models,choices):
        if c['reference_classifier']!=reference_classifier(m['seed']) or c['detector_eligible']!=(m['selected'] is not None):raise ValueError('Classifier/detector identity mismatch')
        if c['detector_eligible'] and c['selected_classifier'] not in ARMS:raise ValueError('Unknown classifier choice')
        if not c['detector_eligible'] and c['selected_classifier'] is not None:raise ValueError('Ineligible model has classifier')
    return p,models,{c['seed']:c for c in choices}


def evaluate(root,external=False):
    root=Path(root);p,models,choices=checked_pipeline(root)
    eligible=[m for m in models if m['selected'] is not None];tag='external' if external else 'internal'
    if not eligible:
        fresh_json(root/(tag+'-not-run.json'),dict(reason='No eligible primary seed; no holdout inference',new_inference_images=0))
        if not external:
            result=stability_summary([dict(seed=m['seed'],eligible=False,test_passed=False,pipeline_passed=False) for m in models])
            result.update(pipeline_passes=0,all_three_pipeline_passed=False);fresh_json(root/'stability.json',result)
        return
    fresh_json(root/(tag+'-started.json'),dict(created_utc=utc(),classifier_lock_sha256=sha(root/'classifier-lock.json')))
    networks=selected_networks(root,models);original=loaded_detectors(p['prior'])
    classifiers=load_models(p['parent'],read_json(Path(p['parent'])/'selection-lock.json'))
    if tuple(classifiers)!=ARMS:raise ValueError('Classifier set changed')
    if external:
        previous=Path(p['external']);refs=read_json(previous/'private-predictions.json');entries={r['name']:r for r in read_json(previous/'entries.json')};inputs={r['name']:r for r in read_json(previous/'input-manifest.json')}
        names=validate_external_entries(list(entries.values()));refmap={r['image']:r for r in refs}
        if len(refs)!=133 or set(refmap)!=set(names):raise ValueError('External correspondence changed')
        url=download_url();rows=[refmap[n] for n in names]
    else:
        rows=[r for r in read_json(Path(p['parent'])/'source-manifest.json') if r['split']=='test'];verify_data(p['data_dir'],rows)
        if len(rows)!=407 or len({r['case_id'] for r in rows})!=10:raise ValueError('Expected fixed test407/10cases')
    outputs={m['seed']:{arm:[] for arm in ('A','B')} for m in eligible}
    for i,r in enumerate(rows):
        if external:
            raw,meta=fetch_entry(url,entries[r['image']])
            if meta['sha256']!=inputs[r['image']]['sha256']:raise ValueError('External RGB hash changed')
            image=Image.open(io.BytesIO(raw))
            if image.mode!='RGB' or image.size!=(640,640):raise ValueError('Expected native640RGB')
            rgb=np.asarray(image);gt=np.asarray(r['gt_points']).reshape(-1,2);gc=np.asarray(r['gt_classes'])
        else:rgb,gt,gc=load_sample(p['data_dir'],r)
        for m in eligible:
            for arm,xy in predict_pair(rgb,m['seed'],m['selected'],original,networks).items():
                outputs[m['seed']][arm].append(classified_row(rgb,xy,gt,gc,classifiers,r['image'],None if external else r['case_id']))
        if (i+1)%25==0:print(tag,i+1,flush=True)
    decisions={}
    for seed,arms in outputs.items():
        folder=root/'pipeline-heldout'/str(seed)/tag;folder.mkdir(parents=True,exist_ok=False);scores={}
        for arm,rs in arms.items():
            write_rows(folder/(arm+'.json.gz'),rs)
            scores[arm]={name:(score_external(rs,name) if external else summarize(rs,name)) for name in ARMS}
        fresh_json(folder/'scores.json',scores)
        c=choices[seed];a=scores['A'][c['reference_classifier']];b=scores['B'][c['selected_classifier']]
        if external:
            comparison=dict(seed=seed,A_classifier=c['reference_classifier'],B_classifier=c['selected_classifier'],A=a,B=b,scope='Reused BCData133; no independent new external claim')
        else:
            normalized=lambda rs:[{**r,'points':np.asarray(r['points']).reshape(-1,2),'gt_points':np.asarray(r['gt_points']).reshape(-1,2)} for r in rs]
            la=summarize_locations(normalized(arms['A']));lb=summarize_locations(normalized(arms['B']));criteria=test_criteria(la,lb)
            pc=pipeline_criteria(a,b,sorted({r['case_id'] for r in rows}))
            comparison=dict(seed=seed,eligible=True,test_passed=all(criteria.values()),criteria=criteria,A=la,B=lb,
                pipeline_passed=all(pc.values()),pipeline_criteria=pc,A_classifier=c['reference_classifier'],B_classifier=c['selected_classifier'],A_pipeline=a,B_pipeline=b)
            decisions[seed]=comparison
        fresh_json(folder/'comparison.json',comparison)
    if not external:
        outcome=stability_summary([decisions.get(m['seed'],dict(seed=m['seed'],eligible=False,test_passed=False,pipeline_passed=False)) for m in models])
        count=sum(r['pipeline_passed'] for r in outcome['seeds']);outcome.update(pipeline_passes=count,all_three_pipeline_passed=count==3)
        fresh_json(root/'stability.json',outcome)
    checked_pipeline(root)
    fresh_json(root/(tag+'-complete.json'),dict(new_inference_images=len(rows),seed_count=len(eligible),all_checks_passed=True,classifier_lock_sha256=sha(root/'classifier-lock.json'),
        evidence_hashes={str(f.relative_to(root)):sha(f) for m in eligible for f in (root/'pipeline-heldout'/str(m['seed'])/tag).iterdir()}))
