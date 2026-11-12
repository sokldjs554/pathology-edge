#!/usr/bin/env python3
"""Acquire original SVS bytes + matching manual annotation ROIs, before inference."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
from pathlib import Path
import re
import shutil

import cv2
import numpy as np
from PIL import Image
import requests
import tifffile

from pathology_edge.wsi_source import RangeReader, decode_tiled_roi, verify_stream, validate_source_item


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False))


def acquire_case(item, out):
    validate_source_item(item)
    case = item['case_id']
    folder = out/case
    folder.mkdir()
    for kind, asset in item['annotations'].items():
        r = requests.get('https://drive.google.com/uc', params={'export':'download','id':asset['id']}, timeout=45)
        r.raise_for_status()
        if 'html' in r.headers.get('Content-Type',''):
            raise ValueError('Annotation access returned HTML')
        (folder/(kind+('.csv' if kind=='csv' else '.png'))).write_bytes(r.content)
    file = item['dsa_files'][0]
    url = 'https://demo.kitware.com/histomicstk/api/v1/file/'+file['_id']+'/download'
    if item['gdc_matching']:
        url = 'https://api.gdc.cancer.gov/data/'+item['gdc_matching'][0]['file_id']
    reader = RangeReader(url, file['size'], allow_unitless_range=bool(item['gdc_matching']))
    left, top, bottom, right = map(int, re.search(r'_left-(\d+)_top-(\d+)_bottom-(\d+)_right-(\d+)',item['roi']).groups())
    with tifffile.TiffFile(reader) as slide:
        page = slide.pages[0]
        orientation = page.tags.get('Orientation')
        if orientation is not None and orientation.value != 1:
            raise ValueError('Nonstandard TIFF orientation')
        native, tiles = decode_tiled_roi(page, reader, (left,top,right,bottom))
        mpp = float(re.search(r'\|MPP\s*=\s*([0-9.]+)',page.description).group(1))
        metadata = dict(size_wh=[page.imagewidth,page.imagelength], native_mpp=mpp,
                        tile_wh=[page.tilewidth,page.tilelength], compression=int(page.compression),
                        description_sha256=hashlib.sha256(page.description.encode()).hexdigest(),
                        decoded_tiles=tiles, bounds_level0=[left,top,right,bottom],
                        output_mpp_xy=[mpp*(right-left)/1024,mpp*(bottom-top)/1024],
                        color_profile_applied=False)
    Image.fromarray(native).save(folder/'native.png')
    resized = Image.fromarray(native).resize((1024,1024),Image.Resampling.BILINEAR)
    resized.save(folder/'original-roi.png')
    provided = np.asarray(Image.open(folder/'rgbs.png').convert('RGB'))
    if provided.shape != (1024,1024,3):
        raise ValueError('Unexpected manual RGB dimensions')
    pixels=np.asarray(resized)
    shift,response=cv2.phaseCorrelate(cv2.cvtColor(provided,cv2.COLOR_RGB2GRAY).astype(np.float32),
                                    cv2.cvtColor(pixels,cv2.COLOR_RGB2GRAY).astype(np.float32))
    comparison=dict(rgb_correlation=float(np.corrcoef(provided.ravel(),pixels.ravel())[0,1]),
                    rgb_mae=float(np.abs(provided.astype(float)-pixels).mean()),
                    phase_shift_xy=shift,phase_response=response,
                    registration_correction_applied=False)
    expected = item['gdc_matching'][0]['md5sum'] if item['gdc_matching'] else None
    if item['gdc_matching'] and item['gdc_matching'][0]['file_size'] != file['size']:
        raise ValueError('GDC/mirror size mismatch')
    def chunks(response):
        total=0;next_progress=256*1024**2
        for chunk in response.iter_content(4*1024**2):
            total+=len(chunk)
            if total>=next_progress:
                print(f'{case}: original stream {total//1024**2} MiB',flush=True)
                next_progress+=256*1024**2
            yield chunk
    with requests.get(url,headers={'Accept-Encoding':'identity'},stream=True,timeout=(15,60)) as response:
        response.raise_for_status()
        if response.status_code != 200:
            raise ValueError('Expected complete original response')
        full = verify_stream(chunks(response),file['size'],reader.blocks,expected)
    result = dict(case_id=case,roi=item['roi'],original_url=url,original_file=file['name'],
                  original_stream=full,metadata=metadata,comparison=comparison,
                  source_ranges=[dict(offset=k,bytes=len(v),sha256=hashlib.sha256(v).hexdigest()) for k,v in sorted(reader.blocks.items())],
                  files={p.name:sha(p) for p in folder.iterdir() if p.is_file()},
                  entire_original_retained_on_disk=False,full_slide_inference=False)
    save(folder/'source-audit.json',result)
    print(f'{case}: original verified, MD5 reference={full["reference_md5_verified"]}',flush=True)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--previous-data',type=Path,required=True)
    parser.add_argument('--source-files',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():
        raise ValueError('Use a fresh output directory')
    listings={kind:{r['name'].rsplit('.',1)[0]:r for r in json.loads((args.previous_data/(kind+'-listing.json')).read_text())}
              for kind in ('rgbs','masks','csv')}
    common=sorted(set.intersection(*(set(x) for x in listings.values())))
    groups={}
    for name in common:
        groups.setdefault('-'.join(name.split('-')[:3]),[]).append(name)
    sources=json.loads(args.source_files.read_text())
    expected=['TCGA-A2-A0D2','TCGA-A2-A0ST','TCGA-A2-A0SX']
    if [r['case_id'] for r in sources] != expected:
        raise ValueError('Prespecified new case list differs')
    for item in sources:
        name=groups[item['case_id']][0]
        item['roi']=name
        item['annotations']={kind:listing[name] for kind,listing in listings.items()}
    args.output.mkdir(parents=True)
    shutil.copy2(args.previous_data/'csv/ALL_FOV_LOCATIONS.csv',args.output/'ALL_FOV_LOCATIONS.csv')
    protocol=dict(cases=sources,selection='First lexical manual ROI from each of3remaining cases in initial50entry publiclistings; none previously predicted',
        expected_model_sha256={'small_vit':'0bb2af67ca4d4e403e5789359feb6b284f9207e6c7eb9bf4e521b7d0972f5898',
                              'small_vit_refined':'b9d3892a257a06ed0b67bd4e8717a331d457272531b3501fadf1fbacd70f004f'},
        threshold=.35,primary_input='Direct original SVS native crop then Pillow BILINEAR1024square',
        secondary_input='Exactly provided1024squareRGB, same labels; paired rendering sensitivity, not independent data',
        annotation_region='FOV/nonzero tissue/nuclear1to7or9, excluding0and8 and inclusive rectangles; additionally require mask/full-canvas Pillow integerpolyline agreement, ignore disagreements both ways',
        primary_macro='Only cases with valid foreground contour GT; retain D2 as background-only false-positive control',
        rasterization_claim='Conservative audit convention, not historical exporter parity',
        inference='128px no_overlap, same frozen pipeline; no stain normalization or registration correction',
        full_stream='Every original byte hashed; every fetched metadata/tile block compared to same whole stream; GDC MD5 if exact DX1 available',
        alignment_gate='Inspect RGB and overlays before predictions; technical coordinate/shape failures recorded, not replaced; no performance-based exclusion',
        clinical_validation=False,full_wsi_ground_truth_validation=False,
        acquisition_script_sha256=sha(__file__),source_reader_sha256=sha(Path(__file__).resolve().parents[1]/'src/pathology_edge/wsi_source.py'))
    save(args.output/'protocol.json',protocol)
    with ThreadPoolExecutor(max_workers=3) as executor:
        results=list(executor.map(lambda item:acquire_case(item,args.output),sources))
    save(args.output/'acquisition.json',dict(all_sources_verified=True,cases=results))


if __name__=='__main__':
    main()
