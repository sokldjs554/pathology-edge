"""Prospective DeepLIIF paired-image adapter; all-cell staining, not tumor LI.

Centroids are derived from supplied segmentation interiors, not expert point
annotations. This explicit adapter is not the official DeepLIIF scoring method.
"""
import hashlib
import io
import struct
import urllib.error
import urllib.request
import zlib
import numpy as np
from PIL import Image
from scipy import ndimage


def segmentation_centers(mask):
    if not isinstance(mask,np.ndarray) or mask.dtype!=np.uint8 or mask.ndim!=3 or mask.shape[2]!=3 or not mask.size:
        raise ValueError('Expected nonempty uint8 RGB reference mask')
    red=np.all(mask==[255,0,0],axis=2);blue=np.all(mask==[0,0,255],axis=2);green=np.all(mask==[0,255,0],axis=2);black=np.all(mask==0,axis=2)
    if not np.all(red|blue|green|black):raise ValueError('Unexpected reference colors')
    labels,n=ndimage.label(red|blue,structure=np.ones((3,3),bool));points=[];classes=[]
    audit=dict(total_components=int(n),retained_components=0,discarded_small_components=0,discarded_small_pixels=0,mixed_components=0,border_components=0,green_pixels=int(green.sum()))
    for i,slices in enumerate(ndimage.find_objects(labels),1):
        yy,xx=np.where(labels[slices]==i);yy+=slices[0].start;xx+=slices[1].start;area=len(xx)
        if area<=4:
            audit['discarded_small_components']+=1;audit['discarded_small_pixels']+=area;continue
        positive=int(red[yy,xx].sum());negative=area-positive
        if positive==negative:raise ValueError('Reference component class tie')
        points.append([float(xx.mean()),float(yy.mean())]);classes.append(0 if positive>negative else 1)
        audit['mixed_components']+=int(positive>0 and negative>0)
        audit['border_components']+=int(np.any((xx==0)|(xx==mask.shape[1]-1)|(yy==0)|(yy==mask.shape[0]-1)))
    audit['retained_components']=len(points)
    return np.asarray(points,dtype=np.float64).reshape(-1,2),np.asarray(classes,dtype=np.int64),audit


def decode_paired_png(raw):
    image=Image.open(io.BytesIO(raw))
    if image.format!='PNG' or image.mode!='RGB' or image.size!=(3072,512):raise ValueError('Expected six native512 RGB PNG tiles')
    array=np.asarray(image);xy,classes,audit=segmentation_centers(array[:,2560:3072])
    return array[:,:512].copy(),xy,classes,audit


def read_range(url,low,high,total):
    if any(type(v) is not int for v in (low,high,total)) or not 0<=low<=high<total or high-low+1>8_000_000:raise ValueError('Invalid bounded byte range')
    request=urllib.request.Request(url,headers={'Range':f'bytes={low}-{high}'})
    with urllib.request.urlopen(request,timeout=60) as response:
        if response.status!=206 or response.headers.get('Content-Range')!=f'bytes {low}-{high}/{total}':raise ValueError('Refuse full or mismatched archive response')
        raw=response.read(high-low+2)
    if len(raw)!=high-low+1:raise ValueError('Truncated or extra range bytes')
    return raw


def fetch_zip_entry(url,entry,total):
    low=entry['offset'];header=read_range(url,low,low+29,total)
    fields=struct.unpack('<4s5H3L2H',header);nlen,elen=fields[-2:]
    if fields[0]!=b'PK\x03\x04' or fields[2]&1 or fields[3]!=8 or entry['method']!=8:raise ValueError('Unsupported ZIP local header')
    size=nlen+elen+entry['compressed_bytes'];tail=read_range(url,low+30,low+29+size,total)
    if tail[:nlen].decode('utf-8')!=entry['name']:raise ValueError('ZIP name mismatch')
    decompressor=zlib.decompressobj(-15);data=decompressor.decompress(tail[nlen+elen:],entry['uncompressed_bytes']+1)
    if not decompressor.eof or decompressor.unused_data or decompressor.unconsumed_tail or len(data)!=entry['uncompressed_bytes'] or zlib.crc32(data)!=entry['crc32']:raise ValueError('ZIP payload size/CRC mismatch')
    return data,{**entry,'sha256':hashlib.sha256(data).hexdigest(),'range_bytes':30+size}


