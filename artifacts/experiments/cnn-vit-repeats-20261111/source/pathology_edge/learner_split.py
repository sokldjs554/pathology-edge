"""User-submitted STEP 9 group-split audit; see docs/STEP_09.md.

The production data.check_split remains unchanged. This function reports
cross-split group IDs; it does not establish patient independence or inspect images.
"""
from __future__ import annotations


def find_group_leaks(records: list[dict]) -> dict[str, list[str]]:
    """서로 다른 split에 등장한 그룹과 해당 split 목록을 반환한다."""
    if not isinstance(records, list):
        raise ValueError("records must be a list")

    split_order = ("train", "validation", "test")
    groups: dict[str, set[str]] = {}

    for record in records:
        if not isinstance(record, dict):
            raise ValueError("each record must be a dict")

        group_id = record.get("group_id")
        split = record.get("split")

        if not isinstance(group_id, str) or not group_id.strip():
            raise ValueError("group_id must be a non-blank string")

        if not isinstance(split, str) or split not in split_order:
            raise ValueError("split must be train, validation or test")

        groups.setdefault(group_id, set()).add(split)

    return {
        group_id: [split for split in split_order if split in splits]
        for group_id, splits in groups.items()
        if len(splits) > 1
    }
