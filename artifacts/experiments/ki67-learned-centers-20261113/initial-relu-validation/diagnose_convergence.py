import json
from pathlib import Path
import numpy as np
import torch
from pathology_edge.ki67_centers import CenterDetector,center_target,center_focal_loss
from pathology_edge.ki67_experiment import load_sample

torch.set_num_threads(2)
root=Path('work/learned-centers-run-20261113')
p=json.loads((root/'protocol.json').read_text())
rows=json.loads((Path(p['parent'])/'source-manifest.json').read_text())
chosen=[r for split in ('train','validation') for r in [x for x in rows if x['split']==split][:8]]
rgb=[];targets=[]
for r in chosen:
    image,points,_=load_sample(p['data_dir'],r)
    rgb.append(image);targets.append(center_target(points,image.shape[:2]))
x=torch.from_numpy(np.stack(rgb).transpose(0,3,1,2).copy()).float()/255
y=torch.from_numpy(np.stack(targets)[:,None])
out=[]
for seed in p['seeds']:
    for variant in ('selected','selected_leaky_diagnostic'):
        m=CenterDetector()
        m.load_state_dict(torch.load(root/f'detector-{seed}.pt',weights_only=True))
        if variant!='selected':
            for module in m.modules():
                if isinstance(module,torch.nn.Sequential):
                    for name,child in list(module.named_children()):
                        if isinstance(child,torch.nn.ReLU):module[int(name)]=torch.nn.LeakyReLU(.1)
        activations={};hooks=[]
        for name in ('e1','e2','bottom','d2','d1'):
            def hook(module,args,value,n=name):
                a=value.detach();activations[n]={'zero_fraction':float((a==0).float().mean()),'min':float(a.min()),'max':float(a.max()),'std':float(a.std())}
            hooks.append(getattr(m,name).register_forward_hook(hook))
        logits=m(x);loss=center_focal_loss(logits,y);loss.backward();heat=logits.detach().sigmoid()
        out.append({'seed':seed,'variant':variant,'sample_splits':[r['split'] for r in chosen],
          'probability_min':float(heat.min()),'probability_max':float(heat.max()),'probability_std':float(heat.std()),
          'loss':float(loss.detach()),'activations':activations,
          'weight_gradient_l1':{n:float(v.grad.abs().sum()) for n,v in m.named_parameters() if n.endswith('weight')},
          'optimizer_steps':0,'test_or_external_used':False})
        for h in hooks:h.remove()
path=Path('work/learned-centers-20261113/convergence-diagnostic.json')
path.write_text(json.dumps(out,indent=2)+'\n')
for r in out:print(json.dumps({k:r[k] for k in ('seed','variant','probability_max','probability_std','loss','activations','weight_gradient_l1')}))
