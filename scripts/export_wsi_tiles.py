#!/usr/bin/env python3
"""Generate every native-resolution Deep Zoom level from the pinned CC0 WSI.

Run after pathology_edge.wsi_export. This standalone CPU-only build step does
not run a model, alter ROI PNGs, or change inference/protocol measurements.
Image rights: CC0-1.0, per the original OpenSlide test-data index. OpenSlide's
LGPL-2.1 software license is separate from the image license.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import resource
import sys
from time import perf_counter

import numpy as np
from PIL import Image, __version__ as pillow_version

SOURCE_SHA256 = '9a1923cd9bcb260ba4d99d64f8d6e32550648c332ba48817f920662f3a513420'
SOURCE_URL = 'https://openslide.cs.cmu.edu/download/openslide-testdata/Aperio/CMU-1-JP2K-33005.svs'


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def dump(path, value, compact=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False,
                               indent=None if compact else 2,
                               separators=(',', ':') if compact else None)+'\n')


def generate_pyramid(slide, output_dir, tile_size=1022, overlap=1, quality=75, workers=4):
    """Write all levels, including glass, and validate each saved tile geometry."""
    from openslide.deepzoom import DeepZoomGenerator
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    dz = DeepZoomGenerator(slide, tile_size=tile_size, overlap=overlap, limit_bounds=False)
    jobs = [(level, col, row) for level, (columns, rows) in enumerate(dz.level_tiles)
            for row in range(rows) for col in range(columns)]
    expected = {f'{level}/{col}_{row}.jpeg' for level, col, row in jobs}
    existing = {p.relative_to(output_dir).as_posix() for p in output_dir.rglob('*') if p.is_file()}
    if existing-expected:
        raise ValueError('Output contains files outside this pyramid; choose a clean output directory')
    for level in range(dz.level_count):
        (output_dir/str(level)).mkdir(exist_ok=True)

    def write(job):
        level, col, row = job
        tile = dz.get_tile(level, (col, row)).convert('RGB')
        expected_size = dz.get_tile_dimensions(level, (col, row))
        correction = None
        if tile.size != expected_size:
            if level == dz.level_count-1:
                raise ValueError('Native level tile geometry differs; native resizing is prohibited')
            # OpenSlide uses Pillow.thumbnail(), which can round one side down
            # to preserve aspect ratio. DZI declares ceil-rounded dimensions.
            correction = dict(before=list(tile.size), after=list(expected_size),
                              filter='LANCZOS', reason='OpenSlide thumbnail aspect-ratio rounding')
            tile = tile.resize(expected_size, Image.Resampling.LANCZOS)
        relative = f'{level}/{col}_{row}.jpeg'
        path = output_dir/relative
        temporary = path.with_suffix('.tmp')
        tile.save(temporary, format='JPEG', quality=quality, subsampling=2,
                  optimize=False, progressive=False)
        temporary.replace(path)
        return dict(path=relative, bytes=path.stat().st_size, sha256=sha256(path),
                    level=level, column=col, row=row, size=list(tile.size), geometry_adjustment=correction)

    print(json.dumps(dict(expected_tiles=dz.tile_count, levels=dz.level_count,
                          native_dimensions=dz.level_dimensions[-1], tile_size=tile_size,
                          overlap=overlap, quality=quality, workers=workers)), flush=True)
    started = perf_counter()
    records, byte_count = [], 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for record in pool.map(write, jobs):
            records.append(record)
            byte_count += record['bytes']
            if len(records) % 100 == 0 or len(records) == len(jobs):
                print(json.dumps(dict(completed_tiles=len(records), total_tiles=len(jobs),
                                      bytes=byte_count, elapsed_seconds=perf_counter()-started)), flush=True)
    generation_seconds = perf_counter()-started
    verify_start = perf_counter()
    assert len(records) == dz.tile_count
    for record in records:
        width, height = dz.level_dimensions[record['level']]
        x, y = record['column']*tile_size, record['row']*tile_size
        expected_size = (min(width, x+tile_size+overlap)-max(0, x-overlap),
                         min(height, y+tile_size+overlap)-max(0, y-overlap))
        with Image.open(output_dir/record['path']) as saved:
            if saved.size != expected_size or saved.format != 'JPEG':
                raise ValueError(f'Invalid saved tile geometry: {record["path"]}')
    actual_files = {p.relative_to(output_dir).as_posix() for p in output_dir.rglob('*') if p.is_file()}
    if actual_files != expected:
        raise ValueError('Written pyramid file set is incomplete or contains unexpected files')
    return dict(tile_count=len(records), level_count=dz.level_count, max_level=dz.level_count-1,
                native_dimensions=list(dz.level_dimensions[-1]),
                level_dimensions=[list(v) for v in dz.level_dimensions],
                level_tiles=[list(v) for v in dz.level_tiles], tile_size=tile_size, overlap=overlap,
                jpeg_quality=quality, jpeg_subsampling='4:2:0', jpeg_optimize=False,
                limit_bounds=False, sparse_tiles=False, total_bytes=byte_count,
                largest_tile_bytes=max(r['bytes'] for r in records),
                generation_seconds=generation_seconds, inventory_verification_seconds=perf_counter()-verify_start,
                all_tile_dimensions_verified=True, native_tiles_resized=0,
                lower_level_geometry_adjustments=[dict(path=r['path'], level=r['level'], **r['geometry_adjustment'])
                                                  for r in records if r['geometry_adjustment']], tiles=records)


def read_native_patch(output_dir, level, tile_size, overlap, x, y, width, height):
    """Decode a requested native patch from disjoint DZI cell interiors."""
    result = np.empty((height, width, 3), np.uint8)
    coverage = np.zeros((height, width), np.uint8)
    for col in range(x//tile_size, (x+width-1)//tile_size+1):
        for row in range(y//tile_size, (y+height-1)//tile_size+1):
            with Image.open(Path(output_dir)/str(level)/f'{col}_{row}.jpeg') as opened:
                tile = np.asarray(opened.convert('RGB'))
            x0, y0 = max(x, col*tile_size), max(y, row*tile_size)
            x1, y1 = min(x+width, (col+1)*tile_size), min(y+height, (row+1)*tile_size)
            origin_x, origin_y = max(0, col*tile_size-overlap), max(0, row*tile_size-overlap)
            result[y0-y:y1-y, x0-x:x1-x] = tile[y0-origin_y:y1-origin_y, x0-origin_x:x1-origin_x]
            coverage[y0-y:y1-y, x0-x:x1-x] += 1
    if not (coverage == 1).all():
        raise ValueError('Tile interiors failed to cover the requested patch exactly once')
    return result


def rgb_errors(a, b):
    difference = np.abs(a.astype(np.float64)-b.astype(np.float64))
    return dict(mae=float(difference.mean()), rmse=float(np.sqrt((difference**2).mean())),
                max_absolute_error=int(difference.max()), p95_absolute_error=float(np.percentile(difference, 95)))


def verify_alignment(slide, output_dir, pyramid, payload, dist_dir):
    """Sample the three fixed ROI locations plus native corners and tile seams."""
    started = perf_counter()
    samples = []
    for roi in payload['rois']:
        path = dist_dir/roi['image']
        if sha256(path) != roi['image_sha256']:
            raise ValueError('Saved native ROI PNG changed')
        stored = np.asarray(Image.open(path).convert('RGB'))
        native = np.asarray(slide.read_region(tuple(roi['origin']), 0, (roi['width'], roi['height'])).convert('RGB'))
        if not np.array_equal(native, stored):
            raise ValueError('Saved ROI differs from the pinned source native pixels')
        for x, y in ((96, 96), (448, 448), (800, 800)):
            x0, y0 = roi['origin'][0]+x, roi['origin'][1]+y
            rendered = read_native_patch(output_dir, pyramid['max_level'], pyramid['tile_size'],
                                         pyramid['overlap'], x0, y0, 96, 96)
            original = stored[y:y+96, x:x+96]
            samples.append(dict(roi_id=roi['id'], origin_local=[x,y], origin_level0=[x0,y0], size=[96,96],
                                correct=rgb_errors(rendered, original),
                                shifted_1_each_axis=rgb_errors(rendered, stored[y+1:y+97,x+1:x+97]),
                                shifted_16_each_axis=rgb_errors(rendered, stored[y+16:y+112,x+16:x+112])))
    # Include bottom-right native pixels (the thin final column is easy to drop)
    # and a native tile-grid intersection, independently of biological ROI choice.
    edge_samples = []
    width, height = slide.dimensions
    for x, y in ((0,0), (width-64,height-64), (1022-32,1022-32)):
        native = np.asarray(slide.read_region((x,y),0,(64,64)).convert('RGB'))
        rendered = read_native_patch(output_dir,pyramid['max_level'],pyramid['tile_size'],pyramid['overlap'],x,y,64,64)
        edge_samples.append(dict(origin_level0=[x,y],size=[64,64],correct=rgb_errors(rendered,native)))
    mae=[r['correct']['mae'] for r in samples]
    return dict(samples=samples, native_edge_samples=edge_samples, sample_count=len(samples),
                correct_mae_mean=float(np.mean(mae)), correct_mae_range=[min(mae),max(mae)],
                all_roi_pngs_match_native=True,
                all_correct_lower_than_both_shift_controls=all(r['correct']['mae']<r['shifted_1_each_axis']['mae']
                    and r['correct']['mae']<r['shifted_16_each_axis']['mae'] for r in samples),
                verification_seconds=perf_counter()-started,
                interpretation='Sampled native coordinate alignment with JPEG loss; no bit-exact display/native equality or inference accuracy claim.')


def update_viewing_metadata(args, report, tile_source):
    payload = json.loads(args.dist_json.read_text())
    original_methods = json.dumps([r['methods'] for r in payload['rois']], sort_keys=True)
    original_model = dict(payload['model'])
    payload['slide']['tile_source'] = tile_source
    provenance = payload['provenance']
    provenance['tile_hosting'] = dict(mode='self-hosted static full-resolution DZI',
        generator='scripts/export_wsi_tiles.py', generator_sha256=report['generator_sha256'],
        report='artifacts/wsi/local-tiles.json', source_sha256=SOURCE_SHA256,
        data_license='CC0-1.0', tile_count=report['pyramid']['tile_count'],
        total_bytes=report['pyramid']['total_bytes'], requires_external_tile_service=False,
        public_url=args.public_url)
    provenance['remote_tiles'] = 'Historical external alignment audit only; deployed external S3 tiles returned AccessDenied HTTP 403, so the viewer now uses locally generated static tiles.'
    provenance['source_identity'] = 'Analysis and self-hosted DZI derive from the same pinned CMU-1-JP2K-33005.svs original.'
    payload['limits'] = [text for text in payload['limits']
                         if text != 'Official external DZI tiles may become unavailable; local ROI images remain available.']
    payload['limits'].append('Static DZI preserves native dimensions with JPEG quality 75 re-encoding; displayed RGB is not bit-exact to source pixels.')
    payload['limits'] = list(dict.fromkeys(payload['limits']))
    assert original_model == payload['model']
    assert original_methods == json.dumps([r['methods'] for r in payload['rois']],sort_keys=True)
    public = json.loads(args.public_provenance.read_text())
    public['slide']['tile_source'] = tile_source
    public['provenance'] = provenance
    dump(args.dist_json, payload, compact=True)
    dump(args.experiment_json, payload)
    dump(args.public_provenance, public)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--slide',type=Path,required=True)
    parser.add_argument('--output-dir',type=Path,default=Path('dist/wsi/slide_files'))
    parser.add_argument('--public-url',default='wsi/slide_files/')
    parser.add_argument('--report',type=Path,default=Path('artifacts/wsi/local-tiles.json'))
    parser.add_argument('--dist-json',type=Path,default=Path('dist/wsi.json'))
    parser.add_argument('--experiment-json',type=Path,default=Path('artifacts/wsi/experiment.json'))
    parser.add_argument('--public-provenance',type=Path,default=Path('dist/wsi/provenance.json'))
    parser.add_argument('--workers',type=int,default=4)
    args=parser.parse_args()
    if args.workers<1 or args.workers>16:
        parser.error('--workers must be between 1 and 16')
    if not args.public_url.endswith('/') or args.public_url.startswith(('http:','https:','//')):
        parser.error('--public-url must be a relative static directory ending with /')
    started=perf_counter()
    if sha256(args.slide)!=SOURCE_SHA256:
        raise ValueError('Source SHA-256 does not match the licensed pinned WSI')
    payload=json.loads(args.dist_json.read_text())
    if payload['slide']['source_sha256']!=SOURCE_SHA256:
        raise ValueError('Viewer and analysis refer to a different source')
    protected=[args.report.parent/'source.json',args.report.parent/'protocol.json']
    protected+=list(args.report.parent.glob('R[123]_*.json'))
    protected+=list((args.dist_json.parent/'wsi').glob('*.png'))
    protected_hashes={str(path):sha256(path) for path in protected}
    before_model=json.loads(json.dumps(payload['model']))
    before_rois=json.loads(json.dumps(payload['rois']))
    import openslide
    with openslide.OpenSlide(args.slide) as slide:
        if slide.dimensions!=(46000,32893) or slide.color_profile is not None:
            raise ValueError('Pinned slide geometry/color-profile assumptions changed')
        slide.set_cache(openslide.OpenSlideCache(128 << 20))
        pyramid=generate_pyramid(slide,args.output_dir,workers=args.workers)
        alignment=verify_alignment(slide,args.output_dir,pyramid,payload,args.dist_json.parent)
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform=='darwin':rss/=1024
    source=dict(name=args.slide.name,url=SOURCE_URL,sha256=SOURCE_SHA256,bytes=args.slide.stat().st_size,
                license='CC0-1.0',license_url='https://creativecommons.org/publicdomain/zero/1.0/',
                rights_source='https://openslide.cs.cmu.edu/download/openslide-testdata/index.json')
    config={'Image':{'xmlns':'http://schemas.microsoft.com/deepzoom/2008','Url':args.public_url,
                     'Format':'jpeg','TileSize':1022,'Overlap':1,'Size':{'Width':46000,'Height':32893}}}
    report=dict(schema_version=1,generated_at_utc=datetime.now(timezone.utc).isoformat(),source=source,
                generator='scripts/export_wsi_tiles.py',generator_sha256=sha256(Path(__file__)),
                generator_library_license='OpenSlide LGPL-2.1; distinct from CC0 image data.',
                tile_source=config,pyramid=pyramid,alignment=alignment,
                elapsed_seconds_before_metadata_update=perf_counter()-started,peak_process_rss_mib=rss/1024,
                memory_scope='Whole standalone tile generation process high-water RSS, including 128MiB OpenSlide cache, tile worker pool, JPEG encoding, inventory and RGB alignment verification; no model loaded.',
                runtime=dict(python=sys.version.split()[0],openslide=openslide.__library_version__,
                    openslide_python=openslide.__version__,pillow=pillow_version,platform=platform.platform(),
                    workers=args.workers,cpu_count=os.cpu_count(),openslide_cache_mib=128),
                reason='Official S3 tile requests from the public deployment returned AccessDenied HTTP403 despite CORS *; no bypass attempted. Generate from already acquired CC0 original and serve same-origin static files.',
                historical_remote_audit='artifacts/wsi/tile-alignment.json',inference_run=False,
                reproduction='Run pathology_edge.wsi_export first, then this CLI; tile build updates viewing metadata only.',
                protected_file_hashes=protected_hashes)
    if protected_hashes!={path:sha256(Path(path)) for path in protected_hashes}:
        raise ValueError('A protected source/protocol/ROI/inference artifact changed during tile generation')
    current=json.loads(args.dist_json.read_text())
    if before_model!=current['model'] or before_rois!=current['rois']:
        raise ValueError('Model/ROI payload changed while tiling; do not overwrite it')
    dump(args.report,report)
    update_viewing_metadata(args,report,config)
    result=json.loads(args.dist_json.read_text())
    assert result['model']==before_model and result['rois']==before_rois
    assert result==json.loads(args.experiment_json.read_text())
    print(json.dumps(dict(finished=True,tile_count=pyramid['tile_count'],total_bytes=pyramid['total_bytes'],
        generation_seconds=pyramid['generation_seconds'],peak_process_rss_mib=report['peak_process_rss_mib'],
        native_dimensions=pyramid['native_dimensions'],alignment_mae_range=alignment['correct_mae_range'],
        inference_run=False)),flush=True)


if __name__=='__main__':
    main()
