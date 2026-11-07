"""One CPU training run; validation-only selection; frozen held-out evaluation."""
from pathlib import Path
from time import perf_counter
import hashlib
import json
import os
import platform
import resource
import subprocess
import sys
import cv2
import numpy as np
import torch
from PIL import Image, ImageDraw
from .data import load_image, load_mask, tissue_mask, check_split, sha256
from .model import TinyUNet, loss_fn
from .patches import grid, extract, stitch, boundary_mask
from .merge import components, deduplicate
from .metrics import binary_metrics, point_metrics


def dump(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False))


def environment():
    return dict(platform=platform.platform(), python=sys.version, torch=torch.__version__,
                numpy=np.__version__, opencv=cv2.__version__, cpu_count=os.cpu_count(),
                torch_threads=torch.get_num_threads(), cuda=torch.cuda.is_available(),
                cpu=Path('/proc/cpuinfo').read_text().split('model name')[1].split('\n')[0].strip(':\t ') if Path('/proc/cpuinfo').exists() else platform.processor())


def load_records(root):
    manifest = json.loads((Path(root)/'manifest.json').read_text())
    check_split(manifest['records'])
    for row in manifest['records']:
        if sha256(Path(root)/row['image']) != row['image_sha256'] or sha256(Path(root)/row['mask']) != row['mask_sha256']:
            raise ValueError('Image/label changed after manifest creation')
    return manifest['records']


def predict(model, image, mode='no_overlap', threshold=0.5, backend='python', threads=1):
    start = perf_counter()
    size, overlap = 128, 64 if mode == 'overlap' else 0
    if mode == 'full':
        patches = grid(image.shape[1], image.shape[0], image.shape[1], 0)
    else:
        patches = grid(image.shape[1], image.shape[0], size, overlap)
    tiles = extract(image, patches, backend, threads)
    valid = [tissue_mask(tile).mean() >= 0.01 for tile in tiles]
    probs = np.zeros(tiles.shape[:3], np.float32)
    model.eval()
    with torch.inference_mode():
        indices = [i for i, v in enumerate(valid) if v]
        for first in range(0, len(indices), 8):
            batch = indices[first:first+8]
            tensor = torch.from_numpy(tiles[batch].transpose(0,3,1,2).copy()).float()/255
            probs[batch] = model(tensor).sigmoid()[:,0].numpy()
    probability = stitch(probs, patches, image.shape[:2], weighted=mode == 'overlap')
    raw = []
    for i, (p, prob) in enumerate(zip(patches, probs)):
        part = prob[:p.valid_height, :p.valid_width]
        raw.extend(components(part >= threshold, part, i, (p.x, p.y)))
    merged, suppressed = deduplicate(raw) if mode == 'overlap' else (raw, [])
    elapsed = perf_counter()-start
    return dict(probability=probability, mask=probability >= threshold, raw=raw,
                objects=merged, suppressed=suppressed, seconds=elapsed,
                patch_count=len(patches), skipped_background=int(len(valid)-sum(valid)))


def classical(image, cutoff):
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    return (gray < cutoff) & (tissue_mask(image) > 0)


