#!/usr/bin/env python3
"""Run fixed detector refitting; no user code or published model overwrite."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from pathology_edge.ki67_center_refit import prepare,fit,evaluate

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('stage',choices=['prepare','fit','internal','external']);p.add_argument('--output',type=Path,required=True);p.add_argument('--prior',type=Path);a=p.parse_args()
    if a.stage=='prepare':
        if a.prior is None:p.error('prepare requires --prior')
        prepare(a.prior,a.output)
    elif a.stage=='fit':fit(a.output)
    else:evaluate(a.output,external=a.stage=='external')
