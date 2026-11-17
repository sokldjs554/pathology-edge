"""Frozen image-only Ki67 experiment. Training, selection and scoring are separate stages."""
from __future__ import annotations
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import time

import numpy as np
from PIL import Image
import torch
from .ihc_baseline import CLASSES, MASK_NAMES, read_points, classification_metrics
from .ki67_detection import response_map, select_peaks, detect_centers
from .ki67_evaluation import evaluate_cells, match_points, count_metrics, positive_fraction
from .ki67_cnn import cell_crops, CellClassifier, classify_centers, predict_image

SEEDS = (20261113, 20261114, 20261115)
SOURCE_NAMES = ('ihc_baseline.py', 'ki67_detection.py', 'ki67_evaluation.py', 'ki67_cnn.py', 'ki67_experiment.py')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for data in iter(lambda: f.read(1024*1024), b''):
            h.update(data)
    return h.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text())


def fresh_json(path, value):
    payload = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n'
    with Path(path).open('x') as f:
        f.write(payload)


def verify_hashes(root, expected):
    for name, digest in expected.items():
        path = Path(root)/name
        if not path.is_file() or sha(path) != digest:
            raise ValueError('File hash mismatch: '+name)


def source_hashes():
    return {name:sha(Path(__file__).parent/name) for name in SOURCE_NAMES}


def validate_manifest(rows, assignment):
    if not rows or len({r['image'] for r in rows}) != len(rows) or {r['image'] for r in rows} != set(assignment):
        raise ValueError('Manifest image set mismatch')
    cases, pixels = defaultdict(set), defaultdict(set)
    for r in rows:
        if Path(r['image']).name != r['image'] or r['split'] not in ('train', 'validation', 'test') or assignment[r['image']] != r['split']:
            raise ValueError('Invalid image or split')
        cases[r['case_id']].add(r['split'])
        pixels[r['pixel_sha256']].add(r['split'])
    if any(len(v)>1 for v in cases.values()):
        raise ValueError('Cross-split case leak')
    if any(len(v)>1 for v in pixels.values()):
        raise ValueError('Cross-split pixel leak')


def verify_data(data, rows):
    for r in rows:
        expected = {'images/'+r['image']:r['image_sha256']}
        expected.update({'labels/'+Path(r['image']).stem+'_'+c+'.png':h for c,h in r['mask_sha256'].items()})
        verify_hashes(data, expected)


def load_sample(data, r):
    rgb = np.asarray(Image.open(Path(data)/'images'/r['image']).convert('RGB'))
    masks = {c:np.asarray(Image.open(Path(data)/'labels'/(Path(r['image']).stem+'_'+c+'.png'))) for c in MASK_NAMES}
    points, classes = read_points(masks)
    if rgb.shape[:2] != masks['normal_cell'].shape:
        raise ValueError('Image / annotation dimensions differ')
    if hashlib.sha256(rgb.tobytes()).hexdigest() != r['pixel_sha256']:
        raise ValueError('Decoded pixel hash mismatch')
    if np.bincount(classes, minlength=4).tolist() != [r['class_counts'][c] for c in CLASSES]:
        raise ValueError('Annotation count mismatch')
    return rgb, points, classes


def prepare(data, assets, output):
    data, assets, output = Path(data).resolve(), Path(assets).resolve(), Path(output).resolve()
    rows, split = read_json(assets/'source-manifest.json'), read_json(assets/'split.json')
    validate_manifest(rows, split['assignment'])
    verify_data(data, rows)  # Hashes only: test images/annotations are not decoded or scored here.
    output.mkdir(parents=True, exist_ok=False)
    for name in ('source-manifest.json','split.json','model.json'):
        (output/name).write_bytes((assets/name).read_bytes())
    protocol = {'schema':'auto-ki67.v1', 'created_utc':datetime.now(timezone.utc).isoformat(), 'data_dir':str(data),
        'input_hashes':{n:sha(output/n) for n in ('source-manifest.json','split.json','model.json')},
        'source_hashes':source_hashes(), 'seeds':list(SEEDS), 'epochs':12, 'batch_size':64, 'learning_rate':.001,
        'torch_threads':2, 'matching_radius_px':6, 'crop_size_px':48,
        'detector_grid':{'min_response':[.03,.06,.10], 'min_distance':[4,6,8], 'sigma':[1.5,2.5,3.5]},
        'selection':'detector: validation case-macro localization F1; CNN: validation GT-center four-class macro-F1; earliest epoch tie',
        'fixed_split':split['subsets'], 'test_exposure':'407 previously used test images; not a new untouched holdout',
        'inference_uses_gt_centers':False, 'clinical_validation':False, 'whole_wsi_validation':False,
        'environment':{'python':platform.python_version(),'torch':torch.__version__,'numpy':np.__version__,'platform':platform.platform()}}
    fresh_json(output/'protocol.json', protocol)
    return protocol