def paired_fraction(a,b):
    def indexed(rows):
        out={r['image']:r for r in rows}
        if len(out)!=len(rows):raise ValueError('Duplicate fraction image ID')
        for r in rows:
            for k in ('gt_fraction','pred_fraction'):
                v=r[k]
                if v is not None and (not np.isfinite(v) or not 0<=v<=1):raise ValueError('Invalid fraction')
        return out
    aa,bb=indexed(a),indexed(b)
    if set(aa)!=set(bb) or any(aa[k]['gt_fraction']!=bb[k]['gt_fraction'] for k in aa):raise ValueError('Fraction membership/reference mismatch')
    gt=sorted(k for k in aa if aa[k]['gt_fraction'] is not None)
    av=sorted(k for k in gt if aa[k]['pred_fraction'] is not None);bv=sorted(k for k in gt if bb[k]['pred_fraction'] is not None)
    common=sorted(set(av)&set(bv));missing=sorted(set(av)-set(bv));valid=bool(av) and not missing
    error=lambda rows,ids:float(np.mean([abs(rows[k]['pred_fraction']-rows[k]['gt_fraction'])*100 for k in ids])) if ids else None
    am=error(aa,av);bm=error(bb,av) if valid else None
    return dict(gt_valid_ids=gt,A_valid_ids=av,B_valid_ids=bv,reference_ids=av,common_ids=common,missing_B_ids=missing,additional_B_ids=sorted(set(bv)-set(av)),
        same_reference_coverage=valid,A_mae_pp=am,B_mae_pp=bm,passed=valid and bm<=am)


def validate_membership(protocol,index):
    names=[e['name'] for e in index['entries'] if e['name'].endswith('.png')]
    expected=set(names)-{protocol['excluded_format_probe']};included=protocol['included_names']
    if (len(names)!=598 or len(names)!=len(set(names)) or protocol['excluded_format_probe'] not in names
        or len(included)!=597 or len(set(included))!=597 or set(included)!=expected or protocol['image_count']!=597):raise ValueError('Prospective image membership changed')
    return included


def score_rows(rows,arm,radius):
    from .ki67_evaluation import evaluate_cells,count_metrics,class_array
    if not rows or len({r['image'] for r in rows})!=len(rows):raise ValueError('Nonempty unique external rows required')
    evaluations=[];images=[]
    for r in rows:
        pc=class_array(r['classes'][arm])%2;tc=class_array(r['gt_classes'])
        if np.any(tc>1):raise ValueError('Expected positive/negative reference only')
        e=evaluate_cells(np.asarray(r['points']).reshape(-1,2),pc,np.asarray(r['gt_points']).reshape(-1,2),tc,radius);evaluations.append(e)
        images.append(dict(image=r['image'],localization=e['localization'],classes=e['classes'][:2],two_class_macro_f1=float(np.mean([c['f1'] for c in e['classes'][:2]])),
            gt_cells=len(tc),pred_cells=len(pc),gt_positive=int((tc==0).sum()),pred_positive=int((pc==0).sum()),
            gt_fraction=float((tc==0).mean()) if len(tc) else None,pred_fraction=float((pc==0).mean()) if len(pc) else None))
    summed=lambda key:count_metrics(*[sum(e[key][k] for e in evaluations) for k in ('tp','fp','fn')])
    classes=[count_metrics(*[sum(e['classes'][c][k] for e in evaluations) for k in ('tp','fp','fn')]) for c in range(2)]
    return dict(localization=summed('localization'),classes=classes,two_class_macro_f1=float(np.mean([c['f1'] for c in classes])),image_count=len(rows),radius_native_px=radius,per_image=images,
                scope='All-cell positive/negative staining; non-tumor predictions remain cells; not tumor-specific Ki67 index')
