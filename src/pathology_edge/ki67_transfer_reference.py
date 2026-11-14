"""Data-only palette amendment before external inference; no RGB/model changes."""
import io
import numpy as np
from PIL import Image
from .ki67_deepliif import segmentation_centers

PALETTE=np.array([[0,0,0],[255,0,0],[0,0,255],[0,255,0]],dtype=np.uint8)


def validate(mask):
    if not isinstance(mask,np.ndarray) or mask.dtype!=np.uint8 or mask.ndim!=3 or mask.shape[2]!=3 or not mask.size:raise ValueError('Expected nonempty uint8 RGB reference')


def normalize_reference(mask):
    validate(mask)
    colors,inverse,counts=np.unique(mask.reshape(-1,3),axis=0,return_inverse=True,return_counts=True)
    distance=np.max(np.abs(colors[:,None,:].astype(np.int16)-PALETTE[None,:,:].astype(np.int16)),axis=2)
    nearest=distance.argmin(1)
    if np.any(distance[np.arange(len(colors)),nearest]>2):raise ValueError('Reference color outside fixed2level palette tolerance')
    changes=[dict(from_color=c.tolist(),to_color=PALETTE[k].tolist(),pixels=int(n)) for c,k,n in zip(colors,nearest,counts) if not np.array_equal(c,PALETTE[k])]
    changes=[{'from':r['from_color'],'to':r['to_color'],'pixels':r['pixels']} for r in changes]
    clean=PALETTE[nearest[inverse]].reshape(mask.shape)
    return clean,dict(max_channel_tolerance=2,changed_pixels=sum(r['pixels'] for r in changes),colors=changes)


def independent_normalize(mask):
    validate(mask);clean=np.zeros_like(mask);assigned=np.zeros(mask.shape[:2],dtype=np.uint8)
    for color in ((0,0,0),(255,0,0),(0,0,255),(0,255,0)):
        belongs=np.all(np.abs(mask.astype(np.int16)-np.array(color,dtype=np.int16))<=2,axis=2)
        assigned+=belongs.astype(np.uint8);clean[belongs]=color
    if not np.all(assigned==1):raise ValueError('Independent palette assignment differs')
    return clean


def decode_reference(raw):
    image=Image.open(io.BytesIO(raw))
    if image.format!='PNG' or image.mode!='RGB' or image.size!=(3072,512):raise ValueError('Expected six native512 RGB PNG tiles')
    array=np.asarray(image);mask=array[:,2560:3072];clean,normalization=normalize_reference(mask)
    if not np.array_equal(clean,independent_normalize(mask)):raise ValueError('Independent normalized mask differs')
    xy,classes,reference=segmentation_centers(clean)
    return array[:,:512].copy(),xy,classes,reference,normalization,clean
