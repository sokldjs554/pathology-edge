"""Post-hoc illustration of saved boundary errors; never trains or runs inference."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

from .metrics import binary_metrics
from .patches import boundary_mask


def runs(mask):
    """Lossless horizontal runs [local_y, local_x, length] of true pixels."""
    result = []
    for y, row in enumerate(mask):
        edges = np.flatnonzero(np.diff(np.pad(row.astype(np.int8), (1, 1))))
        result.extend([y, int(x), int(end-x)] for x, end in zip(edges[::2], edges[1::2]))
    return result


def describe_region(a, b, target, band, bbox):
    x0, y0, x1, y1 = bbox
    sl = np.s_[y0:y1, x0:x1]
    a, b, t, region = a[sl], b[sl], target[sl], band[sl]
    corrected = (a != t) & (b == t) & region
    regressed = (a == t) & (b != t) & region
    good, bad = int(corrected.sum()), int(regressed.sum())
    return dict(bbox=list(bbox), center=[(x0+x1)//2, (y0+y1)//2],
                corrected=good, regressed=bad, net_corrected=good-bad, changed=good+bad,
                target_pixels=int((t & region).sum()),
                before=binary_metrics(a, t, region), after=binary_metrics(b, t, region),
                corrected_runs=runs(corrected), regressed_runs=runs(regressed))


def export_cases(dist):
    dist = Path(dist)
    source = json.loads((dist / 'results.json').read_text())
    hashes = {}
    def digest(path):
        hashes[path] = hashlib.sha256((dist / path).read_bytes()).hexdigest()
    digest('results.json')
    cases = []
    # 32px external margin around a 64px square: center range [64, 448].
    centers = sorted({(x, y) for seam in (128, 256, 384) for v in range(64, 449, 16)
                      for x, y in ((seam, v), (v, seam))}, key=lambda p: (p[1], p[0]))
    for sample in source['samples']:
        paths = [sample['methods'][m]['overlay'] for m in ('no_overlap', 'overlap')]
        for path in paths + [sample['gt']]:
            digest(path)
        a, b = [np.asarray(Image.open(dist / p))[..., 3] > 0 for p in paths]
        target = np.asarray(Image.open(dist / sample['gt'])) > 127
        band = boundary_mask(target.shape, size=128, radius=8)
        candidates = [describe_region(a, b, target, band, (x-32, y-32, x+32, y+32))
                      for x, y in centers]
        for direction, sign in [('improved', 1), ('worsened', -1)]:
            eligible = [r for r in candidates if r['target_pixels'] >= 32 and r['changed'] >= 16
                        and sign*r['net_corrected'] >= 16
                        and sign*(r['after']['dice']-r['before']['dice']) > 0]
            if not eligible:
                continue  # A missing direction is not manufactured.
            best = min(eligible, key=lambda r: (-sign*r['net_corrected'], -r['changed'],
                                               r['center'][1], r['center'][0]))
            cases.append(dict(id=f"{sample['id']}-{direction}", sample_id=sample['id'],
                              direction=direction, **best))
    samples = {s['id']: s for s in source['samples']}
    recommended = {}
    for direction, sign in [('improved', 1), ('worsened', -1)]:
        eligible = []
        for case in cases:
            s = samples[case['sample_id']]['methods']
            if case['direction'] == direction and all(
                sign*(s['overlap']['metrics'][scope]['dice']-s['no_overlap']['metrics'][scope]['dice']) > 0
                for scope in ('all', 'boundary')):
                eligible.append(case)
        if eligible:
            recommended[direction] = min(eligible, key=lambda r: (-sign*r['net_corrected'],
                -r['changed'], r['sample_id'], r['center'][1], r['center'][0]))['id']
    return dict(schema_version=1, model_sha256=source['model_sha256'], source_sha256=hashes,
                protocol=dict(roi_size=64, seam_positions=[128, 256, 384], radius=8,
                              center_step=16, center_min=64, center_max=448,
                              min_target_pixels=32, min_changed_pixels=16, min_net_corrected=16,
                              scope='ROI intersect fixed baseline boundary band; half-open PNG coordinates',
                              selection='Best signed net corrected pixels per image/direction; local Dice sign must agree. '
                                        'Ties: changed pixels descending, y then x ascending. Recommended examples also '
                                        'agree with whole-image and whole-boundary Dice direction.',
                              limitation='Post-hoc illustrations selected with test ground truth, not representative '
                                         'performance estimates, causal proof, or model selection.'),
                recommended=recommended, cases=cases)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dist', type=Path, default=Path('dist'))
    args = parser.parse_args()
    data = export_cases(args.dist)
    (args.dist / 'cases.json').write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')) + '\n')
    print(json.dumps({'cases': len(data['cases']), 'recommended': data['recommended']}))


if __name__ == '__main__':
    main()
