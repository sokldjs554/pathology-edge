#!/usr/bin/env python3
"""Lock validation-only classifiers, then evaluate eligible primary models."""
import argparse
from pathology_edge.ki67_normalized_pipeline import select_classifiers,evaluate


def main():
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=('select','internal','external'));parser.add_argument('--output',required=True);args=parser.parse_args()
    if args.stage=='select':select_classifiers(args.output)
    else:evaluate(args.output,external=args.stage=='external')


if __name__=='__main__':main()
