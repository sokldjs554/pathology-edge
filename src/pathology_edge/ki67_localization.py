"""Candidate-native neighborhood correspondence and bounded local XY refinement."""
import numpy as np
from scipy.spatial.distance import cdist
import torch
from torch import nn
from torch.nn import functional as F
from .ki67_detection import validate_rgb
from .ki67_union import _coordinates

RADIUS=12.


def reflected_context(rgb,points):
    """33px context has an integer-centered rotation anchor at(16,16)."""
    validate_rgb(rgb);points=_coordinates(points,rgb.shape[:2])
    padded=np.pad(rgb,((16,16),(16,16),(0,0)),mode='reflect')
    out=np.empty((len(points),33,33,3),dtype=np.uint8)
    for i,(x,y) in enumerate(points):out[i]=padded[y:y+33,x:x+33]
    return out


def transform_sample(context,offset,k,flip_y,flip_x):
    if not isinstance(context,np.ndarray) or context.shape!=(33,33,3) or context.dtype!=np.uint8:
        raise ValueError('Expected native33 RGB context')
    offset=np.asarray(offset,dtype=np.float64)
    if offset.shape!=(2,) or not np.isfinite(offset).all() or k not in (0,1,2,3):raise ValueError('Invalid offset/rotation')
    crop=np.rot90(context,k);dx,dy=offset
    rotated=[(dx,dy),(dy,-dx),(-dx,-dy),(-dy,dx)][k]
    dx,dy=rotated
    if flip_y:crop=np.flip(crop,axis=0);dy=-dy
    if flip_x:crop=np.flip(crop,axis=1);dx=-dx
    return crop[:32,:32],np.array([dx,dy],dtype=np.float32)


def proxy_targets(points,gt,shape_hw):
    points,gt=_coordinates(points,shape_hw),_coordinates(gt,shape_hw)
    labels=np.full(len(points),-1,dtype=np.int64);offsets=np.zeros((len(points),2),dtype=np.float32)
    nearest=np.full(len(points),-1,dtype=np.int64)
    if len(points) and len(gt):
        distance=cdist(points,gt);nearest=distance.argmin(axis=1);d=distance[np.arange(len(points)),nearest]
        positive=d<=RADIUS;labels[positive]=1;offsets[positive]=(gt[nearest[positive]]-points[positive]).astype(np.float32)
        interior=(points>=24).all(axis=1)&(points[:,0]<shape_hw[1]-24)&(points[:,1]<shape_hw[0]-24)
        labels[interior&(d>RADIUS)]=0
    return dict(labels=labels,offsets=offsets,nearest=nearest)


def bounded_offsets(raw):
    if not isinstance(raw,torch.Tensor) or raw.ndim!=2 or raw.shape[1]!=2 or not raw.is_floating_point() or not torch.isfinite(raw).all():
        raise ValueError('Expected finite Nx2 offset tensor')
    offsets=torch.tanh(raw)*RADIUS
    norm=torch.linalg.vector_norm(offsets,dim=1,keepdim=True)
    return offsets/torch.clamp(norm/RADIUS,min=1.)


def corrected_points(points,offsets,shape_hw):
    points=_coordinates(points,shape_hw);offsets=np.asarray(offsets)
    if offsets.shape!=points.shape or offsets.dtype.kind not in 'iuf' or not np.isfinite(offsets).all() or np.any(np.linalg.norm(offsets,axis=1)>RADIUS+1e-5):
        raise ValueError('Expected finite continuous offsets with norm<=12px')
    corrected=np.rint(points.astype(np.float64)+offsets.astype(np.float64)).astype(np.int64)
    corrected[:,0]=np.clip(corrected[:,0],0,shape_hw[1]-1);corrected[:,1]=np.clip(corrected[:,1],0,shape_hw[0]-1)
    return corrected


