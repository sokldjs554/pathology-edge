import numpy as np
import pytest


def test_only_reviewed_fov_pixels_are_scored_and_boxes_are_not_contours():
    from pathology_edge.panoptils import annotation_region
    mask = np.zeros((16, 16, 3), np.uint8)
    mask[..., 0] = 1
    mask[..., 1] = 9
    mask[5:8, 5:8, 1] = 2
    mask[8:11, 8:11, 1] = 1
    mask[3, 3, 1] = 8
    mask[3, 4, 1] = 0
    annotations = [{'type':'rectangle','left':'5','right':'7','top':'5','bottom':'7'},
                   {'type':'polyline','left':'8','right':'10','top':'8','bottom':'10'}]
    target, valid, stats = annotation_region(mask, annotations, {'left':2,'right':14,'top':2,'bottom':14})
    assert not valid[:2].any() and not valid[:,14:].any()
    assert not valid[5:8,5:8].any()
    assert not valid[3,3] and not valid[3,4]
    assert valid[8:11,8:11].all() and target[8:11,8:11].all()
    assert valid.sum() == 144 - 9 - 2
    assert stats['rectangle_annotations_excluded'] == 1


@pytest.mark.parametrize('damage',['bad_code','empty','bad_fov','bad_type'])
def test_invalid_annotation_contract_fails(damage):
    from pathology_edge.panoptils import annotation_region
    mask=np.zeros((16,16,3),np.uint8);mask[...,0]=1;mask[...,1]=9
    fov={'left':2,'right':14,'top':2,'bottom':14};annotations=[]
    if damage=='bad_code':mask[0,0,1]=10
    if damage=='empty':mask[...,1]=0
    if damage=='bad_fov':fov['right']=17
    if damage=='bad_type':annotations=[{'type':'ellipse'}]
    with pytest.raises(ValueError):annotation_region(mask,annotations,fov)


def test_ignored_pixels_cannot_change_dice_and_seams_use_same_valid_region():
    from pathology_edge.panoptils import score_roi
    target=np.zeros((256,256),bool);target[120:136,120:136]=True
    valid=np.zeros_like(target);valid[100:160,100:160]=True
    probability=target.astype(np.float32);probability[~valid]=1
    scores=score_roi(probability,target,valid,.35)
    assert scores['all']['dice']==1
    assert scores['all']['pixels']==3600
    assert scores['boundary']['pixels']+scores['interior']['pixels']==3600
    assert scores['boundary']['tp']==target.sum()


def test_rectangle_entirely_outside_image_cannot_wrap_negative_slices():
    from pathology_edge.panoptils import annotation_region
    mask=np.zeros((16,16,3),np.uint8);mask[...,0]=1;mask[...,1]=9
    outside=[{'type':'rectangle','left':-5,'right':-2,'top':-5,'bottom':-2}]
    _,valid,_=annotation_region(mask,outside,{'left':0,'right':16,'top':0,'bottom':16})
    assert valid.all()


def test_roi_geometry_checks_encoded_bounds_before_mapping_to_wsi():
    from pathology_edge.panoptils import roi_geometry
    from pathology_edge.learner_wsi import roi_points_to_level0
    record = dict(id='TCGA-A1-A0SP-DX1_left-10_top-20_bottom-1256_right-1247',
                  bounds_level0=dict(left=10, top=20, right=1247, bottom=1256),
                  evaluation_input_wh=[1024, 1024], tiles=dict(sizeX=5000, sizeY=6000))
    geometry = roi_geometry(record)
    assert np.allclose(roi_points_to_level0(np.array([[0, 0], [1024, 1024]]), geometry),
                       [[10, 20], [1247, 1256]])
    record['bounds_level0']['left'] = 11
    with pytest.raises(ValueError, match='bounds'):
        roi_geometry(record)


def test_runner_matches_fov_filename_including_png_extension(tmp_path):
    import importlib.util
    from pathlib import Path
    from PIL import Image
    spec = importlib.util.spec_from_file_location('panoptils_runner', Path(__file__).parents[1]/'scripts/run_panoptils_probe.py')
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    (tmp_path/'csv').mkdir(); (tmp_path/'masks').mkdir()
    (tmp_path/'csv/ALL_FOV_LOCATIONS.csv').write_text('roiname,left,right,top,bottom\nexample.png,1,3,1,3\n')
    (tmp_path/'csv/example.csv').write_text('type,left,right,top,bottom\n')
    mask = np.zeros((4, 4, 3), np.uint8); mask[..., 0] = 1; mask[..., 1] = 9
    Image.fromarray(mask).save(tmp_path/'masks/example.png')
    _, valid, coverage = runner.masks(tmp_path, 'example')
    assert valid.sum() == coverage['valid_pixels'] == 4
