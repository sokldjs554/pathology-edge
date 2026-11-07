import argparse
import json
from .data import prepare


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('command',choices=['prepare','train','evaluate','export','eval-worker','infer'])
    parser.add_argument('--data',default='data')
    parser.add_argument('--output',default='artifacts')
    parser.add_argument('--archive')
    parser.add_argument('--dest',default='dist')
    parser.add_argument('--epochs',type=int,default=16)
    parser.add_argument('--steps',type=int,default=20)
    parser.add_argument('--seed',type=int,default=20261107)
    parser.add_argument('--mode',choices=['classical','no_overlap','overlap','full'])
    parser.add_argument('--image')
    parser.add_argument('--backend',choices=['python','cpp'],default='python')
    parser.add_argument('--threads',type=int,default=1)
    parser.add_argument('--prediction-dir',default='work/inference')
    args=parser.parse_args()
    if args.command=='prepare':
        result=prepare(args.data,args.archive)
        print(json.dumps({'images':len(result['records']),'manifest':args.data+'/manifest.json'}))
        return
    from .experiment import train,evaluate,evaluate_worker,export_demo
    if args.command=='train': train(args.data,args.output,args.seed,args.epochs,args.steps)
    elif args.command=='evaluate': evaluate(args.data,args.output)
    elif args.command=='eval-worker': evaluate_worker(args.data,args.output,args.mode)
    elif args.command=='export': export_demo(args.data,args.output,args.dest)
    elif args.command=='infer':
        from pathlib import Path
        import torch
        import numpy as np
        from PIL import Image
        from .data import load_image,sha256
        from .model import TinyUNet
        from .experiment import predict,dump
        if not args.image: parser.error('--image is required for infer')
        if args.mode not in {None,'no_overlap','overlap'}: parser.error('infer supports no_overlap or overlap')
        torch.set_num_threads(4)
        out=Path(args.output);dest=Path(args.prediction_dir)
        metadata=json.loads((out/'training.json').read_text())
        if sha256(out/'model.pt')!=metadata['model_sha256']: raise ValueError('Checkpoint hash mismatch')
        model=TinyUNet();model.load_state_dict(torch.load(out/'model.pt',weights_only=True))
        result=predict(model,load_image(args.image),args.mode or 'overlap',metadata['threshold'],args.backend,args.threads)
        dest.mkdir(parents=True,exist_ok=True)
        Image.fromarray((result.pop('mask')*255).astype(np.uint8)).save(dest/'mask.png')
        np.save(dest/'probability.npy',result.pop('probability'))
        result.update(model_sha256=metadata['model_sha256'],image_sha256=sha256(args.image),backend=args.backend,threads=args.threads)
        dump(dest/'result.json',result)
        print(json.dumps({'prediction_dir':str(dest),'objects':len(result['objects']),'seconds':result['seconds']}))


if __name__=='__main__': main()
