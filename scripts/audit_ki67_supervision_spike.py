#!/usr/bin/env python3
"""Replay fitting checkpoints on exact training pixels before choosing a loss."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from pathology_edge.ki67_experiment import read_json,fresh_json,sha,verify_data,load_sample
from pathology_edge.ki67_supervision import choose_loss
from pathology_edge.ki67_normalized_centers import NormalizedCenterDetector
from pathology_edge.ki67_normalized_experiment import checked
from pathology_edge.ki67_center_refit import tensor
from pathology_edge.ki67_centers import peak_candidates
from audit_ki67_union import independent_decode,_summary,compare_metrics


def verify_spike_protocol(p,mode,images,cases,source_sha):
    expected=dict(mode=mode,images=images,cases=cases,seed=20261117,steps=300,batch8=True,learning_rate=.001,threads=1,
                  augmentation='same paired rot90/flips RGB[.9,1.1]',source_sha256=source_sha)
    if any(p.get(k)!=v for k,v in expected.items()):raise ValueError('Fitting protocol/membership/source differs')


def audit_spike(root,normalized):
    root,normalized=Path(root).resolve(),Path(normalized).resolve();p=checked(normalized,selected=True)
    rows=[];cases={}
    manifest=Path(p['parent'])/'source-manifest.json'
    for r in read_json(manifest):
        if r['split']=='train' and cases.get(r['case_id'],0)<8:
            rows.append(r);cases[r['case_id']]=cases.get(r['case_id'],0)+1
    if len(rows)!=120 or len(cases)!=15:raise ValueError('Expected120 training images from15cases')
    verify_data(p['data_dir'],rows);images=[r['image'] for r in rows];samples=[];pixels=[]
    for r in rows:
        rgb,gt,gc=load_sample(p['data_dir'],r);pixels.append(rgb);samples.append(dict(image=r['image'],case_id=r['case_id'],gt_points=gt.tolist(),gt_classes=gc.tolist()))
    torch.set_num_threads(1);torch.manual_seed(20261117);initial=NormalizedCenterDetector(16)
    initial_hashes={k:hashlib.sha256(v.detach().numpy().tobytes()).hexdigest() for k,v in initial.state_dict().items()}
    reports={};hashes={str(manifest):sha(manifest),str(root/'loss_spike.py'):sha(root/'loss_spike.py')}
    replays=0;metric_checks=0
    for mode in ('focal','soft_mse','soft_bce'):
        dest=root/('spike-'+mode);protocol=read_json(dest/'protocol.json');report=read_json(dest/'result.json')
        verify_spike_protocol(protocol,mode,images,cases,sha(root/'loss_spike.py'))
        if read_json(dest/'initial-tensors.json')!=initial_hashes:raise ValueError('Initial models differ')
        if [h['step'] for h in report['history']]!=[100,200,300] or any(not np.isfinite(h['loss']) for h in report['history']):raise ValueError('Incomplete fitting budget')
        model=NormalizedCenterDetector(16);model.load_state_dict(torch.load(dest/'model.pt',map_location='cpu',weights_only=True),strict=True);model.eval();peaks=[]
        if not all(torch.isfinite(t).all() for t in model.state_dict().values()):raise ValueError('Nonfinite checkpoint')
        with torch.inference_mode():
            for rgb in pixels:
                heat=torch.sigmoid(model(tensor(rgb[None])))[0,0].numpy();peaks.append(peak_candidates(heat));replays+=1
        for trial in report['trials']:
            points=[independent_decode(xy,sc,trial['config'])[0] for xy,sc in peaks]
            compare_metrics(_summary(samples,points),trial);metric_checks+=1
        reports[mode]=report
        hashes.update({str(dest/n):sha(dest/n) for n in ('protocol.json','result.json','initial-tensors.json','model.pt')})
        print('REPLAYED',mode,flush=True)
    decision=choose_loss(reports)
    for path,digest in hashes.items():
        if sha(path)!=digest:raise ValueError('Diagnostic input changed during audit')
    result=dict(all_checks_passed=True,training_checkpoint_image_replays=replays,metric_checks=metric_checks,training_images=120,training_cases=15,
        heldout_inference_images=0,decision=decision,input_hashes=hashes,audit_sources={str(Path(__file__).resolve()):sha(__file__),str(Path(__file__).resolve().parents[1]/'src/pathology_edge/ki67_supervision.py'):sha(Path(__file__).resolve().parents[1]/'src/pathology_edge/ki67_supervision.py')},
        normalized_protocol_sha256=sha(normalized/'protocol.json'),scope='Training fit replay and hypothesis selection only')
    fresh_json(root/'spike-audit.json',result);fresh_json(root/'loss-decision.json',dict(**decision,audit_sha256=sha(root/'spike-audit.json')))
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',required=True,type=Path);parser.add_argument('--normalized',required=True,type=Path);args=parser.parse_args()
    result=audit_spike(args.root,args.normalized)
    print(json.dumps({k:v for k,v in result.items() if k not in ('decision','input_hashes','audit_sources')}))
    print('SELECTED LOSS',result['decision']['selected_loss'])
