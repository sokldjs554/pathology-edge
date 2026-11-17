import importlib.util
from pathlib import Path


def test_empty_predictions_have_no_fake_matching_links():
    p=Path(__file__).resolve().parents[1]/'scripts/build_ki67_transfer_review.py'
    spec=importlib.util.spec_from_file_location('transfer_review',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    row=dict(points=[],gt_points=[[5,5]],classes={'cnn':[]})
    r=m.display_record(row,{'pred_cells':0},'cnn')
    assert r['points']==[] and r['pairs']==[] and r['classes']==[]


def test_display_collapse_preserves_locations_and_two_stain_classes():
    p=Path(__file__).resolve().parents[1]/'scripts/build_ki67_transfer_review.py'
    spec=importlib.util.spec_from_file_location('transfer_review',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    row=dict(points=[[5,5],[30,30]],gt_points=[[5,5]],classes={'cnn':[2,3]})
    r=m.display_record(row,{},'cnn')
    assert r['points']==row['points'] and r['pairs']==[(0,0)] and r['classes']==[0,1]
