"""Frozen ImageNet features and native-resolution point decoder.

SqueezeNet1.1 feature layout/Fire adapted from torchvision3ac97aa, BSD3Clause;
see third_party/torchvision-SQUEEZENET-LICENSE. No torchvision binary dependency.
"""
from collections import Counter
import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

WEIGHT_SHA256='b8a52dc049b60e4b6ab68ad0df457362afab8b6304b2febdc1650a5dab4d7e7b'


class Fire(nn.Module):
    def __init__(self,inputs,squeeze,expand):
        super().__init__()
        self.squeeze=nn.Conv2d(inputs,squeeze,1)
        self.expand1x1=nn.Conv2d(squeeze,expand,1)
        self.expand3x3=nn.Conv2d(squeeze,expand,3,padding=1)

    def forward(self,x):
        x=F.relu(self.squeeze(x))
        return torch.cat((F.relu(self.expand1x1(x)),F.relu(self.expand3x3(x))),1)


def squeeze_features():
    features=nn.Sequential(nn.Conv2d(3,64,3,stride=2),nn.ReLU(),nn.MaxPool2d(3,2,ceil_mode=True),
        Fire(64,16,64),Fire(128,16,64),nn.MaxPool2d(3,2,ceil_mode=True),
        Fire(128,32,128),Fire(256,32,128),nn.MaxPool2d(3,2,ceil_mode=True),
        Fire(256,48,192),Fire(384,48,192),Fire(384,64,256),Fire(512,64,256))
    for m in features.modules():
        if isinstance(m,nn.Conv2d):nn.init.kaiming_uniform_(m.weight);nn.init.zeros_(m.bias)
    return features


def block(a,b,k=3):
    return nn.Sequential(nn.Conv2d(a,b,k,padding=k//2),nn.GroupNorm(max(1,b//4),b),nn.LeakyReLU(.1))


class DenseDecoder(nn.Module):
    def __init__(self):
        super().__init__()
        self.lateral=nn.ModuleList([block(c,16,1) for c in (64,128,256,512)])
        self.rgb=block(3,8)
        self.output=nn.Sequential(block(24,16),block(16,16),nn.Conv2d(16,1,1))
        nn.init.constant_(self.output[-1].bias,-2.19)

    def forward(self,rgb,features):
        x=self.lateral[-1](features[-1])
        for i in (2,1,0):
            x=F.interpolate(x,size=features[i].shape[-2:],mode='bilinear',align_corners=False)+self.lateral[i](features[i])
        x=F.interpolate(x,size=rgb.shape[-2:],mode='bilinear',align_corners=False)
        return self.output(torch.cat((x,self.rgb(rgb)),1))


class TransferCenterDetector(nn.Module):
    def __init__(self,feature_state=None):
        super().__init__()
        self.features=squeeze_features()
        # Always initialize decoder in the same RNG position, independent of arm.
        self.decoder=DenseDecoder()
        if feature_state is not None:
            if not isinstance(feature_state,dict) or not all(isinstance(v,torch.Tensor) and torch.isfinite(v).all() for v in feature_state.values()):
                raise ValueError('Expected finite feature state')
            self.features.load_state_dict(feature_state,strict=True)
        self.features.requires_grad_(False)
        self.register_buffer('mean',torch.tensor([.485,.456,.406])[None,:,None,None])
        self.register_buffer('std',torch.tensor([.229,.224,.225])[None,:,None,None])

    def forward(self,x):
        if (not isinstance(x,torch.Tensor) or x.ndim!=4 or x.shape[0]<1 or x.shape[1]!=3 or min(x.shape[2:])<17
            or not x.is_floating_point() or not torch.isfinite(x).all() or torch.any(x<0) or torch.any(x>1)):
            raise ValueError('Expected finite RGB Bx3xHxW in [0,1], H/W>=17')
        features=[]
        with torch.no_grad():
            h=(x-self.mean)/self.std
            for i,layer in enumerate(self.features):
                h=layer(h)
                if i in (1,4,7,12):features.append(h)
        return self.decoder(x,features)


def balanced_probabilities(records):
    if (not isinstance(records,list) or not records or
        any(not isinstance(r,dict) or r.get('split')!='train' or not isinstance(r.get('case_id'),str) or not r['case_id'].strip() for r in records)):
        raise ValueError('Nonempty training-only case records required')
    counts=Counter(r['case_id'] for r in records)
    return np.array([1/(len(counts)*counts[r['case_id']]) for r in records],dtype=np.float64)
