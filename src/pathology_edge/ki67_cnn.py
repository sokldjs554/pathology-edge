"""Small morphology classifier and image-only automatic inference interface."""
import numpy as np
import torch
from torch import nn
from .ki67_detection import validate_rgb, detect_centers
from .ki67_evaluation import points_array, positive_fraction
from .ihc_baseline import CLASSES, extract_features, predict_proba


def cell_crops(rgb, points_xy, size=48):
    validate_rgb(rgb)
    points = points_array(points_xy)
    if not isinstance(size, int) or isinstance(size, bool) or size <= 0 or size % 2:
        raise ValueError('Crop size must be a positive even integer')
    if np.any(points != np.floor(points)) or np.any(points < 0) or np.any(points[:, 0] >= rgb.shape[1]) or np.any(points[:, 1] >= rgb.shape[0]):
        raise ValueError('Centers must be integer pixels inside image')
    padded = np.pad(rgb, ((size//2, size//2), (size//2, size//2), (0, 0)), constant_values=255)
    output = np.empty((len(points), size, size, 3), dtype=np.uint8)
    for i, (x, y) in enumerate(points.astype(int)):
        output[i] = padded[y:y+size, x:x+size]
    return output


class CellClassifier(nn.Module):
    def __init__(self):
        super().__init__()
        stages = []
        previous = 3
        for channels in (16, 32, 64):
            stages.extend([nn.Conv2d(previous, channels, 3, padding=1), nn.ReLU(),
                           nn.Conv2d(channels, channels, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2)])
            previous = channels
        self.features = nn.Sequential(*stages, nn.AdaptiveAvgPool2d(1))
        self.head = nn.Linear(64, 4)

    def forward(self, inputs):
        if inputs.ndim != 4 or inputs.shape[1:] != (3, 48, 48) or not inputs.is_floating_point() or not torch.isfinite(inputs).all():
            raise ValueError('Expected finite Nx3x48x48 floating input')
        return self.head(self.features(inputs).flatten(1))


def validate_classifier(model):
    if isinstance(model, CellClassifier):
        if not all(torch.isfinite(value).all() for value in model.state_dict().values()):
            raise ValueError('CNN parameters must contain only finite values')
        return
    if not isinstance(model, dict) or model.get('classes') != list(CLASSES):
        raise ValueError('Expected CellClassifier or four-class exported logistic model')
    try:
        arrays = [np.asarray(model['coefficients']), np.asarray(model['intercepts']),
                  np.asarray(model['scaler']['mean']), np.asarray(model['scaler']['scale'])]
        if [a.shape for a in arrays] != [(4, 40), (4,), (40,), (40,)] or not all(np.isfinite(a).all() for a in arrays) or np.any(arrays[-1] <= 0):
            raise ValueError('Invalid logistic model arrays')
    except (KeyError, TypeError) as exc:
        raise ValueError('Invalid classifier') from exc


def _checked_probabilities(probabilities, count):
    if probabilities.shape != (count, 4) or not np.isfinite(probabilities).all() or np.any(probabilities < 0) or np.any(probabilities > 1) or not np.allclose(probabilities.sum(axis=1), 1, rtol=1e-6, atol=1e-6):
        raise ValueError('Invalid classifier probabilities; refusing class assignment')
    return probabilities


def classify_centers(rgb, points, model):
    validate_classifier(model)
    crops = cell_crops(rgb, points)
    if not len(crops):
        return np.empty((0, 4), dtype=np.float64)
    if isinstance(model, dict):
        with np.errstate(over='ignore', invalid='ignore'):
            probabilities = predict_proba(extract_features(rgb, np.asarray(points, dtype=np.int64)), model)
        return _checked_probabilities(probabilities, len(crops))
    model.eval()
    outputs = []
    with torch.inference_mode():
        for start in range(0, len(crops), 128):
            inputs = torch.from_numpy(crops[start:start+128].transpose(0, 3, 1, 2).copy()).float()/255
            outputs.append(torch.softmax(model(inputs), dim=1).cpu().numpy())
    return _checked_probabilities(np.concatenate(outputs), len(crops))


def predict_image(rgb, detector, classifier):
    detected = detect_centers(rgb, detector)
    probabilities = classify_centers(rgb, detected['points_xy'], classifier)
    classes = probabilities.argmax(axis=1)
    return {**detected, 'probabilities': probabilities, 'classes': classes,
            'positive_fraction': positive_fraction(classes)}