class LocalizationGate(nn.Module):
    def __init__(self,mean=None,scale=None):
        super().__init__();layers=[];previous=3
        for channels in (8,16,32):
            layers.extend([nn.Conv2d(previous,channels,3,padding=1),nn.LeakyReLU(.1),nn.Conv2d(channels,channels,3,padding=1),nn.LeakyReLU(.1),nn.MaxPool2d(2)]);previous=channels
        self.features=nn.Sequential(*layers);self.metadata=nn.Sequential(nn.Linear(4,16),nn.LeakyReLU(.1))
        self.score_head=nn.Linear(528,2);self.offset_head=nn.Linear(528,2)
        nn.init.zeros_(self.offset_head.weight);nn.init.zeros_(self.offset_head.bias)
        mean=np.zeros(4) if mean is None else np.asarray(mean)
        scale=np.ones(4) if scale is None else np.asarray(scale)
        if mean.shape!=(4,) or scale.shape!=(4,) or not np.isfinite(mean).all() or not np.isfinite(scale).all() or np.any(scale<=0):raise ValueError('Invalid training normalizer')
        self.register_buffer('meta_mean',torch.tensor(mean,dtype=torch.float32));self.register_buffer('meta_scale',torch.tensor(scale,dtype=torch.float32))

    def forward(self,inputs,metadata):
        if inputs.ndim!=4 or inputs.shape[1:]!=(3,32,32) or not inputs.is_floating_point() or not torch.isfinite(inputs).all():raise ValueError('Expected finite Nx3x32x32 RGB')
        if metadata.shape!=(len(inputs),4) or not metadata.is_floating_point() or not torch.isfinite(metadata).all():raise ValueError('Expected finite Nx4 proposal metadata')
        if not torch.isfinite(self.meta_scale).all() or torch.any(self.meta_scale<=0):raise ValueError('Invalid metadata scale')
        features=torch.cat([self.features(inputs).flatten(1),self.metadata((metadata-self.meta_mean)/self.meta_scale)],dim=1)
        logits=self.score_head(features);offsets=bounded_offsets(self.offset_head(features))
        if not torch.isfinite(logits).all():raise ValueError('Nonfinite class logits')
        return logits,offsets


def localization_loss(logits,offsets,labels,target_offsets):
    if logits.ndim!=2 or logits.shape[1]!=2 or not len(logits) or offsets.shape!=logits.shape or target_offsets.shape!=logits.shape or labels.shape!=(len(logits),):raise ValueError('Loss input shapes differ')
    if labels.dtype!=torch.long or not torch.isin(labels,torch.tensor([0,1],device=labels.device)).all():raise ValueError('Labels must be binary integer IDs')
    if not all(torch.isfinite(t).all() for t in (logits,offsets,target_offsets)):raise ValueError('Nonfinite loss inputs')
    positive=labels==1
    regression=F.smooth_l1_loss(offsets[positive]/RADIUS,target_offsets[positive]/RADIUS,beta=.25) if positive.any() else offsets.sum()*0
    return F.cross_entropy(logits,labels)+regression


def predict_localized(rgb,points,metadata,model):
    if not isinstance(model,LocalizationGate) or not all(torch.isfinite(t).all() for t in model.state_dict().values()) or torch.any(model.meta_scale<=0):raise ValueError('Expected finite LocalizationGate')
    context=reflected_context(rgb,points);metadata=np.asarray(metadata)
    if metadata.shape!=(len(context),4) or metadata.dtype.kind not in 'iuf' or not np.isfinite(metadata).all():raise ValueError('Expected finite Nx4 metadata')
    scores,offsets=[],[];model.eval()
    with torch.inference_mode():
        for start in range(0,len(context),256):
            x=torch.from_numpy(context[start:start+256,:32,:32].transpose(0,3,1,2).copy()).float()/255
            meta=torch.from_numpy(metadata[start:start+256].astype(np.float32))
            logits,delta=model(x,meta);scores.append(torch.softmax(logits,dim=1)[:,1].cpu().numpy());offsets.append(delta.cpu().numpy())
    score=np.concatenate(scores).astype(np.float64) if scores else np.empty(0,dtype=np.float64)
    delta=np.concatenate(offsets).astype(np.float64) if offsets else np.empty((0,2),dtype=np.float64)
    if not np.isfinite(score).all() or np.any(score<0) or np.any(score>1):raise ValueError('Invalid retention scores')
    return dict(scores=score,offsets=delta,corrected_xy=corrected_points(points,delta,rgb.shape[:2]))
