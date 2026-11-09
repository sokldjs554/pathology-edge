"""Codex-provided contract tests for the reviewed STEP 9 user function."""
from copy import deepcopy

import pytest

from pathology_edge.learner_split import find_group_leaks

# STEP 9 was submitted and reviewed; include these tests in the default suite.


def test_empty_input_has_no_reported_group_conflicts():
    result = find_group_leaks([])
    assert type(result) is dict
    assert result == {}


def test_separate_groups_and_repeated_group_in_one_split_are_allowed():
    records = [
        {"group_id": "01", "split": "train"},
        {"group_id": "01", "split": "train"},
        {"group_id": "08", "split": "validation"},
        {"group_id": "10", "split": "test"},
    ]
    assert find_group_leaks(records) == {}


def test_same_group_leaks_even_when_image_ids_and_hashes_differ():
    records = [
        {"id": "a", "image_sha256": "synthetic-hash-a", "group_id": "01", "split": "train"},
        {"id": "b", "image_sha256": "synthetic-hash-b", "group_id": "01", "split": "test"},
    ]
    assert find_group_leaks(records) == {"01": ["train", "test"]}


def test_reports_all_conflicts_once_in_canonical_split_order():
    records = [
        {"group_id": "B", "split": "test"},
        {"group_id": "A", "split": "validation"},
        {"group_id": "B", "split": "train"},
        {"group_id": "A", "split": "train"},
        {"group_id": "B", "split": "validation"},
        {"group_id": "A", "split": "validation"},
        {"group_id": "C", "split": "test"},
    ]
    assert find_group_leaks(records) == {
        "A": ["train", "validation"],
        "B": ["train", "validation", "test"],
    }


def test_record_order_does_not_affect_result_and_inputs_are_preserved():
    records = [
        {"group_id": "g", "split": "test", "extra": {"origin": [0, 1]}},
        {"group_id": "g", "split": "train", "extra": {"origin": [2, 3]}},
    ]
    before = deepcopy(records)
    assert find_group_leaks(records) == {"g": ["train", "test"]}
    assert records == before
    reversed_records = list(reversed(records))
    assert find_group_leaks(reversed_records) == {"g": ["train", "test"]}
    assert reversed_records == list(reversed(before))


def test_group_ids_are_not_coerced_to_integers():
    assert find_group_leaks([
        {"group_id": "01", "split": "train"},
        {"group_id": "1", "split": "test"},
    ]) == {}


@pytest.mark.parametrize("records", [
    None,
    {},
    (),
    [None],
    [{"split": "train"}],
    [{"group_id": "", "split": "train"}],
    [{"group_id": "   ", "split": "train"}],
    [{"group_id": 1, "split": "train"}],
    [{"group_id": "g"}],
    [{"group_id": "g", "split": "val"}],
    [{"group_id": "g", "split": None}],
    [{"group_id": "g", "split": []}],
])
def test_invalid_records_raise_value_error(records):
    with pytest.raises(ValueError):
        find_group_leaks(records)
