"""Pinned TNBC v1.1 ingestion; split before sampling subpatches."""
from pathlib import Path
import hashlib
import json
import urllib.request
import zipfile
import cv2
import numpy as np
from PIL import Image

URL = 'https://zenodo.org/api/records/2579118/files/TNBC_NucleiSegmentation.zip/content'
MD5 = '1605712a752b201b57eacc8f866adb4f'


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def prepare(root='data', archive=None):
    root = Path(root)
    root.mkdir(exist_ok=True, parents=True)
    archive = Path(archive) if archive else root / 'TNBC_NucleiSegmentation.zip'
    if not archive.exists():
        with urllib.request.urlopen(URL, timeout=120) as response, archive.open('wb') as out:
            while block := response.read(1024 * 1024):
                out.write(block)
    if hashlib.md5(archive.read_bytes()).hexdigest() != MD5:
        raise ValueError('Archive checksum mismatch; do not use an unverified version')
    target = root / 'raw'
    with zipfile.ZipFile(archive) as z:
        for member in z.infolist():
            dest = (target / member.filename).resolve()
            if not dest.is_relative_to(target.resolve()):
                raise ValueError('Unsafe archive path')
        z.extractall(target)
    records = []
    for path in sorted((target / 'TNBC_dataset').glob('Slide_*/*.png')):
        group = path.parent.name.removeprefix('Slide_')
        label = path.parent.parent / f'GT_{group}' / path.name
        image = load_image(path)
        mask = load_mask(label)
        if image.shape[:2] != mask.shape or not set(np.unique(mask)).issubset({0, 1}):
            raise ValueError(f'Invalid image-mask pair: {path}')
        split = 'train' if int(group) <= 7 else 'validation' if int(group) <= 9 else 'test'
        records.append(dict(id=path.stem, group_id=group, split=split,
                            image=str(path.relative_to(root)), mask=str(label.relative_to(root)),
                            image_sha256=sha256(path), mask_sha256=sha256(label),
                            width=image.shape[1], height=image.shape[0],
                            foreground_fraction=float(mask.mean()),
                            source_level=0, downsample=1.0, mpp=None, objective_power=None,
                            origin_xy=[0, 0], unit='provided_png_pixels'))
    if len(records) != 50:
        raise ValueError(f'Expected 50 paired images, got {len(records)}')
    check_split(records)
    manifest = dict(dataset='TNBC v1.1', doi='10.5281/zenodo.2579118',
                    license='CC-BY-4.0', archive_md5=MD5, archive_sha256=sha256(archive),
                    split_rule='Slide_01..07 train; 08..09 validation; 10..11 test',
                    group_caveat='Slide folders used as case groups; no independent patient registry supplied',
                    records=records)
    (root / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    return manifest


def check_split(records):
    """Reject missing IDs, duplicate samples, case groups or bytes crossing splits."""
    groups, hashes, ids = {}, {}, set()
    if not records:
        raise ValueError('Empty manifest')
    for r in records:
        if not r.get('id') or not r.get('group_id') or not r.get('image_sha256'):
            raise ValueError('Missing sample/group/hash')
        if r['split'] not in {'train', 'validation', 'test'}:
            raise ValueError('Unknown split')
        if r['id'] in ids:
            raise ValueError('Duplicate sample ID')
        ids.add(r['id'])
        for seen, key in [(groups, r['group_id']), (hashes, r['image_sha256'])]:
            if key in seen and seen[key] != r['split']:
                raise ValueError(f'Split leakage: {key}')
            seen[key] = r['split']
    return True


def load_image(path):
    return np.asarray(Image.open(path).convert('RGB')).copy()


def load_mask(path):
    a = np.asarray(Image.open(path).convert('L'))
    if not set(np.unique(a)).issubset({0, 255}):
        raise ValueError('TNBC mask must contain only 0 and 255')
    return (a > 0).astype(np.uint8)


def tissue_mask(image):
    hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
    # Conservative background gate. This is not a tumor classifier.
    return ((hsv[..., 1] > 15) & (hsv[..., 2] < 250)).astype(np.uint8)
