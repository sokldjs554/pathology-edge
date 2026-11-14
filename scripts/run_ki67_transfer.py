#!/usr/bin/env python3
import argparse
from pathology_edge.ki67_transfer_experiment import prepare,fit_worker,seal

if __name__=='__main__':
    p=argparse.ArgumentParser();s=p.add_subparsers(dest='command',required=True)
    a=s.add_parser('prepare');a.add_argument('--prior',required=True);a.add_argument('--weights',required=True);a.add_argument('--output',required=True)
    a=s.add_parser('fit');a.add_argument('--run',required=True);a.add_argument('--arm',choices=['pretrained','random'],required=True);a.add_argument('--seed',type=int,required=True)
    a=s.add_parser('seal');a.add_argument('--run',required=True)
    a=p.parse_args()
    if a.command=='prepare':prepare(a.prior,a.weights,a.output)
    elif a.command=='fit':fit_worker(a.run,a.arm,a.seed)
    else:seal(a.run)
