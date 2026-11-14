"""Prospectively locked BCData validation transfer. No fitting on external data.

Only tumor annotations exist: filter predictions to classes 0/1 and never report
four-class accuracy or non-tumor sensitivity. Raw data stay private in memory.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
import struct
import time
import urllib.parse
import urllib.request
import urllib.error
import zlib
import numpy as np
from PIL import Image
import torch
from .ki67_experiment import read_json, fresh_json, sha, checked_run, load_models, summarize, source_hashes
from .ki67_detection import detect_centers
from .ki67_cnn import classify_centers

ARCHIVE_BYTES = 853879248
ARCHIVE_MANIFEST_SHA = 'c40aa87b806ed2fef45359e61d449555419d6b1d351725c96015a977aa3efb92'
PAGE_URL = 'https://drive.usercontent.google.com/download?id=16W04QOR1E-G3ifc4061Be4eGpjRYDlkA&export=download'


def canonical_points(positive, negative):
    arrays, duplicates = [], 0
    for source in (positive,negative):
        a = np.asarray(source)
        if a.shape == (0,):
            a = a.reshape(0,2)
        if a.ndim != 2 or a.shape[1] != 2 or a.dtype.kind not in 'iuf' or not np.isfinite(a).all() or np.any(a != np.floor(a)) or np.any(a<0) or np.any(a>=640):
            raise ValueError('Invalid BCData point coordinates')
        unique = list(dict.fromkeys(map(tuple,a.astype(np.int64).tolist())))
        duplicates += len(a)-len(unique)
        arrays.append(np.asarray(unique,dtype=np.int64).reshape(-1,2))
    if set(map(tuple,arrays[0])) & set(map(tuple,arrays[1])):
        raise ValueError('Conflicting positive/negative point labels')
    return np.concatenate(arrays),np.concatenate([np.full(len(a),i,dtype=np.int64) for i,a in enumerate(arrays)]),{'duplicate_records_removed':duplicates}


def tumor_only_row(row, arm):
    ids = [i for i,c in enumerate(row['classes'][arm]) if c in (0,1)]
    return {**row,'case_id':row['image'],'points':[row['points'][i] for i in ids],
            'classes':{arm:[row['classes'][arm][i] for i in ids]}}


def validate_external_entries(entries):
    names = [e['name'] for e in entries]
    images = sorted(n for n in names if re.fullmatch(r'BCData/images/validation/\d+\.png',n))
    expected = set(images)
    for name in images:
        for label in ('positive','negative'):
            expected.add(f'BCData/annotations/validation/{label}/{Path(name).stem}.h5')
    if len(images)!=133 or len(names)!=399 or len(set(names))!=399 or set(names)!=expected:
        raise ValueError('Expected exactly 133 complete BCData validation triples')
    return images


def prepare_external(run, archive_manifest, output, prior_audit):
    root,protocol,_ = checked_run(run)
    # Preparation can precede fit completion; evaluation requires the exact later lock.
    if sha(archive_manifest) != ARCHIVE_MANIFEST_SHA:
        raise ValueError('Original full archive manifest hash mismatch')
    entries = [e for e in read_json(archive_manifest) if '/validation/' in e['name'] and not e['name'].endswith('/')]
    images = validate_external_entries(entries)
    prior = read_json(prior_audit)
    if prior.get('image_count')!=402:
        raise ValueError('Expected prior 402-image test audit')
    output = Path(output)
    output.mkdir(parents=True,exist_ok=False)
    fresh_json(output/'entries.json',entries)
    fresh_json(output/'prior-test-pixel-hashes.json',[e['pixel_sha256'] for e in prior['images']])
    external = {'created_utc':datetime.now(timezone.utc).isoformat(),'run_protocol_sha256':sha(root/'protocol.json'),
        'external_source_sha256':sha(Path(__file__)),'entries_sha256':sha(output/'entries.json'),
        'prior_test_pixels_sha256':sha(output/'prior-test-pixel-hashes.json'),
        'images':images,'image_count':133,'selection':'all official validation images, fixed before inference',
        'known_exposure':'Official BCData test402 previously evaluated; these validation images not used for model selection in this project',
        'ground_truth':'positive and negative tumor center coordinates only; no non-tumor references',
        'comparison':'same frozen detector and LR vs all three CNN seeds; no adaptation or threshold tuning',
        'matching':'class-blind tumor-prediction matching <=6 native px, maximum cardinality then minimum distance',
        'primary_metrics':['pooled two-class end-to-end macro-F1','per-image tumor-positive-fraction MAE percentage points with valid denominator coverage'],
        'data_quality':'same-class exact duplicate points canonicalized; reject conflicts/nonfinite/fractional/out-of-bounds; never remove by model outcome',
        'overlap_policy':'compare decoded whole-image hashes within external, against Patherea1330 and previous BCData402; stop on exact overlap',
        'independence_limit':'No patient/slide IDs or verified MPP; exact image checks cannot exclude shared patients, slides or partial crops',
        'reference_limit':'Tumor annotation benchmark only; not four-class/non-tumor/clinical/whole-slide validation; published-method evaluation protocols may differ',
        'source_url':'https://sites.google.com/view/bcdataset','source_archive':PAGE_URL,
        'license':'Non-commercial research; raw RGB/HDF5/individual coordinates not redistributed',
        'archive_bytes':ARCHIVE_BYTES,'archive_manifest_sha256':ARCHIVE_MANIFEST_SHA,'full_archive_sha256':None}
    fresh_json(output/'external-protocol.json',external)
    return external


def download_url():
    with urllib.request.urlopen(PAGE_URL,timeout=35) as r:
        page = r.read(200000).decode()
    fields = dict(re.findall(r'<input[^>]+name="([^"]+)"[^>]+value="([^"]*)"',page))
    form = re.search(r'<form[^>]+action="([^"]+)"',page)
    if form is None or form.group(1)!='https://drive.usercontent.google.com/download':
        raise ValueError('Unexpected public archive download form')
    return form.group(1)+'?'+urllib.parse.urlencode(fields)


def fetch_entry(url, entry):
    low = entry['offset']
    high = low+entry['compressed_bytes']+1024
    request = urllib.request.Request(url,headers={'Range':f'bytes={low}-{high}'})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request,timeout=45) as r:
                if r.status!=206 or r.headers.get('Content-Range')!=f'bytes {low}-{high}/{ARCHIVE_BYTES}':
                    raise ValueError('Refuse full or mismatched archive response')
                raw = r.read(high-low+2)
            break
        except (TimeoutError,urllib.error.URLError):
            if attempt==3:
                raise
            time.sleep(2**attempt)
    if len(raw)!=high-low+1:
        raise ValueError('Incomplete byte range')
    header = struct.unpack_from('<4s5H3L2H',raw)
    nlen,elen = header[-2:]
    if header[0]!=b'PK\x03\x04' or header[3]!=entry['method'] or entry['method']!=8 or raw[30:30+nlen].decode()!=entry['name']:
        raise ValueError('ZIP local header mismatch')
    start = 30+nlen+elen
    data = zlib.decompress(raw[start:start+entry['compressed_bytes']],-15)
    if len(data)!=entry['uncompressed_bytes'] or zlib.crc32(data)!=entry['crc32']:
        raise ValueError('ZIP size/CRC mismatch')
    return data,{**entry,'sha256':hashlib.sha256(data).hexdigest(),'range_bytes':len(raw)}


def evaluate_external(run, output):
    import h5py  # Acquisition optional dependency; never imported by core/test collection.
    root,protocol,source_rows = checked_run(run)
    output = Path(output)
    external = read_json(output/'external-protocol.json')
    for path,key in [(root/'protocol.json','run_protocol_sha256'),(Path(__file__),'external_source_sha256'),
                     (output/'entries.json','entries_sha256'),(output/'prior-test-pixel-hashes.json','prior_test_pixels_sha256')]:
        if sha(path)!=external[key]:
            raise ValueError('External lock hash mismatch: '+str(path))
    lock = read_json(root/'selection-lock.json')
    if lock['protocol_sha256']!=sha(root/'protocol.json') or lock['source_hashes']!=source_hashes():
        raise ValueError('Model selection lock mismatch')
    models = load_models(root,lock)
    entries = read_json(output/'entries.json')
    images = validate_external_entries(entries)
    entries = {e['name']:e for e in entries}
    fresh_json(output/'inference-lock.json',{'selection_lock_sha256':sha(root/'selection-lock.json'),
               'external_protocol_sha256':sha(output/'external-protocol.json'),'created_utc':datetime.now(timezone.utc).isoformat()})
    torch.set_num_threads(protocol['torch_threads'])
    forbidden = {r['pixel_sha256'] for r in source_rows} | set(read_json(output/'prior-test-pixel-hashes.json'))
    observed, input_records, predictions, audits = set(),[],[],[]
    url = download_url()
    with ThreadPoolExecutor(max_workers=3) as pool:
        for i,name in enumerate(images):
            stem = Path(name).stem
            names = [name]+[f'BCData/annotations/validation/{c}/{stem}.h5' for c in ('positive','negative')]
            fetched = list(pool.map(lambda n:fetch_entry(url,entries[n]),names))
            image = Image.open(io.BytesIO(fetched[0][0]))
            if image.mode!='RGB' or image.size!=(640,640):
                raise ValueError('Unexpected native RGB geometry')
            rgb = np.asarray(image)
            pixel_sha = hashlib.sha256(rgb.tobytes()).hexdigest()
            if pixel_sha in forbidden or pixel_sha in observed:
                raise ValueError('Exact image overlap: '+name)
            observed.add(pixel_sha)
            arrays = []
            for raw,_ in fetched[1:]:
                with h5py.File(io.BytesIO(raw),'r') as h:
                    if list(h)!=['coordinates']:
                        raise ValueError('Unexpected HDF5 schema')
                    arrays.append(h['coordinates'][:])
            gt,classes,audit = canonical_points(*arrays)
            audits.append({'image':name,'pixel_sha256':pixel_sha,'cells':len(gt),**audit})
            points = detect_centers(rgb,lock['detector']['config'])['points_xy']
            row = {'image':name,'gt_points':gt.tolist(),'gt_classes':classes.tolist(),'points':points.tolist(),'classes':{}}
            for arm,model in models.items():
                row['classes'][arm] = classify_centers(rgb,points,model).argmax(1).tolist()
            predictions.append(row)
            input_records.extend(meta for _,meta in fetched)
            if (i+1)%10==0:
                print(json.dumps({'external_images':i+1,'input_files':len(input_records)}),flush=True)
    # Private reproducible arithmetic inputs; no original image retention or public cell records.
    with (output/'private-predictions.json').open('x') as f:
        json.dump(predictions,f,separators=(',',':'),allow_nan=False)
    fresh_json(output/'input-manifest.json',input_records)
    fresh_json(output/'input-audit.json',{'images':audits,'exact_pixel_overlap_count':0,
        'patient_slide_overlap_checked':False,'raw_images_retained':False,
        'duplicate_annotation_records_removed':sum(a['duplicate_records_removed'] for a in audits)})
    arms = {}
    for arm in models:
        result = summarize([tumor_only_row(r,arm) for r in predictions],arm)
        # Images are not cases. Remove all pseudo-case metrics introduced only for aggregation.
        for key in list(result):
            if key.startswith('case_') or key=='per_case':
                del result[key]
        for r in result['per_image']:
            r.pop('case_id',None)
            r['two_class_macro_f1'] = float(np.mean([c['f1'] for c in r['classes'][:2]]))
            r['classes'] = r['classes'][:2]
            r.pop('macro_f1',None)
        result['two_class_macro_f1'] = float(np.mean([c['f1'] for c in result['classes'][:2]]))
        result['classes'] = result['classes'][:2]
        result.pop('macro_f1',None)
        arms[arm] = result
    final = {'schema':'auto-ki67-bcdata-transfer.v1','image_count':133,'gt_tumor_cells':sum(len(r['gt_classes']) for r in predictions),
             'scope':'External image-level BCData tumor-point benchmark, no patient-level independence, calibration or clinical claim',
             'inference_uses_gt_centers':False,'external_fitting':False,'arms':arms,
             'private_predictions_sha256':sha(output/'private-predictions.json'),
             'inference_lock_sha256':sha(output/'inference-lock.json')}
    fresh_json(output/'results.json',final)
    return final


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage',choices=['prepare','evaluate'])
    p.add_argument('--run',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--archive-manifest',type=Path)
    p.add_argument('--prior-audit',type=Path)
    a = p.parse_args()
    if a.stage=='prepare':
        if a.archive_manifest is None or a.prior_audit is None:
            p.error('prepare requires archive manifest and prior audit')
        prepare_external(a.run,a.archive_manifest,a.output,a.prior_audit)
    else:
        evaluate_external(a.run,a.output)
    print('DONE external '+a.stage,flush=True)


if __name__=='__main__':
    main()
