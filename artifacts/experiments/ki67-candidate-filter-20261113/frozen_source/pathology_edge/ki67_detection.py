"""Image-only classical localization. Scores are LoG responses, not probabilities."""
import numpy as np
from scipy.ndimage import gaussian_laplace, maximum_filter

SIGMAS = (1.5, 2.5, 3.5)


def validate_rgb(rgb):
    if not isinstance(rgb, np.ndarray) or rgb.dtype != np.uint8 or rgb.ndim != 3 or rgb.shape[2] != 3 or min(rgb.shape[:2]) == 0:
        raise ValueError('Expected nonempty uint8 RGB image')


def validate_config(config=None):
    config = {} if config is None else dict(config)
    if set(config) - {'min_response', 'min_distance'}:
        raise ValueError('Unknown detector setting')
    result = {'min_response': .06, 'min_distance': 6.0, **config}
    for value in result.values():
        if isinstance(value, (bool, str)) or not np.isscalar(value) or not np.isfinite(value) or value <= 0:
            raise ValueError('Detector settings must be positive finite numbers')
    return result


def response_map(rgb):
    validate_rgb(rgb)
    density = -np.log((rgb.astype(np.float64) + 1) / 256).mean(axis=2)
    return np.maximum.reduce([-sigma**2 * gaussian_laplace(density, sigma, mode='reflect') for sigma in SIGMAS])


def select_peaks(response, min_response, min_distance):
    validate_config({'min_response': min_response, 'min_distance': min_distance})
    response = np.asarray(response)
    if response.ndim != 2 or not response.size or not np.isfinite(response).all():
        raise ValueError('Expected finite nonempty 2D response')
    yy, xx = np.nonzero((response >= min_response) & (response == maximum_filter(response, size=3, mode='constant', cval=-np.inf)))
    scores = response[yy, xx]
    order = np.lexsort((xx, yy, -scores))
    kept, kept_scores = [], []
    for i in order:
        point = np.array([xx[i], yy[i]])
        if not kept or np.all(np.sum((np.asarray(kept) - point)**2, axis=1) >= min_distance**2):
            kept.append(point)
            kept_scores.append(scores[i])
    return np.asarray(kept, dtype=np.int64).reshape(-1, 2), np.asarray(kept_scores, dtype=np.float64)


def detect_centers(rgb, config=None):
    config = validate_config(config)
    points, scores = select_peaks(response_map(rgb), **config)
    return {'points_xy': points, 'scores': scores}
