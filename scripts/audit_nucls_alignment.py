#!/usr/bin/env python3
"""Read-only audit of the NuCLS supplement and its immutable base; no inference.

Use --base for the extracted original evidence, --supplement for the extracted
supplement (containing evaluation/). Prints JSON; does not modify either input.
"""
import argparse
import csv
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import scipy
from PIL import Image
from scipy.ndimage import zoom

BASE_PROTOCOL = '0623d24445f886733f02fe81d17a808d330e6f23fe599c55a2f99c6e85b60b63'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def equal(actual, expected, label):
    if actual != expected:
        raise ValueError(label)


def read(path):
    return json.loads(Path(path).read_text())


def audit(base, supplement):
    out = supplement / 'evaluation'
    p, r = read(out / 'protocol.json'), read(out / 'results.json')
    equal(sha(base / 'evaluation/protocol.json'), BASE_PROTOCOL, 'base protocol')
    equal(p['base_protocol_sha256'], BASE_PROTOCOL, 'base reference')
    for filename, key in [('evaluation/results.json', 'base_results_sha256'),
                          ('original-acquisition.json', 'base_original_acquisition_sha256'),
                          ('annotation-acquisition.json', 'base_annotation_acquisition_sha256')]:
        equal(sha(base / filename), p[key], filename)
    equal(sha(out / 'protocol.json'), r['protocol_sha256'], 'protocol hash')
    equal(sha(out / 'runner.py'), p['runner_sha256'], 'runner hash')
    equal({x.name: sha(x) for x in (out / 'source/pathology_edge').glob('*.py')},
          p['source_sha256'], 'frozen sources')
    oldp = read(base / 'evaluation/protocol.json')
    oldr = read(base / 'evaluation/results.json')
    for name, digest in oldp['source_sha256'].items():
        equal(p['source_sha256'][name], digest, 'unchanged inference source')
    equal(p['models'], oldp['models'], 'fixed checkpoints')
    for architecture, digest in p['models'].items():
        equal(sha(base / 'evaluation/models' / (architecture + '.pt')), digest, 'model')
    equal(p['threshold'], .35, 'threshold')
    equal(p['mode'], 'no_overlap', 'mode')
    equal([p['patch_size'], p['boundary_radius']], [128, 8], 'seams')
    equal([p['image_count'], p['case_count']], [51, 5], 'membership counts')
    equal(read(out / 'status.json'), dict(completed=True, new_inference_runs=72, reused_predictions=30), 'completion')
    equal([r['new_inference_runs'], r['reused_predictions']], [72, 30], 'execution counts')
    equal(scipy.__version__, r['environment']['scipy'], 'pinned sampling convention')
    for key in ['training_run', 'clinical_validation', 'whole_wsi_validation']:
        equal(p[key], False, key)
        equal(r[key], False, key)
    equal(p['historical_exporter_reproduced'], False, 'historical caveat')
    equal(p['registration_optimized_using_predictions'], False, 'no prediction registration')
    raw = read(base / 'annotation-acquisition.json')
    equal(len(raw), 153, 'raw count')
    for a in raw:
        equal(sha(base / a['path']), a['sha256'], 'raw asset')
    acquisition = read(base / 'original-acquisition.json')
    links = {row['id']: row for case in acquisition['cases'] for row in case['rows']}
    for case in acquisition['cases']:
        equal(case['original_stream']['reference_md5_verified'], True, 'original verification')
        equal(case['original_stream']['md5'], case['source']['md5sum'], 'original md5')
    equal({x['id'] for x in p['images']}, set(links), 'all51 original membership')
    equal(len(p['images']), 51, 'no duplicate rows')
    support_path = base / 'evaluation/support.py'
    equal(sha(support_path), p['support_sha256'], 'frozen annotation support')
    equal(p['support_sha256'], oldp['support_sha256'], 'same policy')
    spec = importlib.util.spec_from_file_location('audited_support', support_path)
    support = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(support)
    oldrows = {x['id']: x for x in oldr['rows']}
    olditems = {x['id']: x for x in oldp['images']}
    export = read(supplement / 'aligned-mask-manifest.json')
    equal(export['protocol_sha256'], r['protocol_sha256'], 'export protocol')
    equal(len(export['rows']), 51, 'categorical export count')
    exported = {x['id']: x for x in export['rows']}
    metrics, metric_checks, identity_checks, transformed = {}, 0, 0, 0
    for item, row in zip(p['images'], r['rows'], strict=True):
        name, link = item['id'], links[item['id']]
        equal([row['id'], row['case_id'], row['key']], [name, link['case_id'], item['key']], 'row identity')
        equal(item['level0_bounds'], link['bounds_level0'], 'level0 extent')
        equal(sha(base / item['input']), link['original_sha256'], 'original image')
        equal(item['input_sha256'], link['original_sha256'], 'input hash')
        equal(sha(out / item['label']), item['label_sha256'], 'label hash')
        mask = np.asarray(Image.open(base / 'raw/mask' / (name + '.png')))
        size = Image.open(base / item['input']).size
        equal(size, Image.open(base / 'raw/rgb' / (name + '.png')).size, 'common RGB frame')
        grid = item['grid']
        equal(grid['source_wh'], [mask.shape[1], mask.shape[0]], 'source grid')
        equal(grid['target_wh'], list(size), 'target grid')
        if max(abs(a - b) for a, b in zip(grid['source_wh'], size)) > 1:
            raise ValueError('outside one-pixel scope')
        equal(grid['identity'], tuple(grid['source_wh']) == size, 'identity rule')
        equal(row['reused'], grid['identity'], 'reuse rule')
        ann_path = base / 'raw/csv' / (name + '.csv')
        annotations = list(csv.DictReader(ann_path.open()))
        original = support.annotation_support(mask, annotations)
        equal(original[3], item['source_coverage'], 'source support counts')
        factors = (size[1] / mask.shape[0], size[0] / mask.shape[1])
        # Independent full-array reference, not the production index sampler.
        sample = lambda a: zoom(a, factors + ((1,) if a.ndim == 3 else ()),
                               order=0, grid_mode=True, prefilter=False, mode='nearest')
        aligned = sample(mask)
        asset = exported[name]
        equal(sha(supplement / asset['path']), asset['sha256'], 'categorical export hash')
        equal(sha(base / asset['raw_path']), asset['raw_sha256'], 'export source hash')
        equal(np.array_equal(np.asarray(Image.open(supplement / asset['path'])), aligned),
              True, 'complete categorical export')
        with np.load(out / item['label'], allow_pickle=False) as z:
            target, valid, mask_support = z['target'], z['valid'], z['base_valid']
        for actual, source in zip((target, valid, mask_support), original[:3], strict=True):
            equal(np.array_equal(actual, sample(source)), True, 'label reconstruction')
        equal([int(valid.sum()), int((target & valid).sum())],
              [item['valid_pixels'], item['foreground_pixels']], 'aligned coverage')
        tuples = lambda a: set(map(tuple, np.unique(a.reshape(-1, 3), axis=0)))
        equal(tuples(aligned) <= tuples(mask), True, 'no invented tuples')
        nuclei = lambda a: set(map(tuple, np.unique(a[(a[..., 0] >= 1) & (a[..., 0] <= 12)], axis=0)))
        equal(nuclei(aligned), nuclei(mask), 'no nuclear ID lost')
        equal(bool(np.any(valid & np.isin(aligned[..., 0], [0, 99]))), False, 'ignored codes')
        equal(sha(out / item['display_annotations']), item['display_annotations_sha256'], 'display coordinates hash')
        display = read(out / item['display_annotations'])
        equal(display['source_csv_sha256'], sha(ann_path), 'CSV reference')
        for raw_row, display_row in zip(annotations, display['rows'], strict=True):
            pts = np.array([[float(v) for v in raw_row[k].split(',')] for k in ('coords_x', 'coords_y')]).T
            expected = (pts + .5) / np.asarray(grid['source_wh']) * np.asarray(size) - .5
            equal(display_row['coords_xy_centers'], expected.tolist(), 'display center mapping')
        if row['reused']:
            identity_checks += 1
            with np.load(base / 'evaluation' / olditems[name]['label'], allow_pickle=False) as z:
                for key, array in [('target', target), ('valid', valid), ('base_valid', mask_support)]:
                    equal(np.array_equal(array, z[key]), True, 'old15 labels bit-identical')
        else:
            transformed += 1
        yy, xx = np.indices(target.shape)
        seams = np.zeros(target.shape, bool)
        for axis, length in [(xx, target.shape[1]), (yy, target.shape[0])]:
            for cut in range(128, length, 128):
                seams |= (axis >= cut - 8) & (axis < cut + 8)
        metrics[name] = {}
        for arch, saved in row['models'].items():
            ref = saved['probability']
            equal(ref['root'], 'base' if row['reused'] else 'supplement', 'probability origin')
            path = (base if ref['root'] == 'base' else out) / ref['path']
            equal(sha(path), ref['sha256'], 'probability hash')
            if row['reused']:
                old = oldrows[name]['inputs']['original'][arch]
                equal(ref, dict(root='base', path='evaluation/' + old['probability'], sha256=old['sha256']), 'cached probability')
                equal(saved['metrics'], old['metrics'], 'old15 exact metrics')
            with np.load(path, allow_pickle=False) as z:
                probs = z['probability']
            equal(probs.shape, target.shape, 'probability shape')
            if not np.isfinite(probs).all() or (probs < 0).any() or (probs > 1).any():
                raise ValueError('probabilities invalid')
            metrics[name][arch] = {}
            for region, selection in [('all', valid), ('boundary', valid & seams),
                                      ('interior', valid & ~seams), ('mask_only_support', mask_support)]:
                truth, pred = target[selection], probs[selection] >= .35
                tp = int(np.count_nonzero(truth & pred))
                ngt, npred = int(truth.sum()), int(pred.sum())
                fp, fn = npred - tp, ngt - tp
                expected = dict(tp=tp, fp=fp, fn=fn, pixels=int(selection.sum()),
                                dice=2 * tp / (npred + ngt) if npred + ngt else 1.,
                                iou=tp / (tp + fp + fn) if tp + fp + fn else 1.,
                                precision=tp / npred if npred else 0., recall=tp / ngt if ngt else 0.)
                equal(saved['metrics'][region], expected, 'independent metric recount')
                metrics[name][arch][region] = expected['dice']
                metric_checks += 1
    equal([identity_checks, transformed], [15, 36], 'partition')
    mean_checks = 0
    for subset, groups in r['summary'].items():
        rows = [x for x in r['rows'] if subset == 'all51' or x['reused'] == (subset == 'previous15')]
        for region, s in groups.items():
            cases = sorted({x['case_id'] for x in rows})
            means = {a: float(np.mean([metrics[x['id']][a][region] for x in rows])) for a in p['models']}
            by_case = {c: {a: float(np.mean([metrics[x['id']][a][region] for x in rows if x['case_id'] == c])) for a in p['models']} for c in cases}
            equal(s['fov_macro'], means, 'FOV means')
            equal(s['case_means'], by_case, 'case means')
            equal(s['case_macro'], {a: float(np.mean([by_case[c][a] for c in cases])) for a in p['models']}, 'case macro')
            equal([s['fovs'], s['cases']], [len(rows), len(cases)], 'subset counts')
            equal(s['delta'], means['small_vit_refined'] - means['small_vit'], 'mean delta')
            deltas = [metrics[x['id']]['small_vit_refined'][region] - metrics[x['id']]['small_vit'][region] for x in rows]
            equal(s['wins_ties_losses'], [sum(d > 0 for d in deltas), sum(d == 0 for d in deltas), sum(d < 0 for d in deltas)], 'win counts')
            mean_checks += 4 + 2 * len(cases)
    return dict(all_checks_passed=True, evaluated_fovs=51, case_groups=5,
                normalized_fovs=transformed, old15_unchanged=identity_checks,
                raw_assets=153, original_crops=51, original_md5_matches=5,
                region_metric_checks=metric_checks, aggregate_mean_checks=mean_checks,
                display_coordinate_sets=51, label_tuple_checks=51, categorical_exports=51,
                model_loaded=False, inference_run=False,
                historical_exporter_reproduced=False,
                clinical_validation=False, whole_wsi_validation=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--supplement', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.base.resolve(), args.supplement.resolve()), indent=2))


if __name__ == '__main__':
    main()
