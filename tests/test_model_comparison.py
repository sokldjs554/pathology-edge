"""Guard data isolation, experiment preservation and checkpoint selection."""
import json
from pathlib import Path

import numpy as np
from PIL import Image
import pytest

from pathology_edge import model_comparison as comparison
from pathology_edge.data import sha256


@pytest.fixture
def data(tmp_path):
    root = tmp_path / 'data'
    root.mkdir()
    rows = []
    for i, split in enumerate(('train', 'validation', 'test')):
        image, mask = root / f'{split}.png', root / f'{split}-mask.png'
        if split == 'test':
            # Hashable but deliberately not decodable: test pixels must never be read.
            image.write_bytes(b'not a test image to decode')
            mask.write_bytes(b'not a test target to decode')
        else:
            size = 128 if split == 'train' else 256
            rgb = np.full((size, size, 3), [150, 80, 120], np.uint8)
            target = np.zeros((size, size), np.uint8)
            target[32:140, 50:100] = 255
            Image.fromarray(rgb).save(image)
            Image.fromarray(target).save(mask)
        rows.append(dict(id=str(i), group_id=str(i), split=split,
                         image=image.name, mask=mask.name,
                         image_sha256=sha256(image), mask_sha256=sha256(mask)))
    (root / 'manifest.json').write_text(json.dumps({'records': rows}))
    return root


def test_selection_uses_all_thresholds_and_keeps_first_tie():
    history = [dict(epoch=1, train_loss=.8, validation_dice={'0.35': .7, '0.5': .7, '0.65': .5}),
               dict(epoch=2, train_loss=.6, validation_dice={'0.35': .5, '0.5': .6, '0.65': .7})]
    assert comparison.select_best(history, [.35, .5, .65]) == (1, .35, .7)
    history[1]['validation_dice']['0.65'] = .8
    assert comparison.select_best(history, [.35, .5, .65]) == (2, .65, .8)


@pytest.mark.parametrize('score', [float('nan'), float('inf'), -.1, 1.1, True])
def test_selection_rejects_invalid_validation_score(score):
    with pytest.raises(ValueError):
        comparison.select_best([dict(epoch=1, train_loss=.8, validation_dice={'0.5': score})], [.5])


def test_existing_output_never_changes(data, tmp_path):
    out = tmp_path / 'existing'
    out.mkdir()
    saved = out / 'model.pt'
    saved.write_bytes(b'preserve model')
    with pytest.raises(FileExistsError):
        comparison.train_one(data, out, 'tiny_unet', epochs=1, steps=1)
    assert saved.read_bytes() == b'preserve model'


def test_invalid_architecture_does_not_start(data, tmp_path):
    out = tmp_path / 'never-created'
    with pytest.raises(ValueError, match='architecture'):
        comparison.train_one(data, out, 'typo', epochs=1, steps=1)
    assert not out.exists()


def test_cnn_training_never_decodes_test_and_saves_selected_masks(data, tmp_path):
    out = tmp_path / 'cnn'
    report = comparison.train_one(data, out, 'tiny_unet', epochs=1, steps=1)
    assert report['train_images'] == report['validation_images'] == 1
    assert report['test_evaluation_run'] is False
    assert report['model_sha256'] == sha256(out / 'model.pt')
    assert report['config']['validation_mode'] == 'no_overlap'
    assert report['validation']['rows'][0]['id'] == '1'
    assert len(list((out / 'predictions').glob('*.npy'))) == 1
    assert not (out / 'evaluation.json').exists()
    assert (out / 'source-hashes.json').exists()
    best = comparison.select_best(report['history'], report['config']['thresholds'])
    assert best == (report['best_epoch'], report['threshold'], report['best_validation_dice'])


def test_paired_architectures_share_crop_trace(data, tmp_path):
    a = comparison.train_one(data, tmp_path / 'a', 'tiny_unet', epochs=1, steps=1)
    b = comparison.train_one(data, tmp_path / 'b', 'small_vit', epochs=1, steps=1)
    assert a['augmentation_trace_sha256'] == b['augmentation_trace_sha256']
    assert a['config'] == b['config']
    assert a['parameter_count'] != b['parameter_count']
    assert b['model_spec']['patch_size'] == 8
    assert b['test_evaluation_run'] is False