def train(root='data', output='artifacts', seed=20261107, epochs=16, steps=20):
    root, out = Path(root), Path(output)
    if (out/'evaluation.json').exists() or (out/'evaluation_lock.json').exists():
        raise RuntimeError('Held-out evaluation already exists. Start a new experiment directory; do not retune on test.')
    torch.set_num_threads(4)
    torch.manual_seed(seed)
    np.random.seed(seed)
    torch.use_deterministic_algorithms(True)
    cv2.setNumThreads(1)
    rng = np.random.default_rng(seed)
    records = load_records(root)
    train_rows = [r for r in records if r['split']=='train']
    val_rows = [r for r in records if r['split']=='validation']
    train_data = [(load_image(root/r['image']),load_mask(root/r['mask'])) for r in train_rows]
    val_data = [(load_image(root/r['image']),load_mask(root/r['mask'])) for r in val_rows]
    out.mkdir(parents=True, exist_ok=True)
    config = dict(seed=seed, epochs=epochs, steps_per_epoch=steps, batch_size=8, crop=128,
                  optimizer='Adam', learning_rate=0.001, loss='BCE + soft Dice', width=8,
                  augmentations=['horizontal/vertical flip','90 degree rotations'],
                  selection='maximum validation image-macro Dice over epochs and thresholds',
                  thresholds=[0.35,0.5,0.65], seam_radius=8, test_used_for_selection=False,
                  patch_size=128, overlap=64, merge_iou=0.3, merge_distance=8, min_component_area=12,
                  centroid_match_radius=12, manifest_sha256=sha256(root/'manifest.json'))
    dump(out/'protocol.json', config)
    model = TinyUNet()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    best, history = -1, []
    start = perf_counter()
    for epoch in range(epochs):
        model.train()
        losses = []
        for _ in range(steps):
            xs, ys = [], []
            for _ in range(8):
                image, mask = train_data[rng.integers(len(train_data))]
                y, x = rng.integers(0, image.shape[0]-127), rng.integers(0, image.shape[1]-127)
                a, b = image[y:y+128,x:x+128], mask[y:y+128,x:x+128]
                k = int(rng.integers(4))
                a, b = np.rot90(a,k), np.rot90(b,k)
                if rng.random()<0.5: a,b = a[:,::-1],b[:,::-1]
                if rng.random()<0.5: a,b = a[::-1],b[::-1]
                xs.append(a.transpose(2,0,1).copy()); ys.append(b[None].copy())
            inputs, targets = torch.from_numpy(np.stack(xs)).float()/255, torch.from_numpy(np.stack(ys)).float()
            optimizer.zero_grad(set_to_none=True)
            loss = loss_fn(model(inputs), targets)
            loss.backward(); optimizer.step()
            losses.append(float(loss.detach()))
        val_probs = [predict(model, a)['probability'] for a,_ in val_data]
        scores = {str(t):float(np.mean([binary_metrics(p>=t,b)['dice'] for p,(_,b) in zip(val_probs,val_data)])) for t in config['thresholds']}
        selected = max(scores, key=scores.get)
        score = scores[selected]
        entry = dict(epoch=epoch+1, train_loss=float(np.mean(losses)), validation_dice=scores)
        history.append(entry)
        if score>best:
            best, threshold, best_epoch = score, float(selected), epoch+1
            torch.save(model.state_dict(), out/'model.pt')
        print(json.dumps(entry), flush=True)
    classical_scores = {str(c):float(np.mean([binary_metrics(classical(a,c),b)['dice'] for a,b in val_data])) for c in [80,100,120,140,160,180]}
    classical_cutoff = int(max(classical_scores, key=classical_scores.get))
    report = dict(config=config, history=history, best_epoch=best_epoch, threshold=threshold,
                  best_validation_dice=best, classical_cutoff=classical_cutoff,
                  classical_validation_scores=classical_scores, seconds=perf_counter()-start,
                  parameter_count=sum(p.numel() for p in model.parameters()),
                  model_sha256=sha256(out/'model.pt'), environment=environment(),
                  train_images=len(train_rows), validation_images=len(val_rows))
    dump(out/'training.json', report)
    dump(out/'manifest.json', json.loads((root/'manifest.json').read_text()))
    return report


