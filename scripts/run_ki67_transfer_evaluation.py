#!/usr/bin/env python3
import argparse
from pathology_edge.ki67_transfer_evaluation import evaluate_existing,evaluate_deepliif,audit_external_inputs

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--stage',choices=['references','validation','test','bcdata','deepliif'],required=True);a=p.parse_args()
    if a.stage=='references':audit_external_inputs(a.run)
    elif a.stage=='deepliif':evaluate_deepliif(a.run)
    else:evaluate_existing(a.run,a.stage)