def checked_run(output):
    output = Path(output)
    protocol = read_json(output/'protocol.json')
    verify_hashes(output, protocol['input_hashes'])
    verify_hashes(Path(__file__).parent, protocol['source_hashes'])
    rows = read_json(output/'source-manifest.json')
    validate_manifest(rows, read_json(output/'split.json')['assignment'])
    return output, protocol, rows


def select_detector(samples):
    if not samples or any(s['split'] != 'validation' for s in samples):
        raise ValueError('Detector selection accepts validation samples only')
    trials = []
    for response in (.03,.06,.10):
        for distance in (4,6,8):
            cases = defaultdict(lambda:np.zeros(3,dtype=np.int64))
            for s in samples:
                p,_ = select_peaks(s['response'], response, distance)
                matches = len(match_points(p,s['points'],6))
                cases[s['case_id']] += [matches,len(p)-matches,len(s['points'])-matches]
            score = float(np.mean([count_metrics(*counts)['f1'] for counts in cases.values()]))
            trials.append({'config':{'min_response':response,'min_distance':distance},'case_macro_f1':score})
    chosen = max(trials,key=lambda t:(t['case_macro_f1'],t['config']['min_response'],t['config']['min_distance']))
    return {'config':chosen['config'],'trials':trials}


def _tensor(crops):
    return torch.from_numpy(crops.transpose(0,3,1,2).copy()).float()/255


def train_classifier(train_crops, train_classes, val_crops, val_classes, seed, output):
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    torch.use_deterministic_algorithms(True)
    model = CellClassifier()
    optimizer = torch.optim.Adam(model.parameters(),lr=.001)
    counts = np.bincount(train_classes,minlength=4)
    if (counts == 0).any():
        raise ValueError('Training requires all four classes')
    weights = torch.tensor(len(train_classes)/(4*counts),dtype=torch.float32)
    history, best, best_epoch, best_state = [], -1., None, None
    started = time.perf_counter()
    for epoch in range(1,13):
        model.train()
        order = rng.permutation(len(train_crops))
        loss_sum = 0.
        for start in range(0,len(order),64):
            ids = order[start:start+64]
            x = _tensor(train_crops[ids])
            # Seeded flips / rotations and RGB multiplicative jitter, training only.
            for i in range(len(x)):
                x[i] = torch.rot90(x[i],int(rng.integers(4)),(1,2))
                if rng.random()<.5:
                    x[i] = x[i].flip(2)
                if rng.random()<.5:
                    x[i] = x[i].flip(1)
            x = (x*torch.tensor(rng.uniform(.9,1.1,(len(x),3,1,1)),dtype=torch.float32)).clamp(0,1)
            optimizer.zero_grad(set_to_none=True)
            loss = torch.nn.functional.cross_entropy(model(x),torch.from_numpy(train_classes[ids]),weight=weights)
            loss.backward()
            optimizer.step()
            loss_sum += loss.item()*len(ids)
        model.eval()
        predicted = []
        with torch.inference_mode():
            for start in range(0,len(val_crops),128):
                predicted.extend(model(_tensor(val_crops[start:start+128])).argmax(1).tolist())
        metrics = classification_metrics(val_classes,np.asarray(predicted))
        item = {'epoch':epoch,'train_loss':loss_sum/len(train_crops),'validation_macro_f1':metrics['macro_f1']}
        history.append(item)
        print(json.dumps({'seed':seed,**item}),flush=True)
        if metrics['macro_f1']>best:
            best, best_epoch = metrics['macro_f1'], epoch
            best_state = {k:v.detach().clone() for k,v in model.state_dict().items()}
    filename = f'cnn-{seed}.pt'
    torch.save(best_state,Path(output)/filename)
    return {'seed':seed,'checkpoint':filename,'sha256':sha(Path(output)/filename),'best_epoch':best_epoch,
            'validation_macro_f1':best,'history':history,'training_seconds':time.perf_counter()-started,
            'training_class_weights':weights.tolist(),'parameter_count':sum(p.numel() for p in model.parameters())}


