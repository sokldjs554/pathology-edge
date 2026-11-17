import torch
from torch import nn
from torch.nn import functional as F


def block(a, b):
    return nn.Sequential(nn.Conv2d(a, b, 3, padding=1), nn.ReLU(), nn.Conv2d(b, b, 3, padding=1), nn.ReLU())


class TinyUNet(nn.Module):
    """Small from-scratch baseline; no external/pretrained weights."""
    def __init__(self, width=8):
        super().__init__()
        self.e1 = block(3, width)
        self.e2 = block(width, width*2)
        self.bottom = block(width*2, width*4)
        self.d2 = block(width*6, width*2)
        self.d1 = block(width*3, width)
        self.head = nn.Conv2d(width, 1, 1)

    def forward(self, x):
        a = self.e1(x)
        b = self.e2(F.max_pool2d(a, 2))
        c = self.bottom(F.max_pool2d(b, 2))
        d = self.d2(torch.cat([F.interpolate(c, size=b.shape[-2:], mode='bilinear', align_corners=False), b], 1))
        e = self.d1(torch.cat([F.interpolate(d, size=a.shape[-2:], mode='bilinear', align_corners=False), a], 1))
        return self.head(e)


def loss_fn(logits, target):
    probability = torch.sigmoid(logits)
    dice = (2*(probability*target).sum((1,2,3))+1) / (probability.sum((1,2,3))+target.sum((1,2,3))+1)
    return F.binary_cross_entropy_with_logits(logits, target) + (1-dice).mean()
