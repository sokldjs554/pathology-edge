"""Isolated, from-scratch CNN/ViT comparison; never evaluates test images."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import resource
import sys
from time import perf_counter

import cv2
import numpy as np
import torch

from . import learner_losses
from .data import load_image, load_mask, sha256
from .experiment import dump, environment, load_records, predict, _training_loss
from .metrics import binary_metrics
from .model import TinyUNet
from .patches import boundary_mask
from .vit import SmallViTSegmenter

ARCHITECTURES = ('tiny_unet', 'small_vit')


def select_best(history, thresholds):
    """Maximum image-macro Dice; ties retain first epoch then first threshold."""
    if not history or not thresholds:
        raise ValueError('Nonempty history and thresholds required')
    best = None
    for epoch, entry in enumerate(history, 1):
        if entry['epoch'] != epoch or set(entry['validation_dice']) != {str(t) for t in thresholds}:
            raise ValueError('Invalid epoch or threshold sequence')
        loss = entry['train_loss']
        if isinstance(loss, bool) or not math.isfinite(loss) or loss < 0:
            raise ValueError('Invalid training loss')
        for threshold in thresholds:
            score = entry['validation_dice'][str(threshold)]
            if isinstance(score, bool) or not math.isfinite(score) or not 0 <= score <= 1:
                raise ValueError('Invalid validation score')
            if best is None or score > best[2]:
                best = (epoch, threshold, score)
    return best


def source_hashes():
    return {p.name: sha256(p) for p in sorted(Path(__file__).parent.glob('*.py'))}


def validation_report(model, val_rows, val_data, threshold, out):
    """Save probabilities and region metrics from the selected checkpoint."""
    predict(model, val_data[0][0], threshold=threshold)  # one untimed warmup
    rows = []
    (out / 'predictions').mkdir()
    for index, (row, (image, target)) in enumerate(zip(val_rows, val_data)):
        times = []
        for _ in range(3):
            result = predict(model, image, threshold=threshold)
            times.append(result['seconds'])
        probability = result['probability']
        if not np.isfinite(probability).all():
            raise ValueError('Nonfinite validation prediction')
        path = out / 'predictions' / f'{index:02d}.npy'
        np.save(path, probability, allow_pickle=False)
        boundary = boundary_mask(target.shape)
        metrics = {name: binary_metrics(result['mask'], target, region)
                   for name, region in [('all', None), ('boundary', boundary), ('interior', ~boundary)]}
        rows.append(dict(id=row['id'], group_id=row['group_id'], metrics=metrics,
                         prediction=path.relative_to(out).as_posix(), prediction_sha256=sha256(path),
                         timings_seconds=times, median_seconds=float(np.median(times)),
                         patch_count=result['patch_count']))
    return dict(rows=rows,
                macro_dice={name: float(np.mean([r['metrics'][name]['dice'] for r in rows]))
                            for name in ('all', 'boundary', 'interior')},
                median_image_seconds=float(np.median([r['median_seconds'] for r in rows])),
                timing_scope='CPU no_overlap pipeline: RGB extraction, tissue gate, forward, stitch, components; '
                             'excludes model load, disk I/O and scoring. One warmup; three repeats/image, '
                             'median per image then median across validation images. No NMS in no_overlap.')


def train_one(data, output, architecture, *, seed=20261113, epochs=16, steps=20):
    """Train one architecture into a new directory; preserve existing results."""
    if architecture not in ARCHITECTURES:
        raise ValueError('Unknown architecture')
    if any(type(v) is not int or v <= 0 for v in (seed, epochs, steps)):
        raise ValueError('Positive integer seed, epochs and steps required')
    root, out = Path(data).resolve(), Path(output).resolve()
    if out.exists():
        raise FileExistsError(out)
    if out.is_relative_to(root):
        raise ValueError('Output must be outside input data')
    records = load_records(root)  # all files hashed; only train/validation decoded below
    train_rows = [r for r in records if r['split'] == 'train']
    val_rows = [r for r in records if r['split'] == 'validation']
    if not train_rows or not val_rows:
        raise ValueError('Training and validation images required')
    train_data = [(load_image(root/r['image']), load_mask(root/r['mask'])) for r in train_rows]
    val_data = [(load_image(root/r['image']), load_mask(root/r['mask'])) for r in val_rows]
    for image, target in train_data + val_data:
        if image.shape[:2] != target.shape or min(target.shape) < 128:
            raise ValueError('Aligned masks and images at least 128px required')

    torch.set_num_threads(4)
    cv2.setNumThreads(1)
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True)
    # Crop RNG does not depend on architecture-specific parameter initialization.
    rng = np.random.default_rng(seed)
    selected_loss, loss_label = _training_loss('learner_dice')
    config = dict(seed=seed, epochs=epochs, steps_per_epoch=steps, batch_size=8, crop=128,
                  optimizer='Adam', learning_rate=.001, loss=loss_label, loss_mode='learner_dice',
                  loss_source_sha256=sha256(learner_losses.__file__),
                  augmentations=['horizontal/vertical flip', '90 degree rotations'],
                  thresholds=[.35, .5, .65], validation_mode='no_overlap', patch_size=128,
                  overlap=0, seam_radius=8, min_component_area=12, torch_threads=4,
                  selection='maximum validation image-macro Dice over epochs and thresholds; first tie',
                  test_used_for_selection=False, pretrained=False, manifest_sha256=sha256(root/'manifest.json'))
    before = source_hashes()
    out.mkdir(parents=True)
    dump(out/'protocol.json', config)
    dump(out/'source-hashes.json', before)
    dump(out/'manifest.json', json.loads((root/'manifest.json').read_text()))
    model = TinyUNet() if architecture == 'tiny_unet' else SmallViTSegmenter()
    model_spec = dict(width=8) if architecture == 'tiny_unet' else model.config
    optimizer = torch.optim.Adam(model.parameters(), lr=.001)
    trace = hashlib.sha256()
    best_score, history = -1., []
    start = perf_counter()
    for epoch in range(1, epochs + 1):
        model.train()
        losses = []
        for _ in range(steps):
            xs, ys = [], []
            for _ in range(8):
                index = int(rng.integers(len(train_data)))
                image, mask = train_data[index]
                y, x = int(rng.integers(image.shape[0]-127)), int(rng.integers(image.shape[1]-127))
                k = int(rng.integers(4))
                horizontal, vertical = rng.random() < .5, rng.random() < .5
                trace.update(json.dumps([train_rows[index]['id'], y, x, k, horizontal, vertical]).encode()+b'\n')
                a, b = np.rot90(image[y:y+128, x:x+128], k), np.rot90(mask[y:y+128, x:x+128], k)
                if horizontal:
                    a, b = a[:, ::-1], b[:, ::-1]
                if vertical:
                    a, b = a[::-1], b[::-1]
                xs.append(a.transpose(2, 0, 1).copy())
                ys.append(b[None].copy())
            inputs = torch.from_numpy(np.stack(xs)).float()/255
            targets = torch.from_numpy(np.stack(ys)).float()
            optimizer.zero_grad(set_to_none=True)
            loss = selected_loss(model(inputs), targets)
            if not torch.isfinite(loss):
                raise ValueError('Nonfinite training loss')
            loss.backward()
            optimizer.step()
            losses.append(float(loss.detach()))
        probabilities = [predict(model, a)['probability'] for a, _ in val_data]
        if not all(np.isfinite(p).all() for p in probabilities):
            raise ValueError('Nonfinite validation prediction')
        scores = {str(t): float(np.mean([binary_metrics(p >= t, b)['dice']
                                        for p, (_, b) in zip(probabilities, val_data)]))
                  for t in config['thresholds']}
        entry = dict(epoch=epoch, train_loss=float(np.mean(losses)), validation_dice=scores)
        history.append(entry)
        _, _, score = select_best(history, config['thresholds'])
        if score > best_score:
            best_score = score
            torch.save(model.state_dict(), out/'model.pt')
        dump(out/'history.json', history)
        print(json.dumps(dict(architecture=architecture, **entry)), flush=True)
    seconds = perf_counter() - start
    best_epoch, threshold, best = select_best(history, config['thresholds'])
    model.load_state_dict(torch.load(out/'model.pt', weights_only=True, map_location='cpu'))
    validation = validation_report(model, val_rows, val_data, threshold, out)
    if not math.isclose(validation['macro_dice']['all'], best, abs_tol=1e-12):
        raise ValueError('Reloaded checkpoint differs from selected validation score')
    if source_hashes() != before or sha256(root/'manifest.json') != config['manifest_sha256']:
        raise ValueError('Sources or manifest changed during training')
    load_records(root)  # detect dataset mutation, including test hashes, without test decoding
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024**2 if sys.platform == 'darwin' else 1024)
    report = dict(architecture=architecture, model_spec=model_spec, config=config, history=history,
                  best_epoch=best_epoch, threshold=threshold, best_validation_dice=best,
                  seconds=seconds, training_time_scope='Training and epoch validation; excludes final detailed validation and model/data load',
                  parameter_count=sum(p.numel() for p in model.parameters()),
                  model_sha256=sha256(out/'model.pt'), environment=environment(),
                  train_images=len(train_rows), validation_images=len(val_rows),
                  train_groups=len({r['group_id'] for r in train_rows}),
                  validation_groups=len({r['group_id'] for r in val_rows}),
                  augmentation_trace_sha256=trace.hexdigest(), validation=validation,
                  peak_process_rss_mib=rss, memory_scope='Absolute whole-worker high-water RSS including training and validation',
                  test_evaluation_run=False)
    dump(out/'training.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--architecture', required=True, choices=ARCHITECTURES)
    args = parser.parse_args()
    train_one(args.data, args.output, args.architecture)


if __name__ == '__main__':
    main()