def evaluate_worker(root, output, mode, repeats=3):
    """Each mode runs in a fresh process; RSS is whole worker high-water mark."""
    root, out = Path(root), Path(output)
    torch.set_num_threads(4); cv2.setNumThreads(1)
    training = json.loads((out/'training.json').read_text())
    model = TinyUNet(); model.load_state_dict(torch.load(out/'model.pt',weights_only=True))
    records = load_records(root)
    warmup = next(r for r in records if r['split']=='validation')
    predict(model, load_image(root/warmup['image']), mode if mode!='classical' else 'no_overlap', training['threshold'])
    rows, payloads = [], {}
    for r in records:
        if r['split']!='test': continue
        image, target = load_image(root/r['image']), load_mask(root/r['mask'])
        timings=[]
        for _ in range(repeats):
            if mode=='classical':
                t0=perf_counter(); mask=classical(image,training['classical_cutoff'])
                objects=components(mask); elapsed=perf_counter()-t0
                result=dict(mask=mask,probability=mask.astype(np.float32),objects=objects,raw=objects,suppressed=[],seconds=elapsed,patch_count=1,skipped_background=0)
            else:
                result=predict(model,image,mode,training['threshold'])
            timings.append(result['seconds'])
        boundary = boundary_mask(target.shape)
        targets = components(target, min_area=1)
        metrics = {name:binary_metrics(result['mask'],target,region) for name,region in [('all',None),('boundary',boundary),('interior',~boundary)]}
        metrics['centroid_proxy'] = point_metrics([(o['x'],o['y']) for o in result['objects']], [(o['x'],o['y']) for o in targets])
        rows.append(dict(id=r['id'],group_id=r['group_id'],metrics=metrics,
                         median_seconds=float(np.median(timings)),timings_seconds=timings,
                         raw_count=len(result['raw']),merged_count=len(result['objects']),
                         suppressed_count=len(result['suppressed']),target_components=len(targets),
                         patch_count=result['patch_count'],skipped_background=result['skipped_background']))
        payloads[r['id']]=dict(objects=result['objects'],raw=result['raw'],suppressed=result['suppressed'])
        image_out = out/'predictions'/mode
        image_out.mkdir(parents=True,exist_ok=True)
        Image.fromarray((result['mask']*255).astype(np.uint8)).save(image_out/f'{r["id"]}.png')
        np.save(image_out/f'{r["id"]}.npy',result['probability'])
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform=='darwin': rss/=1024
    report=dict(mode=mode,rows=rows,macro_dice={k:float(np.mean([r['metrics'][k]['dice'] for r in rows])) for k in ['all','boundary','interior']},
                median_image_seconds=float(np.median([r['median_seconds'] for r in rows])),
                peak_process_rss_mib=rss/1024,environment=environment(),
                timing_scope='warm CPU; RGB extraction + tissue gate + forward + stitch + components + NMS; excludes disk I/O, scoring and model load',
                memory_scope='fresh worker absolute peak RSS including runtime/model, validation warmup, image I/O and scoring')
    dump(out/f'eval_{mode}.json',report)
    dump(out/f'objects_{mode}.json',payloads)


def evaluate(root='data', output='artifacts'):
    root, out = Path(root), Path(output)
    training=json.loads((out/'training.json').read_text())
    if sha256(out/'model.pt')!=training['model_sha256'] or sha256(root/'manifest.json')!=training['config']['manifest_sha256']:
        raise ValueError('Frozen model or split changed')
    lock=dict(model_sha256=training['model_sha256'],protocol=training['config'],threshold=training['threshold'])
    if (out/'evaluation_lock.json').exists() and json.loads((out/'evaluation_lock.json').read_text()) != lock:
        raise ValueError('Evaluation protocol changed after test was opened')
    if (out/'evaluation.json').exists():
        return json.loads((out/'evaluation.json').read_text())
    dump(out/'evaluation_lock.json',lock)
    modes=['classical','no_overlap','overlap','full']
    for mode in modes:
        subprocess.run([sys.executable,'-m','pathology_edge.cli','eval-worker','--data',str(root),'--output',str(out),'--mode',mode],check=True)
    reports={mode:json.loads((out/f'eval_{mode}.json').read_text()) for mode in modes}
    report=dict(methods=reports,model_sha256=training['model_sha256'],
                test_images=7,test_groups=2,confidence_interval=None,
                limitation='one seed, two held-out case groups; no clinical/external validation; centroid metrics use binary-mask component proxy')
    dump(out/'evaluation.json',report)
    return report


