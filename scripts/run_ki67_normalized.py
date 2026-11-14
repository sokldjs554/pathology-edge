#!/usr/bin/env python3
from pathlib import Path
import argparse,json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from pathology_edge.ki67_normalized_experiment import prepare,fit_worker,seal
p=argparse.ArgumentParser(description='Fixed normalized detector workers; not clinical Ki67')
p.add_argument('stage',choices=['prepare','worker','seal']);p.add_argument('--output',type=Path,required=True);p.add_argument('--prior',type=Path);p.add_argument('--width',type=int,choices=[4,16]);p.add_argument('--seed',type=int)
a=p.parse_args()
if a.stage=='prepare':
 if a.prior is None:p.error('prepare needs --prior')
 result=prepare(a.prior,a.output)
elif a.stage=='worker':
 if a.width is None or a.seed is None:p.error('worker needs --width and --seed')
 result=fit_worker(a.output,a.width,a.seed)
else:result=seal(a.output)
print('DONE '+a.stage,flush=True)
