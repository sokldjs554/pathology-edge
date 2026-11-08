"""USER STEP 2. Reproduce a synthetic limitation; see docs/STEP_02.md.

Codex supplied the imports and fixture. The user submitted the reviewed body.
This is not a real pathology annotation or a new model inference result.
"""
from math import hypot

import pytest

from pathology_edge.merge import box_iou, deduplicate

# STEP 2 was submitted and reviewed; include it in the default regression suite.


@pytest.fixture
def candidate_pair():
    """Two distinct synthetic nuclei expressed in the same original coordinates."""
    return [
        dict(x=99.5, y=49.5, bbox=[98, 48, 102, 52], area=16,
             score=0.9, patch_id=0, touches_edge=False),
        dict(x=105.5, y=49.5, bbox=[104, 48, 108, 52], area=16,
             score=0.8, patch_id=1, touches_edge=False),
    ]


def test_distance_rule_can_suppress_distinct_nuclei(candidate_pair):
    """합성 정답은 서로 다른 핵 2개지만, 현재 규칙이 1개만 유지하는 한계를 재현한다."""
    a, b = candidate_pair

    assert box_iou(a["bbox"], b["bbox"]) == 0.0
    assert hypot(a["x"] - b["x"], a["y"] - b["y"]) == pytest.approx(6.0)

    kept, removed = deduplicate(candidate_pair)

    assert len(kept) == 1
    assert len(removed) == 1
    assert kept[0]["raw_index"] == 0
    assert removed[0]["suppressed_index"] == 1
    assert removed[0]["kept_index"] == 0