def export_demo(root='data', output='artifacts', dest='dist'):
    root,out,dest=Path(root),Path(output),Path(dest)
    assets=dest/'assets'; assets.mkdir(parents=True,exist_ok=True)
    evaluation=json.loads((out/'evaluation.json').read_text())
    training=json.loads((out/'training.json').read_text())
    object_data={m:json.loads((out/f'objects_{m}.json').read_text()) for m in ['no_overlap','overlap','full','classical']}
    samples=[]
    for r in load_records(root):
        if r['split']!='test': continue
        name=r['id']; image=load_image(root/r['image'])
        Image.fromarray(image).save(assets/f'{name}.png')
        Image.fromarray(load_mask(root/r['mask'])*255).save(assets/f'{name}_gt.png')
        methods={}
        for mode in object_data:
            mask=load_image(out/'predictions'/mode/f'{name}.png')[...,0]>0
            rgba=np.zeros((*mask.shape,4),np.uint8); rgba[mask]=[66,224,184,110]
            Image.fromarray(rgba).save(assets/f'{name}_{mode}.png')
            metrics=next(row for row in evaluation['methods'][mode]['rows'] if row['id']==name)
            methods[mode]=dict(**object_data[mode][name],**metrics,overlay=f'assets/{name}_{mode}.png')
        samples.append(dict(id=name,width=512,height=512,group_id=r['group_id'],image=f'assets/{name}.png',gt=f'assets/{name}_gt.png',methods=methods))
    delta=lambda s:s['methods']['overlap']['metrics']['all']['dice']-s['methods']['no_overlap']['metrics']['all']['dice']
    worst=min(samples,key=delta)['id']
    payload=dict(title='Pathology Edge',dataset='TNBC v1.1 · H&E · 512×512 PNG',license='CC BY 4.0',
                 source='https://doi.org/10.5281/zenodo.2579118',authors='Naylor, Walter, Laé, Reyal',
                 unit='provided PNG pixels (not WSI level-0)',model='TinyUNet · from scratch · CPU',
                 model_sha256=training['model_sha256'],threshold=training['threshold'],
                 training_seconds=training['seconds'],summary={m:{k:v for k,v in report.items() if k!='rows'} for m,report in evaluation['methods'].items()},
                 samples=samples,worst_delta_sample=worst,seed=training['config']['seed'],
                 limits=['H&E 핵 분할: Ki-67 양성률을 산출할 수 없음','WSI 전체·외부 데이터·임상 검증 미수행','단일 seed, 테스트 2개 케이스 그룹','검출 수와 F1은 연결 성분 기반 대리지표; 종양 세포 수 아님','겹침 병합은 근접한 다른 핵을 합치거나 조각을 남길 수 있음'])
    dump(dest/'results.json',payload)
    # A real output visualization, explicitly not a browser screenshot.
    sample=next(s for s in samples if s['id']==worst)
    canvas=Image.new('RGB',(1056,568),(18,25,34)); draw=ImageDraw.Draw(canvas)
    for i,mode in enumerate(['no_overlap','overlap']):
        base=Image.open(assets/f'{worst}.png').convert('RGBA')
        base=Image.alpha_composite(base,Image.open(assets/f'{worst}_{mode}.png'))
        canvas.paste(base.convert('RGB'),(8+i*528,40))
        draw.text((8+i*528,10),f'{worst} | {mode} | Dice {sample["methods"][mode]["metrics"]["all"]["dice"]:.4f}',fill='white')
        for k in [128,256,384]:
            draw.line([(8+i*528+k,40),(8+i*528+k,552)],fill=(255,185,70))
            draw.line([(8+i*528,40+k),(520+i*528,40+k)],fill=(255,185,70))
    canvas.save(out/'boundary_comparison.png')
    return payload
