#!/usr/bin/env python3
"""Evaluate frozen models on directly read originals and their paired annotation RGB."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np
from PIL import Image

from pathology_edge.panoptils import contour_agreement_region, score_roi


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False))


def read(path):
    return json.loads(Path(path).read_text())


def masks(root, item):
    with (root/'ALL_FOV_LOCATIONS.csv').open() as stream:
        matches=[r for r in csv.DictReader(stream) if r['roiname']==item['roi']+'.png']
    if len(matches)!=1:
        raise ValueError('Exactly one source FOV required')
    folder=root/item['case_id']
    with (folder/'csv.csv').open() as stream:
        records=list(csv.DictReader(stream))
    return contour_agreement_region(np.asarray(Image.open(folder/'masks.png')),records,matches[0])


def validate_result_layout(report, protocol):
    inputs={'original','provided'};models={'small_vit','small_vit_refined'};regions={'all','boundary','interior'}
    ids=[r['case_id'] for r in protocol['cases']]
    if len(ids)!=3 or len(set(ids))!=3 or set(protocol['expected_model_sha256'])!=models:
        raise ValueError('Expected three cases and two fixed models')
    if [r['case_id'] for r in report['rows']]!=ids or set(report['means'])!=inputs:
        raise ValueError('Incomplete case/input set')
    expected=set()
    for row in report['rows']:
        if set(row['inputs'])!=inputs:
            raise ValueError('Incomplete paired inputs')
        for rendition,results in row['inputs'].items():
            if set(results)!=models:
                raise ValueError('Incomplete paired models')
            for model,value in results.items():
                name=f'predictions/{row["case_id"]}-{rendition}-{model}.npz'
                if value['probability']!=name or set(value['metrics'])!=regions:
                    raise ValueError('Unexpected probability path or metric region')
                expected.add(name)
    if set(report['predictions'])!=expected:
        raise ValueError('Incomplete probability manifest')
    for values in report['means'].values():
        if set(values)!=models or any(set(metrics)!=regions for metrics in values.values()):
            raise ValueError('Incomplete mean comparison')


def audit(out):
    from pathology_edge.learner_metrics import dice_score
    from pathology_edge.patches import boundary_mask
    lock=read(out/'lock.json');report=read(out/'results.json');protocol=read(out/'protocol.json')
    validate_result_layout(report,protocol)
    if sha(out/'lock.json')!=report['lock_sha256']:
        raise ValueError('Run lock differs')
    for name,digest in lock['files'].items():
        if sha(out/name)!=digest:
            raise ValueError('Input/source hash differs')
    if [r['case_id'] for r in report['rows']]!=[i['case_id'] for i in protocol['cases']]:
        raise ValueError('Case set differs')
    for name,digest in report['predictions'].items():
        if sha(out/name)!=digest:
            raise ValueError('Saved probability hash differs')
    checked=0
    for item,row in zip(protocol['cases'],report['rows']):
        target,valid,coverage=masks(out,item)
        if coverage!=row['coverage']:
            raise ValueError('Annotation coverage differs')
        seam=boundary_mask(target.shape,128,8)
        for rendition,models in row['inputs'].items():
            for model,result in models.items():
                with np.load(out/result['probability'],allow_pickle=False) as z:
                    probability=z['probability']
                if probability.shape!=target.shape or not np.isfinite(probability).all() or np.any((probability<0)|(probability>1)):
                    raise ValueError('Invalid probabilities')
                pred=probability>=.35
                for region,selection in [('all',valid),('boundary',valid&seam),('interior',valid&~seam)]:
                    p,t=pred[selection],target[selection]
                    tp=int(np.count_nonzero(p&t));fp=int(np.count_nonzero(p&~t));fn=int(np.count_nonzero(~p&t))
                    expected=dict(tp=tp,fp=fp,fn=fn,pixels=int(selection.sum()),dice=dice_score(pred,target,selection),
                        iou=tp/(tp+fp+fn) if tp+fp+fn else 1.,precision=tp/(tp+fp) if tp+fp else 0.,recall=tp/(tp+fn) if tp+fn else 0.)
                    if result['metrics'][region]!=expected:
                        raise ValueError('Independent confusion count or Dice differs')
                    checked+=1
    for rendition,models in report['means'].items():
        for model,metrics in models.items():
            for region,value in metrics.items():
                if value!=float(np.mean([r['inputs'][rendition][model]['metrics'][region]['dice'] for r in report['rows']
                                        if r['coverage']['foreground_valid_pixels']>0])):
                    raise ValueError('Macro mean differs')
    result=dict(passed=True,region_checks=checked,mean_checks=12,raw_annotation_reconstruction=True,
                results_sha256=sha(out/'results.json'),new_inference_during_audit=False)
    save(out/'audit.json',result)
    return result


def run(data,models,out):
    import cv2
    import torch
    from pathology_edge.model_comparison import build_model
    from pathology_edge.experiment import predict, environment
    if out.exists():
        raise ValueError('Use a fresh output directory')
    acquisition=read(data/'acquisition.json')
    if not acquisition['all_sources_verified']:
        raise ValueError('Original stream verification required before inference')
    protocol=read(data/'protocol.json')
    for item in acquisition['cases']:
        for name,digest in item['files'].items():
            if sha(data/item['case_id']/name)!=digest:
                raise ValueError('Acquired asset changed')
    shutil.copytree(data,out)
    source=Path(__file__).resolve().parents[1]/'src/pathology_edge'
    shutil.copytree(source,out/'source/pathology_edge',ignore=shutil.ignore_patterns('__pycache__','*.so'))
    shutil.copy2(__file__,out/'runner.py')
    (out/'models').mkdir()
    for architecture,digest in protocol['expected_model_sha256'].items():
        src=models/architecture/'model.pt'
        if sha(src)!=digest:
            raise ValueError('Fixed checkpoint changed')
        shutil.copy2(src,out/'models'/f'{architecture}.pt')
    save(out/'lock.json',dict(phase='before first prediction on these cases',
        files={p.relative_to(out).as_posix():sha(p) for p in sorted(out.rglob('*')) if p.is_file()}))
    torch.set_num_threads(4);cv2.setNumThreads(1);torch.use_deterministic_algorithms(True)
    loaded={}
    for architecture in protocol['expected_model_sha256']:
        model=build_model(architecture)
        model.load_state_dict(torch.load(out/'models'/f'{architecture}.pt',map_location='cpu',weights_only=True))
        loaded[architecture]=model.eval()
    (out/'predictions').mkdir()
    rows=[]
    for item in protocol['cases']:
        target,valid,coverage=masks(out,item)
        row=dict(case_id=item['case_id'],roi=item['roi'],coverage=coverage,inputs={})
        for rendition,filename in [('original','original-roi.png'),('provided','rgbs.png')]:
            image=np.asarray(Image.open(out/item['case_id']/filename).convert('RGB')).copy()
            row['inputs'][rendition]={}
            for architecture,model in loaded.items():
                result=predict(model,image,mode='no_overlap',threshold=.35)
                name=f'predictions/{item["case_id"]}-{rendition}-{architecture}.npz'
                np.savez_compressed(out/name,probability=result['probability'])
                row['inputs'][rendition][architecture]=dict(probability=name,
                    metrics=score_roi(result['probability'],target,valid,.35),patch_count=result['patch_count'],
                    skipped_background=result['skipped_background'])
        rows.append(row)
        print(item['case_id'],flush=True)
    means={rendition:{architecture:{region:float(np.mean([r['inputs'][rendition][architecture]['metrics'][region]['dice'] for r in rows
                                                        if r['coverage']['foreground_valid_pixels']>0]))
             for region in ('all','boundary','interior')} for architecture in loaded} for rendition in ('original','provided')}
    save(out/'results.json',dict(rows=rows,means=means,environment=environment(),lock_sha256=sha(out/'lock.json'),
        predictions={p.relative_to(out).as_posix():sha(p) for p in sorted((out/'predictions').glob('*.npz'))},
        new_cases=3,primary_contour_cases=[r['case_id'] for r in rows if r['coverage']['foreground_valid_pixels']>0],
        background_only_cases=[r['case_id'] for r in rows if r['coverage']['foreground_valid_pixels']==0],
        independent_cases_not_six=True,original_previous3_cases_included=False,
        training_run=False,threshold_tuned=False,clinical_validation=False,full_wsi_gt_validation=False))
    return audit(out)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('data','models','output','audit'):
        parser.add_argument('--'+key,type=Path)
    args=parser.parse_args()
    if args.audit:
        print(json.dumps(audit(args.audit)))
    else:
        if not all((args.data,args.models,args.output)):
            parser.error('--data --models --output required')
        print(json.dumps(run(args.data,args.models,args.output)))
