"""USER STEP 2. Reproduce a synthetic limitation; see docs/STEP_02.md.

Codex supplies the imports and fixture. The user writes the test body.
This is not a real pathology annotation or a new model inference result.
"""
from math import hypot

import pytest

from pathology_edge.merge import box_iou, deduplicate

pytestmark = pytest.mark.learner


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
    """Document the current heuristic's undercount for the two-nucleus fixture."""
    # USER TODO: verify the geometry, call the real function and check the
    # retained candidate and suppression mapping described in docs/STEP_02.md.
    raise NotImplementedError("사용자 작성 예정: docs/STEP_02.md")
