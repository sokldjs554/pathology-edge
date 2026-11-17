"""Dense Gaussian fitting objectives; scores are not calibrated probabilities."""
import math
import torch
from torch.nn import functional as F

MODES=('soft_mse','soft_bce')


def supervision_loss(logits:torch.Tensor,target:torch.Tensor,mode:str)->torch.Tensor:
    if not isinstance(logits,torch.Tensor) or not isinstance(target,torch.Tensor):
        raise ValueError('Expected tensor logits and targets')
    if (logits.ndim!=4 or logits.shape[1]!=1 or min(logits.shape)<=0 or logits.shape!=target.shape
        or not logits.is_floating_point() or not target.is_floating_point()
        or logits.dtype!=target.dtype or logits.device!=target.device):
        raise ValueError('Expected same floating Bx1xHxW dtype/device')
    if not torch.isfinite(logits).all() or not torch.isfinite(target).all() or torch.any(target<0) or torch.any(target>1):
        raise ValueError('Expected finite logits and targets in [0,1]')
    if not isinstance(mode,str) or mode not in MODES:raise ValueError('Unknown dense objective')
    axes=(1,2,3);positive=target.sum(axes).clamp_min(1);negative=(1-target).sum(axes).clamp_min(1)
    if mode=='soft_mse':
        squared=(torch.sigmoid(logits)-target).square()
        per_image=(squared*target).sum(axes)/positive+(squared*(1-target)).sum(axes)/negative
    else:
        per_image=(F.softplus(-logits)*target).sum(axes)/positive+(F.softplus(logits)*(1-target)).sum(axes)/negative
    loss=per_image.mean()
    if not torch.isfinite(loss):raise ValueError('Nonfinite dense loss')
    return loss


def choose_loss(reports:dict)->dict:
    """A fitting diagnostic can select a hypothesis, never establish validation success."""
    if not isinstance(reports,dict) or set(reports)!={'focal',*MODES}:raise ValueError('Require three fitting arms')
    expected={(t,d) for t in (.01,.02,.03,.05,.075,.1,.15,.2,.3,.5,.7,.9) for d in (4,6,8)}
    best={};cases=None
    for mode,r in reports.items():
        if r.get('mode')!=mode or r.get('training_images')!=120 or r.get('heldout_inference_images')!=0:
            raise ValueError('Expected fixed train-only120 fitting run')
        trials=r.get('trials',[])
        if len(trials)!=36 or {(t['config']['threshold'],t['config']['min_distance']) for t in trials}!=expected:
            raise ValueError('Fitting decoder grid changed')
        for t in trials:
            current=set(t['cases'])
            if cases is None:cases=current
            if len(current)!=15 or current!=cases:raise ValueError('Training case membership changed')
            values=[t['case_macro_f1'],t['case_macro_recall'],*t['tumor_recalls']]
            if len(values)!=4 or any(not math.isfinite(v) or not 0<=v<=1 for v in values):raise ValueError('Invalid fitting scores')
        best[mode]=max(trials,key=lambda t:(t['case_macro_f1'],t['case_macro_recall'],t['config']['threshold'],t['config']['min_distance']))
        if r.get('best')!=best[mode]:raise ValueError('Reported fitting best differs')
    reference=best['focal'];criteria={}
    for mode in MODES:
        b=best[mode]
        criteria[mode]=dict(f1_gain=b['case_macro_f1']-reference['case_macro_f1']>=.03-1e-12,
                            positive_tumor_recall_noninferior=b['tumor_recalls'][0]>=reference['tumor_recalls'][0])
    eligible=[m for m in MODES if all(criteria[m].values())]
    selected=max(eligible,key=lambda m:(best[m]['case_macro_f1'],best[m]['case_macro_recall'],-MODES.index(m))) if eligible else None
    return dict(selected_loss=selected,best_by_mode=best,criteria=criteria,scope='Training fit diagnostic only; not heldout improvement')