def fit(output):
    output, protocol, rows = checked_run(output)
    if (output/'selection-lock.json').exists():
        raise FileExistsError('Selection already locked')
    fresh_json(output/'fit-started.json',{'started_utc':datetime.now(timezone.utc).isoformat()})
    torch.set_num_threads(protocol['torch_threads'])
    selected = [r for r in rows if r['split'] in ('train','validation')]
    verify_data(protocol['data_dir'],selected)
    crops, labels = defaultdict(list),defaultdict(list)
    validation = []
    for r in selected:
        rgb, points, classes = load_sample(protocol['data_dir'],r)
        crops[r['split']].append(cell_crops(rgb,points))
        labels[r['split']].append(classes)
        if r['split']=='validation':
            validation.append({'split':'validation','case_id':r['case_id'],'response':response_map(rgb),'points':points})
    detector = select_detector(validation)
    fresh_json(output/'detector-selection.json',detector)
    print('DETECTOR '+json.dumps(detector['config']),flush=True)
    x,y = {s:np.concatenate(crops[s]) for s in crops},{s:np.concatenate(labels[s]) for s in labels}
    models = [train_classifier(x['train'],y['train'],x['validation'],y['validation'],seed,output) for seed in SEEDS]
    selection = {'created_utc':datetime.now(timezone.utc).isoformat(), 'protocol_sha256':sha(output/'protocol.json'),
                 'source_hashes':source_hashes(),'detector':detector,'models':models,
                 'model_hashes':{m['checkpoint']:m['sha256'] for m in models},'test_evaluation_started':False}
    fresh_json(output/'selection-lock.json',selection)
    return selection


def load_models(output, selection):
    verify_hashes(output, selection['model_hashes'])
    models = {'lr':read_json(Path(output)/'model.json')}
    for m in selection['models']:
        model = CellClassifier()
        model.load_state_dict(torch.load(Path(output)/m['checkpoint'],map_location='cpu',weights_only=True),strict=True)
        models[f"cnn-{m['seed']}"] = model.eval()
    return models


def _aggregate(evaluations, gt_classes, pred_classes):
    loc = count_metrics(*np.sum([[e['localization'][k] for k in ('tp','fp','fn')] for e in evaluations],axis=0))
    classes = [count_metrics(*np.sum([[e['classes'][c][k] for k in ('tp','fp','fn')] for e in evaluations],axis=0)) for c in range(4)]
    gt, pred = positive_fraction(gt_classes),positive_fraction(pred_classes)
    return {'localization':loc,'classes':classes,'macro_f1':float(np.mean([c['f1'] for c in classes])),
            'target_fraction':gt,'predicted_fraction':pred,
            'ratio_error_pp':None if gt['fraction'] is None or pred['fraction'] is None else abs(gt['fraction']-pred['fraction'])*100,
            'count_error':len(pred_classes)-len(gt_classes)}


def summarize(rows, arm):
    if not rows:
        raise ValueError('Cannot summarize empty evaluation')
    evaluations, by_case, per_image = [],defaultdict(list),[]
    for i,r in enumerate(rows):
        e = evaluate_cells(np.asarray(r['points']).reshape(-1,2),r['classes'][arm],np.asarray(r['gt_points']).reshape(-1,2),r['gt_classes'])
        evaluations.append(e)
        by_case[r['case_id']].append(i)
        per_image.append({'image':r['image'],'case_id':r['case_id'],**_aggregate([e],r['gt_classes'],r['classes'][arm])})
    def group(ids):
        return _aggregate([evaluations[i] for i in ids],[c for i in ids for c in rows[i]['gt_classes']],
                          [c for i in ids for c in rows[i]['classes'][arm]])
    overall = group(range(len(rows)))
    per_case = [{'case_id':case,**group(ids)} for case,ids in sorted(by_case.items())]
    overall.update(per_image=per_image,per_case=per_case,image_count=len(rows),case_count=len(by_case))
    for kind, values in [('image',per_image),('case',per_case)]:
        valid = [v['ratio_error_pp'] for v in values if v['ratio_error_pp'] is not None]
        overall[kind+'_ratio_mae_pp'] = float(np.mean(valid)) if valid else None
        overall[kind+'_ratio_valid'] = len(valid)
        overall[kind+'_count_mae'] = float(np.mean([abs(v['count_error']) for v in values]))
    matched = sum(e['localization']['tp'] for e in evaluations)
    correct = sum(np.trace(e['matched_confusion']) for e in evaluations)
    overall['matched_only_accuracy'] = float(correct/matched) if matched else None
    return overall


