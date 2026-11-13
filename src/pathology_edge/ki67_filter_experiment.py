"""Frozen candidate-rejection ablation. Reuses classifications; does not retrain them."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import platform
import time
import numpy as np
from PIL import Image
import sklearn
from .ki67_candidate_filter import (
    THRESHOLDS, training_labels, gate_features, fit_gate, gate_scores,
    keep_candidates, select_threshold,
)
from .ki67_detection import detect_centers
from .ki67_experiment import (
    fresh_json, read_json, sha, verify_hashes, validate_manifest, verify_data,
    load_sample, summarize,
)
from .ki67_external import tumor_only_row, fetch_entry, download_url

DETECTOR = {'min_response':.10,'min_distance':8}
SOURCES = ('ihc_baseline.py','ki67_detection.py','ki67_evaluation.py',
           'ki67_candidate_filter.py','ki67_filter_experiment.py',
           'ki67_experiment.py','ki67_cnn.py','ki67_external.py')


def utc():
    return datetime.now(timezone.utc).isoformat()


def subset_row(row, ids):
    if not isinstance(ids,list) or any(isinstance(i,bool) or not isinstance(i,int) for i in ids) or ids != sorted(set(ids)) or any(i<0 or i>=len(row['points']) for i in ids):
        raise ValueError('Expected ordered unique valid candidate indices')
    if any(len(v)!=len(row['points']) for v in row['classes'].values()):
        raise ValueError('Candidate/class count mismatch')
    return {**row,'points':[row['points'][i] for i in ids],
            'classes':{a:[c[i] for i in ids] for a,c in row['classes'].items()}}


def predict_gate(rgb, gate, threshold):
    located = detect_centers(rgb,DETECTOR)
    x = gate_features(rgb,located['points_xy'],located['scores'])
    scores = gate_scores(x,gate)
    ids = np.flatnonzero(keep_candidates(x,gate,threshold)).tolist()
    return dict(points=located['points_xy'],scores=scores,keep_indices=ids)


def prepare(parent, external, output):
    parent, external, output = map(lambda p:Path(p).resolve(),(parent,external,output))
    p = read_json(parent/'protocol.json')
    lock = read_json(parent/'selection-lock.json')
    if lock['protocol_sha256'] != sha(parent/'protocol.json') or lock['detector']['config'] != DETECTOR:
        raise ValueError('Unexpected parent protocol or detector')
    verify_hashes(parent,lock['model_hashes'])
    verify_hashes(parent,p['input_hashes'])
    for folder,predfile,key in [(parent,'predictions.json','predictions_sha256'),
                               (external,'private-predictions.json','private_predictions_sha256')]:
        if sha(folder/predfile) != read_json(folder/'results.json')[key]:
            raise ValueError('Parent prediction digest mismatch')
    # The inference implementation received a finite-model guard later; freeze current
    # sources separately. Baseline arrays and historical model hashes remain immutable.
    rows=read_json(parent/'source-manifest.json')
    validate_manifest(rows,read_json(parent/'split.json')['assignment'])
    output.mkdir(parents=True,exist_ok=False)
    source=Path(__file__).parent
    (output/'source').mkdir()
    for name in SOURCES:
        (output/'source'/name).write_bytes((source/name).read_bytes())
    tracked = {str(parent/n):sha(parent/n) for n in (
        'protocol.json','selection-lock.json','source-manifest.json','split.json',
        'model.json','predictions.json','results.json',*lock['model_hashes'])}
    tracked.update({str(external/n):sha(external/n) for n in (
        'private-predictions.json','results.json','entries.json','input-manifest.json','input-audit.json')})
    protocol=dict(schema='candidate-filter-experiment.v1',created_utc=utc(),
        parent=str(parent),external=str(external),data_dir=p['data_dir'],
        input_hashes=tracked,source_hashes={n:sha(source/n) for n in SOURCES},
        detector=DETECTOR,thresholds=list(THRESHOLDS),matching_radius_px=6,
        proxy_labels='matched<=6px positive; >12px from all GT and 24px edge margin negative proxy; empty-GT patches ignored',
        training='train only; standardized balanced LogisticRegression C1/lbfgs/max_iter2000; no sampling',
        selection='validation case-macro localization F1; >=90% ungated recall in EACH validation case; ties recall then lower threshold',
        reuse='Original candidate classes reused unchanged for all four classifiers. New image-only gate inference; classifiers not retrained.',
        evaluation_scope='Patherea407 and BCData133 previously exposed: re-evaluation only, not fresh external validation',
        clinical_validation=False,whole_wsi_validation=False,
        environment=dict(python=platform.python_version(),numpy=np.__version__,sklearn=sklearn.__version__,platform=platform.platform()))
    fresh_json(output/'protocol.json',protocol)
    return protocol


def checked(output):
    output=Path(output)
    p=read_json(output/'protocol.json')
    for path,digest in p['input_hashes'].items():
        if sha(path)!=digest: raise ValueError('Input hash mismatch: '+path)
    verify_hashes(Path(__file__).parent,p['source_hashes'])
    return output,p


def verify_selection(output):
    output=Path(output)
    lock=read_json(output/'selection-lock.json')
    verify_hashes(output,lock['hashes'])
    return lock


def fit(output):
    output,p=checked(output)
    fresh_json(output/'fit-started.json',{'created_utc':utc()})
    all_rows=read_json(Path(p['parent'])/'source-manifest.json')
    rows=[r for r in all_rows if r['split'] in ('train','validation')]
    verify_data(p['data_dir'],rows)
    train_x,train_y,validation=[],[],[]
    counts={'train':0,'validation':0}
    started=time.perf_counter()
    for i,r in enumerate(rows):
        rgb,gt,_=load_sample(p['data_dir'],r)
        found=detect_centers(rgb,DETECTOR)
        x=gate_features(rgb,found['points_xy'],found['scores'])
        counts[r['split']]+=1
        if r['split']=='train':
            train_x.append(x)
            train_y.append(training_labels(found['points_xy'],gt,rgb.shape[:2]))
        else:
            validation.append(dict(split='validation',case_id=r['case_id'],features=x,
                                   points=found['points_xy'],gt_points=gt))
        if (i+1)%100==0: print('FEATURES '+str(i+1),flush=True)
    labels=np.concatenate(train_y)
    model=fit_gate(np.concatenate(train_x),labels,split='train')
    fresh_json(output/'gate.json',model)
    for s in validation:
        s['scores']=gate_scores(s.pop('features'),model)
    selected=select_threshold(validation,thresholds=p['thresholds'])
    fresh_json(output/'threshold-selection.json',selected)
    fresh_json(output/'training.json',dict(image_counts=counts,
        proxy_counts={str(k):int((labels==k).sum()) for k in (-1,0,1)},
        seconds=time.perf_counter()-started,selected_threshold=selected['threshold'],
        training_run=True,test_used_for_fit_or_selection=False,external_used_for_fit_or_selection=False))
    fresh_json(output/'selection-lock.json',dict(created_utc=utc(),
        hashes={n:sha(output/n) for n in ('protocol.json','gate.json','threshold-selection.json','training.json')},
        evaluation_started=False))
    return selected


def _score(rows,external):
    reports={}
    for arm in rows[0]['classes']:
        scored=[tumor_only_row(r,arm) for r in rows] if external else rows
        report=summarize(scored,arm)
        if external:
            report['two_class_macro_f1']=float(np.mean([r['f1'] for r in report['classes'][:2]]))
            report.pop('macro_f1')
            report['classes']=report['classes'][:2]
            for r in report['per_image']:
                r['two_class_macro_f1']=float(np.mean([v['f1'] for v in r['classes'][:2]]))
                r.pop('macro_f1');r['classes']=r['classes'][:2]
            for k in list(report):
                if k=='per_case' or k.startswith('case_'): report.pop(k)
        reports[arm]=report
    return reports


def evaluate(output, external=False):
    output,p=checked(output)
    verify_selection(output)
    tag='bcdata' if external else 'patherea'
    fresh_json(output/(tag+'-started.json'),dict(created_utc=utc(),selection_lock_sha256=sha(output/'selection-lock.json')))
    model=read_json(output/'gate.json')
    threshold=read_json(output/'threshold-selection.json')['threshold']
    parent=Path(p['external'] if external else p['parent'])
    rows=read_json(parent/('private-predictions.json' if external else 'predictions.json'))
    if external:
        entries={e['name']:e for e in read_json(parent/'entries.json')}
        inputs={e['name']:e for e in read_json(parent/'input-manifest.json')}
        url=download_url()
    else:
        manifest={r['image']:r for r in read_json(parent/'source-manifest.json') if r['split']=='test'}
        if set(manifest)!={r['image'] for r in rows} or len(rows)!=len(manifest):
            raise ValueError('Test prediction/image set mismatch')
        verify_data(p['data_dir'],list(manifest.values()))
    masks,filtered=[],[]
    for i,r in enumerate(rows):
        if external:
            name='BCData/images/validation/'+r['image']+'.png'
            raw,meta=fetch_entry(url,entries[name])
            if meta['sha256']!=inputs[name]['sha256']: raise ValueError('External raw image hash mismatch')
            rgb=np.asarray(Image.open(io.BytesIO(raw)).convert('RGB'))
        else:
            rgb,gt,gc=load_sample(p['data_dir'],manifest[r['image']])
            if gt.tolist()!=r['gt_points'] or gc.tolist()!=r['gt_classes']:
                raise ValueError('Baseline annotation mismatch')
        predicted=predict_gate(rgb,model,threshold)
        if predicted['points'].tolist()!=r['points']:
            raise ValueError('Replayed detector differs from immutable baseline')
        ids=predicted['keep_indices']
        filtered.append(subset_row(r,ids))
        masks.append(dict(image=r['image'],keep_indices=ids,scores=predicted['scores'].tolist()))
        if (i+1)%50==0: print(tag.upper()+' '+str(i+1),flush=True)
    with (output/(tag+'-retention.json')).open('x') as f:
        json.dump(masks,f,separators=(',',':'),allow_nan=False)
    result=dict(scope=p['evaluation_scope'],image_count=len(rows),
        selection_lock_sha256=sha(output/'selection-lock.json'),
        retention_sha256=sha(output/(tag+'-retention.json')),
        baseline_prediction_sha256=sha(parent/('private-predictions.json' if external else 'predictions.json')),
        threshold=threshold,original_candidates=sum(len(r['points']) for r in rows),
        kept_candidates=sum(len(r['points']) for r in filtered),
        baseline=_score(rows,external),filtered=_score(filtered,external),
        new_gate_inference_images=len(rows),classifier_retraining=False,
        classifier_predictions_reused=True,all_detector_replays_identical=True,
        new_unseen_external_validation=False,clinical_validation=False,whole_wsi_validation=False)
    fresh_json(output/(tag+'-results.json'),result)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    prep=sub.add_parser('prepare')
    prep.add_argument('--parent',type=Path,required=True)
    prep.add_argument('--external',type=Path,required=True)
    for name in ('fit','evaluate','external'): sub.add_parser(name)
    for child in sub.choices.values(): child.add_argument('--output',type=Path,required=True)
    a=parser.parse_args()
    if a.command=='prepare': prepare(a.parent,a.external,a.output)
    elif a.command=='fit': fit(a.output)
    else: evaluate(a.output,external=a.command=='external')
    print('DONE '+a.command,flush=True)


if __name__=='__main__': main()
