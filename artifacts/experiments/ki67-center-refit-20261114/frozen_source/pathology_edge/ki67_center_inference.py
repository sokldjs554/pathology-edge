"""Portable image-only inference from a hash-checked research bundle."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image
import torch
from .ki67_centers import CenterDetector,predict_centers
from .ki67_cnn import CellClassifier,classify_centers
from .ki67_evaluation import positive_fraction
from .ki67_experiment import read_json,fresh_json,sha,verify_hashes


def infer_rgb(rgb,detector,config,classifier):
    found=predict_centers(rgb,detector,config)
    probabilities=classify_centers(rgb,found['points_xy'],classifier)
    classes=probabilities.argmax(axis=1)
    return dict(points_xy=found['points_xy'],scores=found['scores'],probabilities=probabilities,
                classes=classes,positive_fraction=positive_fraction(classes))


def bundle_file(root,record):
    root=Path(root).resolve();relative=Path(record['file'])
    path=(root/relative).resolve()
    if relative.is_absolute() or '..' in relative.parts or not path.is_relative_to(root):
        raise ValueError('Bundle file must be inside bundle root')
    if sha(path)!=record['sha256']:raise ValueError('Bundle file hash mismatch: '+record['file'])
    return path


def load_bundle(path,seed,classifier):
    path=Path(path);bundle=read_json(path)
    if bundle.get('schema')!='learned-centers-inference.v1':raise ValueError('Unknown inference bundle')
    selected=[m for m in bundle['detectors'] if m['seed']==seed]
    if len(selected)!=1:raise ValueError('Unknown or duplicate detector seed')
    if classifier not in bundle['classifiers']:raise ValueError('Unknown classifier')
    expected=bundle['source_hashes']
    # Restrict source lookup to module basenames before checking provenance.
    if not expected or any(Path(n).name!=n or not n.endswith('.py') for n in expected):raise ValueError('Invalid source hash manifest')
    verify_hashes(Path(__file__).parent,expected)
    record=selected[0];detector=CenterDetector()
    detector.load_state_dict(torch.load(bundle_file(path.parent,record),map_location='cpu',weights_only=True),strict=True)
    c=bundle['classifiers'][classifier];file=bundle_file(path.parent,c)
    if c['kind']=='logistic':classification=read_json(file)
    elif c['kind']=='cnn':
        classification=CellClassifier();classification.load_state_dict(torch.load(file,map_location='cpu',weights_only=True),strict=True)
    else:raise ValueError('Unknown classifier kind')
    return detector.eval(),record['config'],classification


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bundle',type=Path,required=True);p.add_argument('--image',type=Path,required=True)
    p.add_argument('--detector-seed',type=int,default=20261117);p.add_argument('--classifier',default='cnn-20261113')
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise FileExistsError('Refusing to overwrite output')
    image=Image.open(a.image)
    if getattr(image,'n_frames',1)!=1 or min(image.size)<4 or max(image.size)>2048:
        raise ValueError('Expected single image patch, sides4..2048px; full WSI is not supported')
    rgb=np.asarray(image.convert('RGB'));torch.set_num_threads(2)
    detector,config,classifier=load_bundle(a.bundle,a.detector_seed,a.classifier)
    result=infer_rgb(rgb,detector,config,classifier)
    result={k:v.tolist() if isinstance(v,np.ndarray) else v for k,v in result.items()}
    result.update(image_sha256=sha(a.image),bundle_sha256=sha(a.bundle),detector_seed=a.detector_seed,
                  classifier=a.classifier,image_size_wh=list(image.size),scope='research image-patch inference',
                  ground_truth_supplied=False,clinical_validation=False,probability_calibration=False)
    fresh_json(a.output,result)
    print(json.dumps(dict(candidates=len(result['points_xy']),positive_fraction=result['positive_fraction'],
                          ground_truth_supplied=False,output=str(a.output))))


if __name__=='__main__':main()
