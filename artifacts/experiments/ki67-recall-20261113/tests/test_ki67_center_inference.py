import numpy as np
import pytest
import torch
from pathology_edge import ki67_center_inference as i
from pathology_edge.ki67_centers import CenterDetector
from pathology_edge.ihc_baseline import CLASSES


def classifier():
    return dict(classes=list(CLASSES),coefficients=np.zeros((4,40)).tolist(),intercepts=[0.]*4,
                scaler=dict(mean=[0.]*40,scale=[1.]*40))


def model(bias):
    m=CenterDetector()
    with torch.no_grad():
        for v in m.parameters():v.zero_()
        m.head.bias.fill_(bias)
    return m


def test_image_only_pipeline_classifies_new_plateau_coordinate():
    p=i.infer_rgb(np.full((32,32,3),255,dtype=np.uint8),model(0),{'threshold':.5,'min_distance':8},classifier())
    assert p['points_xy'].tolist()==[[15,15]]
    assert p['classes'].tolist()==[0]
    assert p['positive_fraction']=={'positive_tumor_cells':1,'tumor_cells':1,'fraction':1.}
    assert 'probability_map' not in p  # portable per-cell output, not dense pixel dump


def test_empty_predictions_have_undefined_ratio_and_bad_model_is_not_hidden():
    rgb=np.zeros((32,32,3),dtype=np.uint8)
    p=i.infer_rgb(rgb,model(-20),{'threshold':.5,'min_distance':8},classifier())
    assert p['positive_fraction']['fraction'] is None and p['probabilities'].shape==(0,4)
    bad=classifier();bad['intercepts'][0]=float('nan')
    with pytest.raises(ValueError):i.infer_rgb(rgb,model(-20),{'threshold':.5,'min_distance':8},bad)


def test_bundle_file_rejects_traversal_and_hash_mismatch(tmp_path):
    (tmp_path/'model.pt').write_bytes(b'abc')
    with pytest.raises(ValueError):i.bundle_file(tmp_path,{'file':'../model.pt','sha256':'0'*64})
    with pytest.raises(ValueError,match='hash'):i.bundle_file(tmp_path,{'file':'model.pt','sha256':'0'*64})


def test_bundle_rejects_unknown_seed_without_loading_weights(tmp_path):
    import json
    (tmp_path/'bundle.json').write_text(json.dumps({'schema':'learned-centers-inference.v1','detectors':[], 'classifiers':{}}))
    with pytest.raises(ValueError,match='seed'):i.load_bundle(tmp_path/'bundle.json',99,'lr')
