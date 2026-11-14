from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class Patch:
    x: int
    y: int
    size: int
    valid_width: int
    valid_height: int
    source_level: int = 0
    downsample: float = 1.0
    coordinate_unit: str = 'provided_png_pixels'


def grid(width, height, size=128, overlap=0):
    if min(width, height, size) <= 0 or not 0 <= overlap < size:
        raise ValueError('Positive dimensions and 0 <= overlap < size required')
    step = size - overlap
    # Regular grid, trailing patches white padded; no surprise shifted last tile.
    return [Patch(x, y, size, min(size, width-x), min(size, height-y))
            for y in range(0, height, step) for x in range(0, width, step)]


def extract_python(image, patches):
    image = np.asarray(image)
    if image.ndim != 3 or image.shape[2] != 3 or image.dtype != np.uint8:
        raise ValueError('Expected uint8 RGB HWC')
    if not patches:
        return np.empty((0, 0, 0, 3), dtype=np.uint8)
    size = patches[0].size
    out = np.full((len(patches), size, size, 3), 255, dtype=np.uint8)
    for i, p in enumerate(patches):
        if p.size != size or p.x < 0 or p.y < 0 or p.x >= image.shape[1] or p.y >= image.shape[0]:
            raise ValueError('Invalid patch geometry')
        h, w = min(size, image.shape[0]-p.y), min(size, image.shape[1]-p.x)
        out[i, :h, :w] = image[p.y:p.y+h, p.x:p.x+w]
    return out


def extract(image, patches, backend='python', threads=1):
    if backend == 'python':
        return extract_python(image, patches)
    if backend != 'cpp':
        raise ValueError('Unknown backend')
    from pathology_edge import _patch_cpp
    if not patches:
        return np.empty((0, 0, 0, 3), dtype=np.uint8)
    if any(p.size != patches[0].size for p in patches):
        raise ValueError('Mixed patch sizes')
    return _patch_cpp.extract(np.ascontiguousarray(image),
                              np.array([(p.x, p.y) for p in patches], dtype=np.int64),
                              patches[0].size, threads)


def stitch(probabilities, patches, shape, weighted=False):
    h, w = shape
    if len(probabilities) != len(patches) or not patches:
        raise ValueError('One probability map per patch required')
    size = patches[0].size
    weights = np.ones((size, size), np.float32)
    if weighted:
        a = np.maximum(np.hanning(size).astype(np.float32), 0.05)
        weights = np.outer(a, a)
    total, norm = np.zeros((h, w), np.float32), np.zeros((h, w), np.float32)
    for prob, p in zip(probabilities, patches):
        vh, vw = min(size, h-p.y), min(size, w-p.x)
        sl = np.s_[p.y:p.y+vh, p.x:p.x+vw]
        total[sl] += prob[:vh, :vw] * weights[:vh, :vw]
        norm[sl] += weights[:vh, :vw]
    if np.any(norm == 0):
        raise ValueError('Uncovered pixels')
    return total / norm


def boundary_mask(shape, size=128, radius=8):
    """Same internal baseline seam bands for every compared method; excludes exterior."""
    if size <= 0 or radius < 0:
        raise ValueError('Invalid seam parameters')
    h, w = shape
    mask = np.zeros(shape, bool)
    for x in range(size, w, size):
        mask[:, max(0, x-radius):min(w, x+radius)] = True
    for y in range(size, h, size):
        mask[max(0, y-radius):min(h, y+radius), :] = True
    return mask
