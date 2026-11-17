def components(mask, probability=None, patch_id=-1, origin=(0, 0), min_area=12):
    # Coordinate-only NMS review does not require the image-processing stack.
    import cv2
    import numpy as np

    n, labels, stats, centers = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
    objects = []
    for i in range(1, n):
        x, y, w, h, area = map(int, stats[i])
        if area < min_area:
            continue
        cx, cy = centers[i]
        score = float(probability[labels == i].mean()) if probability is not None else 1.0
        edge = x == 0 or y == 0 or x+w == mask.shape[1] or y+h == mask.shape[0]
        objects.append(dict(x=float(cx+origin[0]), y=float(cy+origin[1]),
                            bbox=[x+origin[0], y+origin[1], x+w+origin[0], y+h+origin[1]],
                            area=area, score=score, patch_id=int(patch_id), touches_edge=edge))
    return objects


def box_iou(a, b):
    iw, ih = max(0, min(a[2], b[2])-max(a[0], b[0])), max(0, min(a[3], b[3])-max(a[1], b[1]))
    inter = iw*ih
    union = (a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - inter
    return inter/union if union else 0.0


def deduplicate(objects, iou_threshold=0.3, distance=8):
    """Deterministic cross-patch NMS; prefer complete components then confidence.

    A heuristic: can merge close distinct nuclei or miss fragments. The pixel
    segmentation branch instead blends probability maps before thresholding.
    """
    if not 0 < iou_threshold <= 1 or distance < 0:
        raise ValueError('Invalid merge thresholds')
    order = sorted(range(len(objects)), key=lambda i: (objects[i]['touches_edge'], -objects[i]['score'], i))
    kept, removed = [], []
    for i in order:
        a = objects[i]
        match = None
        for j in kept:
            b = objects[j]
            if a['patch_id'] == b['patch_id']:
                continue
            if box_iou(a['bbox'], b['bbox']) >= iou_threshold or (a['x']-b['x'])**2+(a['y']-b['y'])**2 <= distance**2:
                match = j
                break
        if match is None:
            kept.append(i)
        else:
            removed.append(dict(suppressed_index=i, kept_index=match))
    return [dict(objects[i], raw_index=i) for i in kept], removed
