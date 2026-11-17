"""Learned cell center heatmaps; no nuclear boundary or clinical probability claim."""
import math
import numpy as np
from scipy.ndimage import maximum_filter, label
import torch
from torch.nn import functional as F
from .model import TinyUNet
from .ki67_detection import validate_rgb
from .ki67_evaluation import points_array


def _positive(value, name):
    if isinstance(value,(str,bool)) or not np.isscalar(value) or not np.isrealobj(value) or not np.isfinite(value) or value<=0:
        raise ValueError(name+' must be positive finite real')
    return float(value)


def center_target(points_xy, shape_hw, sigma=2):
    sigma=_positive(sigma,'sigma')
    if len(shape_hw)!=2 or any(isinstance(v,bool) or not isinstance(v,(int,np.integer)) or v<=0 for v in shape_hw):
        raise ValueError('Expected positive integer height/width')
    h,w=shape_hw; points=points_array(points_xy)
    if np.any(points!=np.floor(points)) or np.any(points<0) or np.any(points[:,0]>=w) or np.any(points[:,1]>=h) or len(np.unique(points,axis=0))!=len(points):
        raise ValueError('Expected unique integer XY centers inside image')
    result=np.zeros((h,w),dtype=np.float32)
    radius=math.ceil(3*sigma)
    for x,y in points.astype(np.int64):
        x0,x1=max(0,x-radius),min(w,x+radius+1)
        y0,y1=max(0,y-radius),min(h,y+radius+1)
        yy,xx=np.mgrid[y0:y1,x0:x1]
        squared=(xx-x)**2+(yy-y)**2
        values=np.where(squared<=radius**2,np.exp(-squared/(2*sigma**2)),0).astype(np.float32)
        result[y0:y1,x0:x1]=np.maximum(result[y0:y1,x0:x1],values)
    return result


def center_focal_loss(logits,target):
    if not isinstance(logits,torch.Tensor) or not isinstance(target,torch.Tensor):
        raise ValueError('Expected tensors')
    if logits.ndim!=4 or logits.shape[1]!=1 or min(logits.shape)<=0 or logits.shape!=target.shape or not logits.is_floating_point() or not target.is_floating_point() or logits.device!=target.device or logits.dtype!=target.dtype:
        raise ValueError('Expected same floating Bx1xHxW tensors')
    if not torch.isfinite(logits).all() or not torch.isfinite(target).all() or torch.any(target<0) or torch.any(target>1):
        raise ValueError('Expected finite logits and target in [0,1]')
    p=torch.sigmoid(logits)
    centers=target==1
    terms=torch.where(centers,(1-p).square()*F.softplus(-logits),
                      p.square()*(1-target).pow(4)*F.softplus(logits))
    n=centers.sum((1,2,3)).clamp_min(1)
    return (terms.sum((1,2,3))/n).mean()


class CenterDetector(TinyUNet):
    """Small native-resolution encoder/decoder trained on point-derived maps."""
    def __init__(self):
        super().__init__(width=4)
        # Preserve gradients for negative features in this narrow detector.
        # Existing H&E TinyUNet and its checkpoints retain their original ReLUs.
        for name in ('e1','e2','bottom','d2','d1'):
            block=getattr(self,name)
            block[1]=torch.nn.LeakyReLU(.1)
            block[3]=torch.nn.LeakyReLU(.1)
        torch.nn.init.constant_(self.head.bias,-2.19)

    def forward(self,x):
        if x.ndim!=4 or x.shape[0]<1 or x.shape[1]!=3 or min(x.shape[2:])<4 or not x.is_floating_point() or not torch.isfinite(x).all():
            raise ValueError('Expected finite Bx3xHxW, H/W >=4')
        return super().forward(x)


def peak_candidates(probability_map):
    heat=np.asarray(probability_map)
    if heat.ndim!=2 or not heat.size or heat.dtype.kind not in 'iuf' or not np.isfinite(heat).all() or np.any(heat<0) or np.any(heat>1):
        raise ValueError('Expected nonempty finite HW probability map in [0,1]')
    maxima=(heat>0)&(heat==maximum_filter(heat,size=3,mode='constant',cval=-1))
    regions,_=label(maxima,structure=np.ones((3,3),dtype=int))
    yy,xx=np.nonzero(maxima)
    if not len(xx): return np.empty((0,2),dtype=np.int64),np.empty(0,dtype=np.float64)
    ids=regions[yy,xx]
    counts=np.bincount(ids)
    meanx=np.bincount(ids,weights=xx)/np.maximum(counts,1)
    meany=np.bincount(ids,weights=yy)/np.maximum(counts,1)
    distance=(xx-meanx[ids])**2+(yy-meany[ids])**2
    order=np.lexsort((xx,yy,distance,ids))
    first=np.r_[True,ids[order][1:]!=ids[order][:-1]]
    keep=order[first];points=np.column_stack([xx[keep],yy[keep]])
    scores=heat[yy[keep],xx[keep]].astype(np.float64)
    order=np.lexsort((points[:,0],points[:,1],-scores))
    return points[order],scores[order]


def decode_candidates(points,scores,threshold,min_distance):
    threshold=_positive(threshold,'threshold'); min_distance=_positive(min_distance,'min_distance')
    points=points_array(points);scores=np.asarray(scores)
    if threshold>1 or scores.shape!=(len(points),) or scores.dtype.kind not in 'iuf' or not np.isfinite(scores).all() or np.any(scores<0) or np.any(scores>1) or np.any(points<0) or np.any(points!=np.floor(points)):
        raise ValueError('Invalid candidates/configuration')
    order=np.lexsort((points[:,0],points[:,1],-scores))
    kept=[];buckets={}
    # Spatial buckets keep dense/flat inputs from quadratic full-list scans.
    for i in order:
        if scores[i]<threshold: continue
        x,y=points[i];bucket=(math.floor(x/min_distance),math.floor(y/min_distance))
        neighbors=[j for dx in (-1,0,1) for dy in (-1,0,1) for j in buckets.get((bucket[0]+dx,bucket[1]+dy),[])]
        if any(float(np.sum((points[i]-points[j])**2))<min_distance**2 for j in neighbors): continue
        kept.append(int(i));buckets.setdefault(bucket,[]).append(int(i))
    return dict(points_xy=points[kept].astype(np.int64).reshape(-1,2),scores=scores[kept].astype(np.float64))


def decode_centers(probability_map,threshold,min_distance):
    return decode_candidates(*peak_candidates(probability_map),threshold,min_distance)


def predict_centers(rgb,model,config):
    validate_rgb(rgb)
    if not isinstance(model,CenterDetector) or not all(torch.isfinite(t).all() for t in model.state_dict().values()):
        raise ValueError('Expected finite CenterDetector weights')
    if not isinstance(config,dict) or set(config)!={'threshold','min_distance'}:
        raise ValueError('Expected threshold and min_distance')
    model.eval()
    x=torch.from_numpy(rgb.transpose(2,0,1).copy()).to(device=next(model.parameters()).device,dtype=torch.float32).unsqueeze(0)/255
    with torch.inference_mode(): heat=torch.sigmoid(model(x))[0,0].cpu().numpy()
    return {**decode_centers(heat,**config),'probability_map':heat}
