"""Recount stored point predictions without importing the production evaluator."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import maximum_bipartite_matching


def metrics(tp, called, support):
    return dict(tp=int(tp),fp=int(called-tp),fn=int(support-tp),precision=float(tp/called) if called else 0.,
                recall=float(tp/support) if support else 0., f1=float(2*tp/(called+support)) if called+support else 0.)


def ratio(counts):
    pos,den = int(counts[0]),int(counts[0]+counts[1])
    return dict(positive_tumor_cells=pos,tumor_cells=den,fraction=pos/den if den else None)


def recount(row, arm, external):
    pred = np.asarray(row['points']).reshape(-1,2)
    pc = np.asarray(row['classes'][arm],dtype=int)
    if external:
        ids=np.isin(pc,[0,1]); pred,pc=pred[ids],pc[ids]
    gt=np.asarray(row['gt_points']).reshape(-1,2)
    gc=np.asarray(row['gt_classes'],dtype=int)
    n,m=len(pred),len(gt)
    tp=np.zeros(4,dtype=int)
    matched=0
    if n and m:
        d=np.sqrt(((pred[:,None,:]-gt[None,:,:])**2).sum(2))
        permitted=d<=6
        maximum=int((maximum_bipartite_matching(csr_matrix(permitted),perm_type='column')>=0).sum())
        penalty=min(n,m)+1
        costs=np.concatenate([np.where(permitted,d/6,2*penalty),np.full((n,n),penalty)],axis=1)
        ii,jj=linear_sum_assignment(costs)
        for i,j in zip(ii,jj):
            if j<m and permitted[i,j]:
                matched+=1
                if pc[i]==gc[j]: tp[pc[i]]+=1
        if matched!=maximum: raise ValueError('Matching cardinality is not maximal')
    return dict(tp=tp,matched=matched,called=np.bincount(pc,minlength=4),support=np.bincount(gc,minlength=4))


def aggregate(stats, external):
    tp=np.sum([s['tp'] for s in stats],axis=0)
    pc=np.sum([s['called'] for s in stats],axis=0)
    gc=np.sum([s['support'] for s in stats],axis=0)
    matched=sum(s['matched'] for s in stats)
    classes=[metrics(tp[c],pc[c],gc[c]) for c in range(2 if external else 4)]
    pr,gr=ratio(pc),ratio(gc)
    return dict(localization=metrics(matched,pc.sum(),gc.sum()),classes=classes,
                predicted_fraction=pr,target_fraction=gr,
                ratio_error_pp=None if pr['fraction'] is None or gr['fraction'] is None else abs(pr['fraction']-gr['fraction'])*100,
                count_error=int(pc.sum()-gc.sum()),
                **{('two_class_macro_f1' if external else 'macro_f1'):float(np.mean([v['f1'] for v in classes]))})


def compare(expected, actual, where='root'):
    if isinstance(expected,dict):
        for k,v in expected.items(): compare(v,actual[k],where+'.'+k)
    elif isinstance(expected,list):
        if len(expected)!=len(actual): raise ValueError('Length mismatch '+where)
        for i,(x,y) in enumerate(zip(expected,actual)): compare(x,y,where+f'[{i}]')
    elif expected is None or isinstance(expected,str):
        if expected!=actual: raise ValueError('Mismatch '+where)
    elif not np.isclose(expected,actual,rtol=0,atol=1e-12):
        raise ValueError(f'Mismatch {where}: {expected} != {actual}')


def audit(run, external=False):
    run=Path(run)
    records=json.loads((run/('private-predictions.json' if external else 'predictions.json')).read_text())
    published=json.loads((run/'results.json').read_text())
    for arm,report in published['arms'].items():
        stats=[recount(r,arm,external) for r in records]
        images=[]
        for r,s,old in zip(records,stats,report['per_image']):
            if r['image']!=old['image']: raise ValueError('Image order mismatch')
            result=aggregate([s],external); compare(result,old,r['image']+'/'+arm); images.append(result)
        total=aggregate(stats,external); compare(total,report,arm)
        matched=sum(s['matched'] for s in stats)
        compare(None if not matched else sum(int(s['tp'].sum()) for s in stats)/matched,report['matched_only_accuracy'])
        groups=defaultdict(list)
        if not external:
            for r,s in zip(records,stats): groups[r['case_id']].append(s)
            cases=[]
            for old in report['per_case']:
                value=aggregate(groups[old['case_id']],False); compare(value,old); cases.append(value)
        for kind,values in [('image',images)]+([] if external else [('case',cases)]):
            errors=[v['ratio_error_pp'] for v in values if v['ratio_error_pp'] is not None]
            compare(len(errors),report[kind+'_ratio_valid'])
            compare(float(np.mean(errors)) if errors else None,report[kind+'_ratio_mae_pp'])
            compare(float(np.mean([abs(v['count_error']) for v in values])),report[kind+'_count_mae'])
    predfile=run/('private-predictions.json' if external else 'predictions.json')
    digest=hashlib.sha256(predfile.read_bytes()).hexdigest()
    compare(digest,published['private_predictions_sha256' if external else 'predictions_sha256'])
    result={'all_checks_passed':True,'image_count':len(records),'arms':list(published['arms']),
            'image_arm_recounts':len(records)*len(published['arms']),
            'maximum_cardinality_independent_solver':'scipy.sparse.csgraph.maximum_bipartite_matching',
            'prediction_sha256':digest,'new_inference_run':False,'clinical_validation':False}
    print(json.dumps(result))
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',type=Path,required=True)
    p.add_argument('--external',action='store_true')
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    result=audit(a.run,a.external)
    with a.output.open('x') as f: json.dump(result,f,indent=2)