def evaluate(output):
    output, protocol, rows = checked_run(output)
    selection = read_json(output/'selection-lock.json')
    if selection['protocol_sha256'] != sha(output/'protocol.json') or selection['source_hashes'] != source_hashes():
        raise ValueError('Selection lock does not match protocol/source')
    models = load_models(output,selection)
    fresh_json(output/'evaluation-started.json',{'selection_lock_sha256':sha(output/'selection-lock.json'),
        'created_utc':datetime.now(timezone.utc).isoformat()})
    torch.set_num_threads(protocol['torch_threads'])
    test = [r for r in rows if r['split']=='test']
    verify_data(protocol['data_dir'],test)
    predictions = []
    for i,r in enumerate(test):
        rgb, gt_points, gt_classes = load_sample(protocol['data_dir'],r)
        start = time.perf_counter()
        located = detect_centers(rgb,selection['detector']['config'])
        points = located['points_xy']
        row = {'image':r['image'],'case_id':r['case_id'],'points':points.tolist(),'gt_points':gt_points.tolist(),
               'gt_classes':gt_classes.tolist(),'classes':{},'pipeline_seconds':{}}
        detector_seconds = time.perf_counter()-start
        for name,model in models.items():
            start = time.perf_counter()
            row['classes'][name] = classify_centers(rgb,points,model).argmax(1).tolist()
            row['pipeline_seconds'][name] = detector_seconds+time.perf_counter()-start
        predictions.append(row)
        if (i+1)%50==0:
            print('EVALUATED '+str(i+1),flush=True)
    # Compact sufficient statistics preserve points and every class, not dense maps.
    with (output/'predictions.json').open('x') as f:
        json.dump(predictions,f,separators=(',',':'),allow_nan=False)
    result = {'schema':'auto-ki67-results.v1','selection_lock_sha256':sha(output/'selection-lock.json'),
              'predictions_sha256':sha(output/'predictions.json'),'scope':'Automatic IHC patch analysis on reused Patherea test; not WSI or clinical validation',
              'matching':'Class-blind maximum cardinality, minimum distance; <=6 native pixels',
              'inference_uses_gt_centers':False,'training_seeds':list(SEEDS),'arms':{a:summarize(predictions,a) for a in models}}
    for a in models:
        result['arms'][a]['median_pipeline_seconds'] = float(np.median([r['pipeline_seconds'][a] for r in predictions]))
    fresh_json(output/'results.json',result)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command',required=True)
    prep = sub.add_parser('prepare')
    prep.add_argument('--data-dir',type=Path,required=True)
    prep.add_argument('--assets',type=Path,default=Path('artifacts/ihc'))
    prep.add_argument('--output',type=Path,required=True)
    for name in ('fit','evaluate'):
        sub.add_parser(name).add_argument('--output',type=Path,required=True)
    infer = sub.add_parser('infer')
    infer.add_argument('--run',type=Path,required=True)
    infer.add_argument('--image',type=Path,required=True)
    infer.add_argument('--classifier',default='lr')
    infer.add_argument('--output',type=Path,required=True)
    a = p.parse_args()
    if a.command=='prepare':
        prepare(a.data_dir,a.assets,a.output)
    elif a.command=='fit':
        fit(a.output)
    elif a.command=='evaluate':
        evaluate(a.output)
    else:
        root,protocol,_ = checked_run(a.run)
        lock = read_json(root/'selection-lock.json')
        if lock['protocol_sha256'] != sha(root/'protocol.json') or lock['source_hashes'] != source_hashes():
            raise ValueError('Selection lock mismatch')
        torch.set_num_threads(protocol['torch_threads'])
        models = load_models(root,lock)
        if a.classifier not in models:
            raise ValueError('Unknown classifier')
        rgb = np.asarray(Image.open(a.image).convert('RGB'))
        result = predict_image(rgb,lock['detector']['config'],models[a.classifier])
        fresh_json(a.output,{k:v.tolist() if isinstance(v,np.ndarray) else v for k,v in result.items()})
    print('DONE '+a.command,flush=True)


if __name__=='__main__':
    main()
