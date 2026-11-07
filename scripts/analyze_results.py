"""Descriptive analysis of frozen predictions, never model/threshold selection."""
import json
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw
from pathology_edge.data import load_image,load_mask
from pathology_edge.patches import boundary_mask
from pathology_edge.merge import components
from pathology_edge.metrics import point_metrics

out=Path('artifacts');data=Path('data')
manifest=json.loads((out/'manifest.json').read_text())
report=json.loads((out/'evaluation.json').read_text())
objects=json.loads((out/'objects_overlap.json').read_text())
rows=[];quality=[]
for r in manifest['records']:
    image=load_image(data/r['image']);target=load_mask(data/r['mask'])
    hsv=cv2.cvtColor(image,cv2.COLOR_RGB2HSV)
    quality.append(dict(id=r['id'],split=r['split'],group=r['group_id'],
                        foreground_fraction=float(target.mean()),mean_saturation=float(hsv[...,1].mean()),
                        grayscale_std=float(cv2.cvtColor(image,cv2.COLOR_RGB2GRAY).std())))
    if r['split']!='test':continue
    name=r['id'];boundary=boundary_mask(target.shape)
    full=np.load(out/'predictions'/'full'/f'{name}.npy')
    row=dict(id=name,group=r['group_id'])
    for mode in ['no_overlap','overlap']:
        p=np.load(out/'predictions'/mode/f'{name}.npy')
        row[mode]=dict(boundary_mae_vs_full=float(np.abs(p-full)[boundary].mean()),
                       interior_mae_vs_full=float(np.abs(p-full)[~boundary].mean()))
    centers=[(o['x'],o['y']) for o in components(target,min_area=1)]
    for key in ['raw','objects']:
        row[f'centroid_proxy_{key}']=point_metrics([(o['x'],o['y']) for o in objects[name][key]],centers)
    rows.append(row)
group_dice={}
for mode in ['no_overlap','overlap']:
    group_dice[mode]={}
    for group in ['10','11']:
        rs=[r for r in report['methods'][mode]['rows'] if r['group_id']==group]
        group_dice[mode][group]={region:float(np.mean([r['metrics'][region]['dice'] for r in rs])) for region in ['all','boundary','interior']}
analysis=dict(per_image=rows,group_dice=group_dice,quality=quality,
              caution='Full image is a consistency reference, not ground truth. CC centroids are proxy targets. Descriptive analysis after frozen test, no retuning.')
(out/'analysis.json').write_text(json.dumps(analysis,indent=2))
for name in ['10_3','10_4','11_2']:
    row=next(r for r in manifest['records'] if r['id']==name)
    original=Image.fromarray(load_image(data/row['image'])).convert('RGBA')
    truth=load_mask(data/row['mask']).astype(bool)
    canvas=Image.new('RGB',(1536,550),(20,29,36));draw=ImageDraw.Draw(canvas)
    for i,mode in enumerate(['ground_truth','no_overlap','overlap']):
        mask=truth if i==0 else np.asarray(Image.open(out/'predictions'/mode/f'{name}.png'))>0
        layer=np.zeros((512,512,4),np.uint8)
        if i==0:layer[mask]=[199,155,255,120]
        else:
            layer[mask&truth]=[67,224,180,120]
            layer[mask&~truth]=[255,60,100,170]
            layer[~mask&truth]=[255,195,55,170]
        canvas.paste(Image.alpha_composite(original,Image.fromarray(layer)).convert('RGB'),(i*512,38))
        draw.text((i*512+8,10),f'{name} | {mode} | green TP / pink FP / gold FN' if i else f'{name} | ground truth: purple',fill='white')
    canvas.save(out/f'error_{name}.png')
print('Saved descriptive group, seam-consistency, merge-proxy and error-image analysis.')
