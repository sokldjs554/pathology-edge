import numpy as np
import pytest
from pathology_edge.ki67_external import canonical_points, tumor_only_row, validate_external_entries


def test_canonical_points_reject_conflicts_deduplicate_and_keep_xy():
    p, c, audit = canonical_points(np.array([[12,31],[12,31]]),np.empty((0,)))
    assert p.tolist() == [[12,31]] and c.tolist() == [0]
    assert audit['duplicate_records_removed'] == 1
    with pytest.raises(ValueError):
        canonical_points([[1,2]],[[1,2]])
    with pytest.raises(ValueError):
        canonical_points([[640,2]],[])


def test_non_tumor_predictions_are_not_scored_as_annotated_non_tumor():
    row = {'image':'1','points':[[2,2],[5,5]],'classes':{'cnn':[2,0]},'gt_points':[[2,2]],'gt_classes':[0]}
    filtered = tumor_only_row(row,'cnn')
    assert filtered['points'] == [[5,5]]
    assert filtered['gt_classes'] == [0]
    assert filtered['classes'] == {'cnn':[0]}


def test_external_manifest_must_have_all_133_complete_triples():
    entries = []
    for i in range(133):
        entries.extend([{'name':f'BCData/images/validation/{i}.png'},
                        {'name':f'BCData/annotations/validation/positive/{i}.h5'},
                        {'name':f'BCData/annotations/validation/negative/{i}.h5'}])
    assert len(validate_external_entries(entries)) == 133
    with pytest.raises(ValueError):
        validate_external_entries(entries[:-1])
