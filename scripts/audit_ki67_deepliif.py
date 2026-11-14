#!/usr/bin/env python3
"""Separate OpenCV reference extraction and saved external metric recount."""
import argparse,json
from pathlib import Path
import sys
import cv2
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from audit_ki67_union import compare_metrics,exact_points
from pathology_edge.ki67_evaluation import match_points,count_metrics
from pathology_edge.ki67_experiment import read_json,fresh_json,sha,verify_hashes
from pathology_edge.ki67_union_experiment import read_rows
from pathology_edge.ki67_normalized_pipeline import checked_pipeline,ARMS
from pathology_edge.ki67_deepliif import paired_fraction


def verify_reference_mask(mask,points,classes):
    labels_allowed=np.isin(mask,[0,255]).all() and np.all((mask!=0).sum(axis=2)<=1)
    if mask.dtype!=np.uint8 or mask.ndim!=3 or mask.shape[2]!=3 or not labels_allowed:raise ValueError('Independent reference palette differs')
    fg=((mask[:,:,0]==255)|(mask[:,:,2]==255)).astype(np.uint8)
    n,labels,stats,centers=cv2.connectedComponentsWithStats(fg,connectivity=8)
    result=[]
    for k in range(1,n):
        area=int(stats[k,cv2.CC_STAT_AREA])
        if area<=4:continue
        positive=int(np.sum(mask[:,:,0][labels==k]==255))
        if positive*2==area:raise ValueError('Independent reference class tie')
        result.append((float(centers[k,0]),float(centers[k,1]),0 if positive*2>area else 1))
    expected=sorted((float(x),float(y),int(c)) for (x,y),c in zip(points,classes))
    if len(points)!=len(classes) or len(result)!=len(expected) or not np.allclose(np.asarray(sorted(result)).reshape(-1,3),np.asarray(expected).reshape(-1,3),rtol=0,atol=1e-12):raise ValueError('Independent reference centroids/classes differ')


def independent_scores(rows,name,radius):
    loc=np.zeros(3,dtype=np.int64);correct=np.zeros(2,dtype=np.int64);pred=np.zeros(2,dtype=np.int64);target=np.zeros(2,dtype=np.int64);images=[]
    for r in rows:
        pc=np.asarray([0 if c in (0,2) else 1 for c in r['classes'][name]]);tc=np.asarray(r['gt_classes']);xy=np.asarray(r['points']).reshape(-1,2);gt=np.asarray(r['gt_points']).reshape(-1,2)
        pairs=match_points(xy,gt,radius);loc += [len(pairs),len(xy)-len(pairs),len(gt)-len(pairs)]
        good=np.array([sum(pc[i]==tc[j]==c for i,j in pairs) for c in (0,1)]);pp=np.array([(pc==c).sum() for c in (0,1)]);tt=np.array([(tc==c).sum() for c in (0,1)]);correct+=good;pred+=pp;target+=tt
        cls=[count_metrics(good[c],pp[c]-good[c],tt[c]-good[c]) for c in (0,1)]
        images.append(dict(image=r['image'],localization=count_metrics(len(pairs),len(xy)-len(pairs),len(gt)-len(pairs)),classes=cls,two_class_macro_f1=float(np.mean([v['f1'] for v in cls])),gt_cells=len(gt),pred_cells=len(xy),gt_positive=int(tt[0]),pred_positive=int(pp[0]),gt_fraction=float(tt[0]/len(gt)) if len(gt) else None,pred_fraction=float(pp[0]/len(xy)) if len(xy) else None))
    cls=[count_metrics(correct[c],pred[c]-correct[c],target[c]-correct[c]) for c in (0,1)]
    return dict(localization=count_metrics(*loc),classes=cls,two_class_macro_f1=float(np.mean([v['f1'] for v in cls])),image_count=len(rows),radius_native_px=radius,per_image=images)


def audit(root,output):
    root,output=Path(root),Path(output);_,models,choices=checked_pipeline(root);eligible=[m for m in models if m['selected'] is not None]
    if not eligible:
        if read_json(output/'not-run.json')['new_inference_images']!=0 or (output/'evaluation-lock.json').exists():raise ValueError('Ineligible external evaluation occurred')
        return dict(all_checks_passed=True,new_inference_images=0,reference_images_verified=0,reason='No eligible primary model')
    lock=read_json(output/'evaluation-lock.json');summary=read_json(output/'summary.json');verify_hashes('/',lock['input_hashes']);verify_hashes('/',lock['source_hashes']);verify_hashes(output,summary['evidence_hashes'])
    if lock['classifier_lock_sha256']!=sha(root/'classifier-lock.json'):raise ValueError('External model lock differs')
    refs=read_rows(output/'input-audit.json.gz');names=[r['image'] for r in refs]
    if len(refs)!=597 or len(set(names))!=597 or not all(r['independent_reference_checked'] for r in refs):raise ValueError('External reference coverage differs')
    checks=0;passed={}
    for m in eligible:
        seed=m['seed'];folder=output/f'seed-{seed}';stored=read_rows(folder/'scores.json.gz')[0];comparison=read_json(folder/'comparison.json');computed={}
        for arm in ('A','B'):
            rows=read_rows(folder/(arm+'.json.gz'))
            if [r['image'] for r in rows]!=names:raise ValueError('External image correspondence differs')
            for row,ref in zip(rows,refs):
                exact_points(row['gt_points'],ref['gt_points'])
                if row['gt_classes']!=ref['gt_classes']:raise ValueError('External reference classes differ')
            computed[arm]={}
            for radius in (6,12):
                computed[arm][str(radius)]={}
                for name in ARMS:
                    actual=independent_scores(rows,name,radius);compare_metrics(actual,stored[arm][str(radius)][name]);computed[arm][str(radius)][name]=actual;checks+=1
        c=choices[seed]
        for radius in ('6','12'):
            a=computed['A'][radius][c['reference_classifier']];b=computed['B'][radius][c['selected_classifier']];fraction=paired_fraction(a['per_image'],b['per_image']);compare_metrics(fraction,comparison[radius]['fractions'])
            result=b['localization']['f1']>a['localization']['f1'] and b['two_class_macro_f1']>a['two_class_macro_f1'] and fraction['passed']
            if result!=comparison[radius]['passed']:raise ValueError('External success criterion differs')
            if radius=='6':passed[seed]=result
    if summary['denominator']!=3 or summary['passes']!=sum(passed.values()) or summary['all_three_passed']!=(len(passed)==3 and all(passed.values())):raise ValueError('External stability denominator differs')
    return dict(all_checks_passed=True,new_inference_images=597,reference_images_verified=597,metric_summaries=checks,denominator=3,passes=sum(passed.values()),reference_audit='Separate OpenCV connected components during original streaming, plus saved metric recount; no second raw model replay in this external audit')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--output',required=True);a=p.parse_args();r=audit(a.run,a.output);fresh_json(Path(a.output)/'audit.json',r);print(json.dumps(r))
