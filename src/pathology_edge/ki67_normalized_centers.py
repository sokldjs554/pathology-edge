"""Separate normalized point detector; historical CenterDetector is unchanged."""
import torch
from .ki67_centers import CenterDetector
from .model import TinyUNet


class NormalizedCenterDetector(CenterDetector):
    def __init__(self, width=16):
        if type(width) is not int or width not in (4,16):
            raise ValueError('Registered widths are integer4 or16')
        TinyUNet.__init__(self,width=width)
        self.width=width
        for name in ('e1','e2','bottom','d2','d1'):
            original=getattr(self,name);channels=original[0].out_channels
            setattr(self,name,torch.nn.Sequential(
                original[0],torch.nn.GroupNorm(max(1,channels//4),channels),torch.nn.LeakyReLU(.1),
                original[2],torch.nn.GroupNorm(max(1,channels//4),channels),torch.nn.LeakyReLU(.1)))
        torch.nn.init.constant_(self.head.bias,-2.19)
