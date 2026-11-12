import json,hashlib,shutil,re
from pathlib import Path
from PIL import Image
import numpy as np,cv2,tifffile
from pathology_edge.wsi_source import RangeReader
root=Path(__file__).resolve().parent;old=root/'acquired';out=root/'verified-pairs'
if out.exists():raise ValueError('Fresh output required')
out.mkdir();shutil.copy2(old/'ALL_FOV_LOCATIONS.csv',out/'ALL_FOV_LOCATIONS.csv')
protocol=json.load(open(old/'protocol.json'));protocol['acquisition_amendment']='Before inference: mirror MD5 mismatch led to direct GDC source for ST/SX; native crops identical. D2 retains verified entire mirror stream without an independent reference MD5.'
protocol['annotation_amendment']='Before inference: require originalmask and full-canvas Pillow integer CSV polyline agreement; ignore disagreements in either direction. D2 haszero polylines, report background-only false-positive control and exclude from contour-casemacro.'
protocol['rasterization_claim']='Explicit conservative agreement convention, not reproduction of historical exporter; excludededgepixels can bias metrics.'
protocol['original_selection_protocol_sha256']=hashlib.sha256((old/'protocol.json').read_bytes()).hexdigest()
protocol['source_reader_sha256']=hashlib.sha256(Path('src/pathology_edge/wsi_source.py').read_bytes()).hexdigest()
protocol['acquisition_script_sha256']=hashlib.sha256(Path('scripts/acquire_wsi_pairs.py').read_bytes()).hexdigest()
records=[]
for item in protocol['cases']:
 case=item['case_id'];folder=out/case;folder.mkdir()
 for name in ('rgbs.png','masks.png','csv.csv','native.png','original-roi.png'):shutil.copy2(old/case/name,folder/name)
 if item['gdc_matching']:
  gdc=json.load(open(root/(case+'-direct-gdc-audit.json')))
  assert gdc['status']=='matched' and gdc['observed']['reference_md5_verified'] and gdc['native_gdc_dsa_pixels_equal']
  assert hashlib.sha256((old/case/'gdc-native.png').read_bytes()).hexdigest()==gdc['gdc_native_sha256']
  assert np.array_equal(np.asarray(Image.open(old/case/'gdc-native.png')),np.asarray(Image.open(folder/'native.png')))
  shutil.copy2(old/case/'gdc-native.png',folder/'native.png')
  r=RangeReader(gdc['source_url'],gdc['observed']['bytes'],allow_unitless_range=True)
  with tifffile.TiffFile(r) as t:
   p=t.pages[0];metadata=dict(size_wh=[p.imagewidth,p.imagelength],native_mpp=float(re.search(r'\|MPP\s*=\s*([0-9.]+)',p.description).group(1)),metadata_source='GDC original TIFF page0')
  result=dict(original_stream=gdc['observed'],original_url=gdc['source_url'],metadata=metadata,mirror_native_pixels_equal=True,reference='GDC exactDX1 fileMD5',mirror_reference_md5_mismatch=True)
 else:result=json.load(open(old/case/'source-audit.json'))
 rgb=np.asarray(Image.open(folder/'original-roi.png'));provided=np.asarray(Image.open(folder/'rgbs.png'));shift,response=cv2.phaseCorrelate(cv2.cvtColor(provided,cv2.COLOR_RGB2GRAY).astype(np.float32),cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY).astype(np.float32))
 result.update(case_id=case,roi=item['roi'],comparison=dict(rgb_correlation=float(np.corrcoef(rgb.ravel(),provided.ravel())[0,1]),rgb_mae=float(np.abs(rgb.astype(float)-provided).mean()),phase_shift_xy=shift,phase_response=response),files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir() if p.is_file()})
 (folder/'source-audit.json').write_text(json.dumps(result,indent=2));records.append(result)
(out/'protocol.json').write_text(json.dumps(protocol,indent=2))
(out/'acquisition.json').write_text(json.dumps(dict(all_sources_verified=True,meaning='entire source streams and ROI block binding verified; independentGDCreference2of3',reference_md5_verified_cases=2,cases=records),indent=2))
print('Finalized:3 original streams,2 official GDC MD5 matches; all raw input hashes saved before inference')
