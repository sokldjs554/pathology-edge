#!/usr/bin/env python3
"""Run the frozen seed-20261116 ViT/local-head comparison after learner preflight.

Both models train from scratch in a fresh directory. The user-owned head must
pass preflight before baseline training can start. Saved-result audits are read-only.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import uuid

_spec = importlib.util.spec_from_file_location('trusted_refinement_pair',
                                            Path(__file__).with_name('run_model_comparison.py'))
pair = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pair)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path.cwd())
    parser.add_argument('--data', type=Path, default=Path('data'))
    parser.add_argument('--output', type=Path)
    parser.add_argument('--summarize', type=Path, help='Read-only audit of a completed refinement comparison')
    parser.add_argument('--data-override', type=Path, help='Relocated data for a saved-output audit')
    args = parser.parse_args()
    if args.summarize:
        summary = pair.summarize(args.summarize, data_override=args.data_override)
        pair.require(summary.get('comparison') == 'refinement', 'Expected a refinement comparison')
        print(json.dumps(summary, ensure_ascii=False))
    else:
        output = args.output or args.repo/'work'/f'my-vit-refinement.{uuid.uuid4().hex[:12]}'
        pair.run(args.repo, args.data, output, comparison='refinement', seed=20261116)


if __name__ == '__main__':
    main()
