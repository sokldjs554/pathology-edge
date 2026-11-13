"""Reproduce an unlabelled WSI experiment using fixed native level-0 ROIs.

OpenSlide is imported only by the optional export CLI. CI geometry and artifact
checks do not need the original slide or a native OpenSlide installation.
No general scale transform or learner exercise is implemented here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import statistics
import subprocess
import sys
from time import perf_counter

import numpy as np
from PIL import Image

from .data import sha256
from .merge import box_iou
from .patches import boundary_mask, grid

SOURCE_NAME = 'CMU-1-JP2K-33005.svs'
SOURCE_SHA256 = '9a1923cd9bcb260ba4d99d64f8d6e32550648c332ba48817f920662f3a513420'
SOURCE_URL = 'https://openslide.cs.cmu.edu/download/openslide-testdata/Aperio/' + SOURCE_NAME
FIXED_ROIS = [('R1', (5888, 20608)), ('R2', (29440, 9728)), ('R3', (15872, 26112))]
ROI_SIZE = 1024
METHODS = ('no_overlap', 'overlap')
CASE_SELECTION = ('64x64 windows centered on one internal 128px seam, with the other '
                  'center coordinate sampled every 16px; changed pixels >=16 and '
                  'boundary changes >0; rank boundary-changed descending, total changed '
                  'descending, then y/x ascending; at most one per ROI.')
TIMING_SCOPE = ('warm CPU predict(): patch RGB extraction + tissue gate + forward + '
                'probability stitch + components + NMS; excludes OpenSlide reading, '
                'model load, hashing, PNG/JSON writing and difference selection')
MEMORY_SCOPE = ('fresh process per ROI/method; absolute process high-water RSS including '
                'Python/runtime imports, OpenSlide open/read/cache, model load, one warmup '
                'and three timed predictions; sampled before result serialization')


def dump(path, obj, compact=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=None if compact else 2,
                               separators=(',', ':') if compact else None,
                               ensure_ascii=False, allow_nan=False) + '\n')


def pixel_sha(array):
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()


def patch_manifest(width, height, origin, mode):
    """Native crop translation only: no resize, pyramid scale, or affine API."""
    if mode not in METHODS:
        raise ValueError('Unsupported mode')
    ox, oy = origin
    return [dict(id=i, origin_local=[p.x, p.y], origin_level0=[ox+p.x, oy+p.y],
                 bbox_local=[p.x, p.y, p.x+p.valid_width, p.y+p.valid_height],
                 bbox_level0=[ox+p.x, oy+p.y, ox+p.x+p.valid_width, oy+p.y+p.valid_height],
                 valid_size=[p.valid_width, p.valid_height], size=p.size)
            for i, p in enumerate(grid(width, height, 128, 64 if mode == 'overlap' else 0))]


def suppression_trace(raw, suppressed):
    """Explain existing deduplicate output; never change its ranking or result."""
    trace = []
    for row in suppressed:
        i, j = row['suppressed_index'], row['kept_index']
        a, b = raw[i], raw[j]
        overlap = box_iou(a['bbox'], b['bbox'])
        distance = math.hypot(a['x']-b['x'], a['y']-b['y'])
        iou_trigger, distance_trigger = overlap >= .3, distance <= 8
        if a['patch_id'] == b['patch_id'] or not (iou_trigger or distance_trigger):
            raise ValueError('Invalid cross-patch suppression trace')
        trace.append(dict(suppressed_index=i, kept_index=j,
                          suppressed_raw_index=i, kept_raw_index=j,
                          suppressed_patch_id=a['patch_id'], kept_patch_id=b['patch_id'],
                          box_iou=overlap, center_distance=distance,
                          iou_threshold=.3, distance_threshold=8,
                          iou_trigger=iou_trigger, distance_trigger=distance_trigger,
                          touches_edge_priority=bool(a['touches_edge'] and not b['touches_edge']),
                          suppressed_touches_edge=bool(a['touches_edge']),
                          kept_touches_edge=bool(b['touches_edge']),
                          suppressed_score=a['score'], kept_score=b['score'],
                          priority_rule='complete component, then higher score, then lower raw index; first matching kept candidate'))
    return trace


def difference_rgba(a, b):
    if a.shape != b.shape or a.ndim != 2:
        raise ValueError('Equal 2D mask shapes required')
    a, b = a.astype(bool), b.astype(bool)
    rgba = np.zeros((*a.shape, 4), np.uint8)
    rgba[a & ~b] = [59, 130, 246, 180]
    rgba[b & ~a] = [249, 115, 22, 180]
    return rgba


def select_boundary_case(a, b, origin, roi_id):
    """A 64px window centered on an internal seam, chosen without GT."""
    if a.shape != b.shape or a.ndim != 2:
        raise ValueError('Equal 2D mask shapes required')
    a, b = a.astype(bool), b.astype(bool)
    changed = a ^ b
    seams = boundary_mask(a.shape, size=128, radius=8)
    choices = []
    height, width = a.shape
    # Store top-left coordinates. One center axis is on a real 128px seam;
    # the other moves by 16px. Deduplicate seam intersections before ranking.
    windows = {(cy-32, cx-32)
               for cx in range(128, width-31, 128)
               for cy in range(32, height-31, 16)}
    windows.update((cy-32, cx-32)
                   for cy in range(128, height-31, 128)
                   for cx in range(32, width-31, 16))
    for y, x in windows:
        part = np.s_[y:y+64, x:x+64]
        count = int(changed[part].sum())
        seam_count = int((changed[part] & seams[part]).sum())
        if count >= 16 and seam_count:
            choices.append((-seam_count, -count, y, x))
    if not choices:
        return []
    _, _, y, x = min(choices)
    part = np.s_[y:y+64, x:x+64]
    ox, oy = origin
    return [dict(id=f'{roi_id}-boundary-1', bbox_local=[x, y, x+64, y+64],
                 bbox_level0=[ox+x, oy+y, ox+x+64, oy+y+64],
                 center_level0=[ox+x+32, oy+y+32],
                 added_pixels=int((b[part] & ~a[part]).sum()),
                 removed_pixels=int((a[part] & ~b[part]).sum()),
                 changed_pixels=int(changed[part].sum()),
                 boundary_changed_pixels=int((changed[part] & seams[part]).sum()))]


def native_objects(objects, origin):
    ox, oy = origin
    return [dict(obj, raw_index=obj.get('raw_index', i),
                 bbox_level0=[obj['bbox'][0]+ox, obj['bbox'][1]+oy,
                              obj['bbox'][2]+ox, obj['bbox'][3]+oy],
                 center_level0=[obj['x']+ox, obj['y']+oy])
            for i, obj in enumerate(objects)]


def prepare(slide_path, model_path, training_path, dest, artifacts):
    """Validate originals, extract RGB ROIs, and freeze the protocol before inference."""
    import openslide
    if sha256(slide_path) != SOURCE_SHA256:
        raise ValueError('WSI source SHA-256 does not match the selected original')
    training = json.loads(training_path.read_text())
    model_hash = sha256(model_path)
    if model_hash != training['model_sha256'] or training['threshold'] != .5:
        raise ValueError('Frozen TinyUNet checkpoint or threshold changed')
    for path in (dest/'wsi', artifacts):
        path.mkdir(parents=True, exist_ok=True)
    with openslide.OpenSlide(slide_path) as slide:
        if slide.dimensions != (46000, 32893):
            raise ValueError('Source native dimensions differ from the pinned slide')
        props = slide.properties
        source = dict(id='cmu-1-jp2k-33005', name=SOURCE_NAME, width=slide.dimensions[0],
                      height=slide.dimensions[1], mpp_x=float(props['openslide.mpp-x']),
                      mpp_y=float(props['openslide.mpp-y']), objective_power=float(props['openslide.objective-power']),
                      source_url=SOURCE_URL, source_sha256=SOURCE_SHA256,
                      source_bytes=slide_path.stat().st_size, license='CC0-1.0',
                      license_url='https://creativecommons.org/publicdomain/zero/1.0/',
                      credit='OpenSlide freely distributable test data / Carnegie Mellon University',
                      rights_source='https://openslide.cs.cmu.edu/download/openslide-testdata/index.json',
                      description='Brightfield; JPEG 2000 export of CMU-1.svs. Source does not document tissue/stain identity.',
                      thumbnail='wsi/overview.jpg', native_levels=[list(v) for v in slide.level_dimensions],
                      reader=dict(openslide=openslide.__library_version__, openslide_python=openslide.__version__,
                                  vendor=props.get('openslide.vendor')),
                      tile_source={'Image': {'xmlns': 'http://schemas.microsoft.com/deepzoom/2008',
                          'Url': 'https://openslide-demo-site.s3.dualstack.us-east-2.amazonaws.com/aperio/cmu-1-jp2k-33005/slide_files/',
                          'Format': 'jpeg', 'TileSize': 510, 'Overlap': 1,
                          'Size': {'Width': 46000, 'Height': 32893}}})
        slide.get_thumbnail((1200, 1200)).convert('RGB').save(dest/source['thumbnail'], quality=90)
        source['thumbnail_sha256'] = sha256(dest/source['thumbnail'])
        rois = []
        for roi_id, origin in FIXED_ROIS:
            started = perf_counter()
            rgb = np.asarray(slide.read_region(origin, 0, (ROI_SIZE, ROI_SIZE)).convert('RGB')).copy()
            elapsed = perf_counter()-started
            image_rel = f'wsi/{roi_id}.png'
            Image.fromarray(rgb).save(dest/image_rel)
            thumbnail_rel = f'wsi/{roi_id}-thumb.jpg'
            thumbnail = Image.fromarray(rgb)
            thumbnail.thumbnail((160, 160))
            thumbnail.save(dest/thumbnail_rel, quality=85)
            rois.append(dict(id=roi_id, name=f'Native ROI {roi_id}', origin=list(origin),
                             width=ROI_SIZE, height=ROI_SIZE, image=image_rel, thumbnail=thumbnail_rel,
                             thumbnail_sha256=sha256(dest/thumbnail_rel),
                             image_sha256=sha256(dest/image_rel), image_pixel_sha256=pixel_sha(rgb),
                             preparation_read_seconds=elapsed))
    protocol = dict(schema_version=1, source_sha256=SOURCE_SHA256, model_sha256=model_hash,
                    threshold=training['threshold'], seed=training['config']['seed'],
                    roi_selection='Three tissue locations fixed from overview before inference; no outcome-based ROI selection.',
                    roi_geometry=[{k: roi[k] for k in ('id', 'origin', 'width', 'height', 'image_pixel_sha256')} for roi in rois],
                    preprocessing='Native level 0 RGB, uint8 / 255 in existing predict(); no resize or stain normalization.',
                    patch_size=128, overlap=64, seam_radius=8, seam_reference='Internal no_overlap ROI grid',
                    merge_iou=.3, merge_distance=8, min_component_area=12,
                    background_gate='existing tissue_mask: >= 1% per extracted patch',
                    methods=list(METHODS), warmup_runs=1, timed_repeats=3,
                    torch_threads=4, opencv_threads=1, backend='python', device='cpu',
                    ground_truth=False, timing_scope=TIMING_SCOPE, memory_scope=MEMORY_SCOPE,
                    case_selection=CASE_SELECTION, case_selection_revision=2,
                    colors={'removed_a_only': [59, 130, 246, 180], 'added_b_only': [249, 115, 22, 180]},
                    training_reference='artifacts/training.json', coordinate_unit='native WSI level-0 pixels')
    dump(artifacts/'source.json', source)
    dump(artifacts/'protocol.json', protocol)
    dump(artifacts/'rois.json', rois)
    return source, protocol, rois


def run_worker(args):
    import cv2
    import openslide
    import torch
    from .experiment import environment, predict
    from .model import TinyUNet
    torch.set_num_threads(4)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    cv2.setNumThreads(1)
    protocol = json.loads((args.artifacts/'protocol.json').read_text())
    roi = next(r for r in json.loads((args.artifacts/'rois.json').read_text()) if r['id'] == args.roi)
    if sha256(args.model) != protocol['model_sha256']:
        raise ValueError('Frozen model changed before worker launch')
    started = perf_counter()
    slide = openslide.OpenSlide(args.slide)
    open_seconds = perf_counter()-started
    started = perf_counter()
    image = np.asarray(slide.read_region(tuple(roi['origin']), 0, (roi['width'], roi['height'])).convert('RGB')).copy()
    read_seconds = perf_counter()-started
    slide.close()
    if pixel_sha(image) != roi['image_pixel_sha256']:
        raise ValueError('Read ROI pixels differ from the prepared crop')
    started = perf_counter()
    model = TinyUNet()
    model.load_state_dict(torch.load(args.model, map_location='cpu', weights_only=True))
    model_load_seconds = perf_counter()-started
    warmup = predict(model, image, args.mode, protocol['threshold'])
    warmup_seconds = warmup['seconds']
    del warmup
    timings, fingerprints = [], []
    for _ in range(protocol['timed_repeats']):
        result = predict(model, image, args.mode, protocol['threshold'])
        timings.append(result['seconds'])
        fingerprints.append(pixel_sha(result['probability']))
    if len(set(fingerprints)) != 1:
        raise ValueError('Repeated inference output is not deterministic')
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform == 'darwin':
        rss /= 1024
    mask_rel = f'wsi/{roi["id"]}-{args.mode}-mask.png'
    overlay_rel = f'wsi/{roi["id"]}-{args.mode}.png'
    Image.fromarray(result['mask'].astype(np.uint8)*255).save(args.output_dist/mask_rel)
    rgba = np.zeros((*result['mask'].shape, 4), np.uint8)
    rgba[result['mask']] = [66, 224, 184, 110]
    Image.fromarray(rgba).save(args.output_dist/overlay_rel)
    report = dict(mode=args.mode, overlay=overlay_rel, mask=mask_rel,
                  overlay_sha256=sha256(args.output_dist/overlay_rel), mask_sha256=sha256(args.output_dist/mask_rel),
                  image_pixel_sha256=pixel_sha(image), probability_sha256=fingerprints[-1],
                  repeat_probability_sha256=fingerprints,
                  raw=native_objects(result['raw'], roi['origin']),
                  objects=native_objects(result['objects'], roi['origin']),
                  suppressed=suppression_trace(result['raw'], result['suppressed']),
                  patches=patch_manifest(roi['width'], roi['height'], roi['origin'], args.mode),
                  median_seconds=float(statistics.median(timings)), timings_seconds=timings,
                  warmup_seconds=warmup_seconds, read_seconds=read_seconds,
                  slide_open_seconds=open_seconds, model_load_seconds=model_load_seconds,
                  peak_process_rss_mib=rss/1024, worker_pid=os.getpid(),
                  torch_threads=torch.get_num_threads(), opencv_threads=cv2.getNumThreads(),
                  environment=environment(), raw_count=len(result['raw']), merged_count=len(result['objects']),
                  suppressed_count=len(result['suppressed']), patch_count=result['patch_count'],
                  skipped_background=result['skipped_background'], foreground_pixels=int(result['mask'].sum()),
                  timing_scope=TIMING_SCOPE, memory_scope=MEMORY_SCOPE,
                  read_scope='Fresh OpenSlide handle native level-0 read_region + RGB conversion + ndarray copy; OS file cache uncontrolled.')
    dump(args.artifacts/f'{roi["id"]}_{args.mode}.json', report)
    print(json.dumps({k: report[k] for k in ('mode', 'median_seconds', 'peak_process_rss_mib', 'raw_count', 'merged_count', 'suppressed_count')}), flush=True)


def export(args):
    source, protocol, rois = prepare(args.slide, args.model, args.training, args.output_dist, args.artifacts)
    if args.prepare_only:
        print(json.dumps({'prepared': [r['image'] for r in rois], 'inference_run': False}), flush=True)
        return
    for roi in rois:
        roi['methods'] = {}
        for mode in METHODS:
            command = [sys.executable, '-m', 'pathology_edge.wsi_export', '--worker',
                       '--slide', str(args.slide), '--model', str(args.model),
                       '--training', str(args.training), '--output-dist', str(args.output_dist),
                       '--artifacts', str(args.artifacts), '--roi', roi['id'], '--mode', mode]
            print(f'{roi["id"]}: fresh worker for {mode}', flush=True)
            subprocess.run(command, check=True)
            roi['methods'][mode] = json.loads((args.artifacts/f'{roi["id"]}_{mode}.json').read_text())
        a, b = [np.asarray(Image.open(args.output_dist/roi['methods'][m]['mask'])) > 0 for m in METHODS]
        path = f'wsi/{roi["id"]}-difference.png'
        Image.fromarray(difference_rgba(a, b)).save(args.output_dist/path)
        seams = boundary_mask(a.shape, 128, 8)
        roi['difference'] = dict(overlay=path, overlay_sha256=sha256(args.output_dist/path),
                                 added_pixels=int((b & ~a).sum()), removed_pixels=int((a & ~b).sum()),
                                 changed_pixels=int((a ^ b).sum()), boundary_changed_pixels=int(((a ^ b) & seams).sum()),
                                 boundary_pixels=int(seams.sum()), seam_radius=8, seam_patch_size=128,
                                 cases=select_boundary_case(a, b, roi['origin'], roi['id']))
    analyzed = sum(r['width']*r['height'] for r in rois)
    provenance = dict(source_manifest='artifacts/wsi/source.json', protocol_manifest='artifacts/wsi/protocol.json',
                      pipeline='src/pathology_edge/wsi_export.py', pipeline_sha256=sha256(Path(__file__)),
                      public_manifest='wsi/provenance.json',
                      coordinate_note='Native level-0 ROI translation only; no image resize or general coordinate transform.',
                      remote_tiles='Pinned source path and dimensions from official OpenSlide demo; JPEG display re-encoding; external service availability not guaranteed.',
                      source_identity='Analysis and remote DZI both reference the CMU-1-JP2K-33005 variant.',
                      ground_truth_note='No nuclear ground truth is supplied with this slide; disagreement is not accuracy or improvement.')
    payload = dict(schema_version=1, slide=source,
                   model=dict(name='TinyUNet (fixed original checkpoint)', sha256=protocol['model_sha256'],
                              threshold=protocol['threshold'], trained_on='TNBC v1.1 H&E PNG patches; original from-scratch CPU training; no WSI fine-tuning'),
                   analysis=dict(scope='Three preselected native 1024x1024 ROIs only; the rest of this WSI is not analyzed.',
                                 ground_truth=False, roi_count=len(rois), total_pixels=analyzed,
                                 slide_fraction=analyzed/(source['width']*source['height'])),
                   rois=rois, provenance=provenance,
                   limits=['No nuclear ground truth, Dice, PQ or clinical accuracy for this WSI.',
                           'H&E-trained TNBC model applied exploratorily; source does not document tissue/stain identity.',
                           'NMS may merge nearby distinct nuclei or retain fragments; counts are model component candidates.',
                           'Segmentation overlays are stitched probability masks; NMS candidates are a separate object branch.',
                           'Timings cover these warm CPU ROIs only, not whole-slide inference or download time.',
                           'Read latency is not cold-storage latency; OS caches and shared-host load are uncontrolled.',
                           'Official external DZI tiles may become unavailable; local ROI images remain available.'])
    dump(args.output_dist/'wsi.json', payload, compact=True)
    dump(args.artifacts/'experiment.json', payload)
    dump(args.output_dist/'wsi/provenance.json', dict(slide=source, protocol=protocol, provenance=provenance,
                                                    roi_images=[{k: r[k] for k in ('id','origin','image','image_sha256','image_pixel_sha256')} for r in rois]))
    print(json.dumps({'exported': str(args.output_dist/'wsi.json'), 'roi_count': len(rois), 'ground_truth': False}), flush=True)


def refresh_cases(dest, artifacts):
    """Update postprocessing from hash-verified saved masks, without inference."""
    payload = json.loads((dest/'wsi.json').read_text())
    protocol = json.loads((artifacts/'protocol.json').read_text())
    public_manifest = json.loads((dest/'wsi/provenance.json').read_text())
    for roi in payload['rois']:
        masks = []
        for mode in METHODS:
            method = roi['methods'][mode]
            path = dest/method['mask']
            if sha256(path) != method['mask_sha256']:
                raise ValueError(f'{roi["id"]} {mode}: saved mask SHA-256 changed')
            masks.append(np.asarray(Image.open(path)) > 0)
        if masks[0].shape != (roi['height'], roi['width']):
            raise ValueError('Saved mask dimensions differ from the ROI')
        roi['difference']['cases'] = select_boundary_case(*masks, roi['origin'], roi['id'])
    protocol.update(case_selection=CASE_SELECTION, case_selection_revision=2)
    provenance = payload['provenance']
    provenance.setdefault('inference_pipeline_sha256', provenance['pipeline_sha256'])
    provenance['pipeline_sha256'] = sha256(Path(__file__))
    provenance['case_selection_pipeline_sha256'] = provenance['pipeline_sha256']
    provenance['case_refresh_scope'] = 'Saved prediction masks only; no inference rerun; original timing and candidates retained.'
    public_manifest.update(protocol=protocol, provenance=provenance)
    dump(dest/'wsi.json', payload, compact=True)
    dump(artifacts/'experiment.json', payload)
    dump(artifacts/'protocol.json', protocol)
    dump(dest/'wsi/provenance.json', public_manifest)
    print(json.dumps({'refreshed_cases': len(payload['rois']), 'inference_run': False,
                      'public_json_bytes': (dest/'wsi.json').stat().st_size}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--slide', type=Path)
    parser.add_argument('--model', type=Path, default=Path('artifacts/model.pt'))
    parser.add_argument('--training', type=Path, default=Path('artifacts/training.json'))
    parser.add_argument('--output-dist', type=Path, default=Path('dist'))
    parser.add_argument('--artifacts', type=Path, default=Path('artifacts/wsi'))
    parser.add_argument('--prepare-only', action='store_true', help='Extract RGB for pre-inference inspection only')
    parser.add_argument('--refresh-cases', action='store_true', help='Update cases from saved masks only; no slide or inference needed')
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--roi', choices=[r[0] for r in FIXED_ROIS], help=argparse.SUPPRESS)
    parser.add_argument('--mode', choices=METHODS, help=argparse.SUPPRESS)
    args = parser.parse_args()
    for name in ('slide', 'model', 'training', 'output_dist', 'artifacts'):
        if getattr(args, name) is not None:
            setattr(args, name, getattr(args, name).resolve())
    if args.refresh_cases:
        if args.worker or args.prepare_only:
            parser.error('--refresh-cases cannot be combined with inference or preparation')
        refresh_cases(args.output_dist, args.artifacts)
    elif args.slide is None:
        parser.error('--slide is required for preparation or inference')
    elif args.worker:
        if not args.roi or not args.mode:
            parser.error('--worker requires --roi and --mode')
        run_worker(args)
    else:
        export(args)


if __name__ == '__main__':
    main()
