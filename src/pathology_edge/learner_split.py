"""USER STEP 9. Independent group-split audit; see docs/STEP_09.md.

The production data.check_split remains unchanged. This function reports
cross-split group IDs; it does not establish patient independence or inspect images.
"""
from __future__ import annotations


def find_group_leaks(records: list[dict]) -> dict[str, list[str]]:
    """Return groups seen in multiple splits, with train/validation/test ordering.

    Follow the validation, empty-input and input-preservation contract in STEP_09.
    Read group_id and split only; do not call data.check_split or change records.
    """
    raise NotImplementedError("사용자 작성 예정: docs/STEP_09.md")
