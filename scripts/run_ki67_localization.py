#!/usr/bin/env python3
"""Run fixed candidate-native localization stages."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from pathology_edge.ki67_localization_experiment import prepare,fit,evaluate

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('stage',choices=['prepare','fit','internal','external']);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--prior',type=Path)
    args=parser.parse_args()
    if args.stage=='prepare':
        if args.prior is None:parser.error('prepare requires --prior')
        prepare(args.prior,args.output)
    elif args.stage=='fit':fit(args.output)
    else:evaluate(args.output,external=args.stage=='external')
if __name__=='__main__':main()
