import requests,json,hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from pathology_edge.wsi_source import RangeReader,verify_stream,SourceDigestMismatch,decode_tiled_roi
import tifffile,numpy as np
from PIL import Image
root=Path(__file__).resolve().parent
rows=json.load(open(root/'acquired/protocol.json'))['cases'][1:]
def run(item):
 g=item['gdc_matching'][0];url='https://api.gdc.cancer.gov/data/'+g['file_id'];folder=root/'acquired'/item['case_id']
 def normalized_get(url,headers,timeout):
  r=requests.get(url,headers=headers,timeout=timeout)
  if r.status_code==206 and r.headers.get('Content-Range','').startswith(tuple('0123456789')):r.headers['Content-Range']='bytes '+r.headers['Content-Range']
  return r
 reader=RangeReader(url,g['file_size'],get=normalized_get)
 import re
 left,top,bottom,right=map(int,re.search(r'_left-(\d+)_top-(\d+)_bottom-(\d+)_right-(\d+)',item['roi']).groups())
 with tifffile.TiffFile(reader) as t:
  crop,_=decode_tiled_roi(t.pages[0],reader,(left,top,right,bottom))
 old=np.asarray(Image.open(folder/'native.png'));same=bool(np.array_equal(crop,old))
 Image.fromarray(crop).save(folder/'gdc-native.png')
 print(item['case_id'],'GDC/DSA native equal:',same,flush=True)
 with requests.get(url,headers={'Accept-Encoding':'identity'},stream=True,timeout=(15,60)) as r:
  r.raise_for_status()
  if r.status_code!=200:raise ValueError(('Full original HTTP',r.status_code))
  try:result=verify_stream(r.iter_content(4*1024**2),g['file_size'],reader.blocks,g['md5sum']);status='matched'
  except SourceDigestMismatch as e:result=e.observed;status='mismatched'
 data=dict(case_id=item['case_id'],source_url=url,reference_md5=g['md5sum'],status=status,observed=result,native_gdc_dsa_pixels_equal=same,gdc_native_sha256=hashlib.sha256((folder/'gdc-native.png').read_bytes()).hexdigest())
 (root/(item['case_id']+'-direct-gdc-audit.json')).write_text(json.dumps(data,indent=2));print(json.dumps(data),flush=True)
with ThreadPoolExecutor(max_workers=2) as p:list(p.map(run,rows))
