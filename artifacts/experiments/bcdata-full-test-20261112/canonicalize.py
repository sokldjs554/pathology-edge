"""Coordinate-only diagnostic canonicalization; never uses model outputs."""
from collections import Counter

import numpy as np


def canonicalize(positive, negative, width=640, height=640):
    arrays, valid, excluded, empty_shapes = [], [], [], []
    for target, source in enumerate((positive, negative)):
        array = np.asarray(source)
        empty_shape = array.shape == (0,)
        if empty_shape:
            array = array.reshape(0, 2)
        if array.ndim != 2 or array.shape[1] != 2 or not np.issubdtype(array.dtype, np.number):
            raise ValueError("Expected numeric Nx2 coordinates, or an empty (0,) array")
        arrays.append(array)
        empty_shapes.append(empty_shape)
        rows = []
        for index, point in enumerate(array):
            if not np.isfinite(point).all():
                reason = "nonfinite"
            elif not (point == np.floor(point)).all():
                reason = "noninteger"
            elif not (0 <= point[0] < width and 0 <= point[1] < height):
                reason = "out_of_bounds"
            else:
                rows.append((index, tuple(int(x) for x in point)))
                continue
            excluded.append({"class": target, "source_row_index": index, "reason": reason})
        valid.append(rows)
    conflicts = {point for _, point in valid[0]} & {point for _, point in valid[1]}
    points, truth, duplicates, class_counts = [], [], [], []
    for target, rows in enumerate(valid):
        first = {}
        repeated_locations = sum(n > 1 for n in Counter(point for _, point in rows if point not in conflicts).values())
        for index, point in rows:
            if point in conflicts:
                excluded.append({"class": target, "source_row_index": index, "reason": "cross_label_conflict"})
            elif point in first:
                duplicates.append({"class": target, "source_row_index": index,
                                   "first_source_row_index": first[point], "point": list(point)})
            else:
                first[point] = index
                points.append(point)
                truth.append(target)
        class_counts.append({"raw_records": len(arrays[target]), "unique_centers": len(first),
                             "duplicate_excess_records": sum(r["class"] == target for r in duplicates),
                             "repeated_locations": repeated_locations,
                             "empty_shape_normalized": empty_shapes[target]})
    return {"points": np.asarray(points, dtype=np.int64).reshape(-1, 2),
            "truth": np.asarray(truth, dtype=np.int64), "duplicates": duplicates,
            "excluded": excluded, "cross_label_conflicting_locations": len(conflicts),
            "class_counts": class_counts}
