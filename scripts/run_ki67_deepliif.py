#!/usr/bin/env python3
"""Prospective paired external evaluation after all detector/classifier locks."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import time
import urllib.error
import sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from audit_ki67_deepliif import verify_reference_mask
from pathology_edge.ki67_deepliif import fetch_zip_entry,decode_paired_png,validate_membership,score_rows,paired_fraction
from pathology_edge.ki67_normalized_pipeline import checked_pipeline,selected_networks,predict_pair,classified_row,ARMS
from pathology_edge.ki67_center_experiment import loaded_detectors
from pathology_edge.ki67_experiment import read_json,fresh_json,sha,verify_hashes,load_models
from pathology_edge.ki67_union_experiment import utc,write_rows


def evaluate_new(root,index_path,protocol_path,output):
    root,index_path,protocol_path,output=map(Path,(root,index_path,protocol_path,output));p,models,choices=checked_pipeline(root)
    eligible=[m for m in models if m['selected'] is not None]
    output.mkdir(parents=True,exist_ok=False)
    if not eligible:
        fresh_json(output/'not-run.json',dict(reason='No eligible primary normalized detector; prospective external data not scored',new_inference_images=0,stability_denominator=3))
        return
    ep=read_json(protocol_path);index=read_json(index_path)
    if sha(protocol_path)!=protocol_path.with_suffix('.sha256').read_text().strip() or sha(index_path)!=ep['index_sha256']:raise ValueError('Prospective protocol/index hash differs')
    names=validate_membership(ep,index);entries={e['name']:e for e in index['entries']}
    if index['url']!=ep['source_url'] or index['bytes']!=ep['archive_bytes'] or ep['radii_native_px']!=[6,12] or ep['primary_radius']!=6:raise ValueError('External source/scoring protocol differs')
    external=Path(p['external']);man=Path(p['parent'])/'source-manifest.json'
    extra=[man,external/'input-audit.json',external/'prior-test-pixel-hashes.json',index_path,protocol_path]
    lock=dict(created_utc=utc(),detector_lock_sha256=sha(root/'selection-lock.json'),classifier_lock_sha256=sha(root/'classifier-lock.json'),input_hashes={str(f.resolve()):sha(f) for f in extra},
        source_hashes={str(Path(__file__).resolve()):sha(__file__),str(Path(__import__('pathology_edge.ki67_deepliif',fromlist=['x']).__file__).resolve()):sha(__import__('pathology_edge.ki67_deepliif',fromlist=['x']).__file__)},
        dataset_scope=ep['scope'],lock_phase='Before inference',full_archive_checksum_verified=False)
    lock['source_hashes'][str(Path(__file__).with_name('audit_ki67_deepliif.py').resolve())]=sha(Path(__file__).with_name('audit_ki67_deepliif.py'))
    fresh_json(output/'evaluation-lock.json',lock)
    forbidden={r['pixel_sha256'] for r in read_json(man)}|set(read_json(external/'prior-test-pixel-hashes.json'))|{r['pixel_sha256'] for r in read_json(external/'input-audit.json')['images']}
    networks=selected_networks(root,models);original=loaded_detectors(p['prior']);classifiers=load_models(p['parent'],read_json(Path(p['parent'])/'selection-lock.json'))
    if tuple(classifiers)!=ARMS:raise ValueError('Four frozen classifiers required')
    outputs={m['seed']:{arm:[] for arm in ('A','B')} for m in eligible};observed=set();audits=[]
    def download(name):
        for attempt in range(4):
            try:return fetch_zip_entry(ep['source_url'],entries[name],ep['archive_bytes'])
            except (TimeoutError,urllib.error.URLError):
                if attempt==3:raise
                time.sleep(2**attempt)
    # Bounded prefetch avoids storing the full1GB ZIP or hundreds of decoded images.
    with ThreadPoolExecutor(max_workers=4) as pool:
        pending={i:pool.submit(download,n) for i,n in enumerate(names[:8])}
        for i,name in enumerate(names):
            raw,meta=pending.pop(i).result()
            if i+8<len(names):pending[i+8]=pool.submit(download,names[i+8])
            rgb,gt,gc,reference=decode_paired_png(raw);pixel=hashlib.sha256(rgb.tobytes()).hexdigest()
            from PIL import Image
            import io
            mask=np.asarray(Image.open(io.BytesIO(raw)))[:,2560:3072];verify_reference_mask(mask,gt,gc)
            if pixel in forbidden or pixel in observed:raise ValueError('Exact decoded image overlap; stop without selective exclusion')
            observed.add(pixel);audits.append(dict(image=name,pixel_sha256=pixel,gt_points=gt.tolist(),gt_classes=gc.tolist(),reference=reference,source=meta,independent_reference_checked=True))
            with (output/'stream-progress.jsonl').open('a') as progress:progress.write(json.dumps(dict(image=name,verified_index=i+1,source_sha256=meta['sha256'],reference_cells=len(gt)))+'\n')
            for m in eligible:
                for arm,xy in predict_pair(rgb,m['seed'],m['selected'],original,networks).items():
                    outputs[m['seed']][arm].append(classified_row(rgb,xy,gt,gc,classifiers,name))
            # Six prespecified ordinal examples for review, not metric-based selection.
            if i in (0,100,200,300,400,596):
                from PIL import Image
                (output/'examples').mkdir(exist_ok=True);Image.fromarray(rgb).save(output/'examples'/f'{i:03d}.png')
            if (i+1)%25==0:print('DEEPLIIF',i+1,'/',len(names),flush=True)
    write_rows(output/'input-audit.json.gz',audits);comparisons={}
    for seed,arms in outputs.items():
        folder=output/f'seed-{seed}';folder.mkdir();scores={}
        for arm,rows in arms.items():
            write_rows(folder/(arm+'.json.gz'),rows);scores[arm]={str(radius):{name:score_rows(rows,name,radius) for name in ARMS} for radius in (6,12)}
        write_rows(folder/'scores.json.gz',[scores]);c=choices[seed];paired={}
        for radius in ('6','12'):
            a=scores['A'][radius][c['reference_classifier']];b=scores['B'][radius][c['selected_classifier']]
            fractions=paired_fraction(a['per_image'],b['per_image']);criteria=dict(detection_f1_increase=b['localization']['f1']>a['localization']['f1'],two_class_f1_increase=b['two_class_macro_f1']>a['two_class_macro_f1'],same_population_fraction_mae_nonincrease=fractions['passed'])
            paired[radius]=dict(A_classifier=c['reference_classifier'],B_classifier=c['selected_classifier'],A={k:v for k,v in a.items() if k!='per_image'},B={k:v for k,v in b.items() if k!='per_image'},fractions=fractions,criteria=criteria,passed=all(criteria.values()))
        fresh_json(folder/'comparison.json',paired);comparisons[seed]=paired
    checked_pipeline(root);verify_hashes('/',lock['input_hashes']);verify_hashes('/',lock['source_hashes'])
    outcomes=[dict(seed=m['seed'],eligible=m['selected'] is not None,passed=bool(comparisons.get(m['seed'],{}).get('6',{}).get('passed',False))) for m in models]
    fresh_json(output/'summary.json',dict(all_checks_passed=True,images=len(names),models=len(eligible),denominator=3,passes=sum(r['passed'] for r in outcomes),seeds=outcomes,primary_radius=6,secondary_radius=12,
        all_three_passed=all(r['passed'] for r in outcomes),exact_pixel_overlap_count=0,clinical_validation=False,whole_wsi_validation=False,scope=ep['scope'],
        limitation='Derived segmentation centroids; no patient/slide independence or calibrated MPP guarantee; no tumor-specific labels; native-pixel radius differs in physical size across sources',
        evidence_hashes={str(f.relative_to(output)):sha(f) for f in output.rglob('*') if f.is_file()}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--index',required=True);p.add_argument('--protocol',required=True);p.add_argument('--output',required=True);a=p.parse_args();evaluate_new(a.run,a.index,a.protocol,a.output)
