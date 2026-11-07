import json
from pathlib import Path
import numpy as np
import pytest
import torch
from pathology_edge.data import check_split, tissue_mask
from pathology_edge.patches import grid, extract, stitch, boundary_mask
from pathology_edge.merge import box_iou, deduplicate, components
from pathology_edge.metrics import binary_metrics, point_metrics
from pathology_edge.model import TinyUNet, loss_fn
from pathology_edge.experiment import predict


@pytest.mark.parametrize('shape,size,overlap', [((32,45),16,0),((32,45),16,8),((5,7),16,4),((128,128),128,0)])
@pytest.mark.parametrize('threads',[1,2,4])
def test_native_matches_python_with_trailing_padding(shape,size,overlap,threads):
    image=np.random.default_rng(9).integers(0,256,(*shape,3),dtype=np.uint8)
    patches=grid(shape[1],shape[0],size,overlap)
    expected=extract(image,patches)
    np.testing.assert_array_equal(extract(image,patches,'cpp',threads),expected)
    for p,t in zip(patches,expected):
        np.testing.assert_array_equal(t[:p.valid_height,:p.valid_width],image[p.y:p.y+p.valid_height,p.x:p.x+p.valid_width])
        assert (t[p.valid_height:]==255).all()
        assert (t[:,p.valid_width:]==255).all()


@pytest.mark.parametrize('args',[(0,10,8,0),(10,10,8,8),(10,10,8,-1),(10,10,0,0)])
def test_grid_rejects_bad_geometry(args):
    with pytest.raises(ValueError): grid(*args)


@pytest.mark.parametrize('weighted',[False,True])
def test_stitch_reconstructs_ramp(weighted):
    h,w=31,27
    target=np.arange(h*w,dtype=np.float32).reshape(h,w)/1000
    patches=grid(w,h,16,8); probs=[]
    for p in patches:
        a=np.zeros((16,16),np.float32)
        a[:p.valid_height,:p.valid_width]=target[p.y:p.y+p.valid_height,p.x:p.x+p.valid_width]
        probs.append(a)
    np.testing.assert_allclose(stitch(probs,patches,(h,w),weighted),target,atol=1e-6)


def test_fixed_boundary_regions():
    a=boundary_mask((256,256),128,8)
    assert a[:,120:136].all() and a[120:136,:].all()
    assert not a[0,0] and not a[-1,-1]
    assert int(a.sum())==16*256*2-16*16


def test_metric_known_counts():
    r=binary_metrics(np.array([[1,1],[0,0]]),np.array([[1,0],[1,0]]))
    assert (r['tp'],r['fp'],r['fn'])==(1,1,1)
    assert r['dice']==.5 and r['iou']==pytest.approx(1/3)
    assert binary_metrics(np.zeros((2,2)),np.zeros((2,2)))['dice']==1
    with pytest.raises(ValueError): binary_metrics(np.full((2,2),.5),np.zeros((2,2)))


def test_matching_does_not_double_count():
    r=point_metrics([[1,1],[1.1,1]],[[1,1]],1)
    assert (r['tp'],r['fp'],r['fn'])==(1,1,0)
    assert point_metrics([],[[1,1]])['fn']==1
    assert point_metrics([],[])['f1']==1


def test_matching_maximizes_cardinality_before_distance():
    # Greedy nearest would use target 0 for pred 0 and lose pred 1.
    r=point_metrics([[1,0],[-1,0]],[[0,0],[3,0]],2.1)
    assert r['tp']==2


def obj(x,patch=0,edge=False):
    return dict(x=x,y=10,bbox=[x-5,5,x+5,15],score=.9,patch_id=patch,touches_edge=edge)


def test_merge_prefers_complete_and_tracks_suppression():
    a,b=obj(10,0,True),obj(11,1,False)
    merged,removed=deduplicate([a,b])
    assert len(merged)==1 and merged[0]['patch_id']==1
    assert removed==[dict(suppressed_index=0,kept_index=1)]
    assert len(deduplicate([obj(10,0),obj(11,0)])[0])==2
    assert len(deduplicate([obj(10,0),obj(50,1)])[0])==2
    assert box_iou([0,0,10,10],[10,0,20,10])==0


def test_component_coordinate_and_padding():
    mask=np.zeros((20,20),np.uint8); mask[4:10,2:8]=1
    o=components(mask,patch_id=3,origin=(100,200))[0]
    assert o['bbox']==[102,204,108,210]
    assert o['x']==104.5 and o['y']==206.5


@pytest.mark.parametrize('kind',['group','bytes','id','missing'])
def test_split_leakage_rejected(kind):
    a=dict(id='a',group_id='g1',image_sha256='h1',split='train')
    b=dict(id='b',group_id='g2',image_sha256='h2',split='test')
    key={'group':'group_id','bytes':'image_sha256','id':'id','missing':'group_id'}[kind]
    b[key]=None if kind=='missing' else a[key]
    with pytest.raises(ValueError): check_split([a,b])


def test_valid_split_and_background_gate():
    assert check_split([dict(id='a',group_id='g1',image_sha256='h1',split='train'),dict(id='b',group_id='g2',image_sha256='h2',split='test')])
    assert tissue_mask(np.full((12,12,3),255,np.uint8)).sum()==0


def test_model_gradient_and_real_inference_backend_parity():
    torch.set_num_threads(2); torch.manual_seed(7)
    model=TinyUNet(); x=torch.rand(2,3,32,40)
    loss=loss_fn(model(x),torch.zeros(2,1,32,40)); loss.backward()
    assert model.head.weight.grad.abs().sum()>0
    image=np.full((140,170,3),[100,60,130],np.uint8)
    a=predict(model,image,'overlap',backend='python')
    b=predict(model,image,'overlap',backend='cpp',threads=2)
    np.testing.assert_array_equal(a['probability'],b['probability'])
    assert a['objects']==b['objects'] and a['mask'].shape==(140,170)


def test_export_assets_connect_to_measured_results():
    path=Path('dist/results.json')
    if not path.exists(): pytest.skip('Run real train/evaluate/export to verify artifact wiring')
    from PIL import Image
    payload=json.loads(path.read_text())
    evaluation=json.loads(Path('artifacts/evaluation.json').read_text())
    assert payload['model_sha256']==evaluation['model_sha256']
    for s in payload['samples']:
        image=np.asarray(Image.open(Path('dist')/s['image']))
        assert image.shape[:2]==(s['height'],s['width'])
        for mode,result in s['methods'].items():
            overlay=np.asarray(Image.open(Path('dist')/result['overlay']))
            assert overlay.shape==(s['height'],s['width'],4)
            mask=np.asarray(Image.open(f'artifacts/predictions/{mode}/{s["id"]}.png'))>0
            np.testing.assert_array_equal(overlay[...,3]>0,mask)
            measured=next(r for r in evaluation['methods'][mode]['rows'] if r['id']==s['id'])
            assert result['metrics']==measured['metrics']
            assert len(result['objects'])==measured['merged_count']
            for o in result['objects']:
                assert 0<=o['x']<s['width'] and 0<=o['y']<s['height']


def test_training_cannot_restart_after_test_evaluation_started(tmp_path):
    from pathology_edge.experiment import train
    (tmp_path/'evaluation_lock.json').write_text('{}')
    with pytest.raises(RuntimeError,match='Held-out'):
        train(root='does-not-exist',output=tmp_path)


def test_changed_threshold_rejected_after_test_opened(tmp_path):
    from pathology_edge.data import sha256
    from pathology_edge.experiment import evaluate
    data=tmp_path/'data';out=tmp_path/'out';data.mkdir();out.mkdir()
    (data/'manifest.json').write_text('{}');(out/'model.pt').write_bytes(b'checkpoint-fixture')
    cfg={'manifest_sha256':sha256(data/'manifest.json')}
    training={'model_sha256':sha256(out/'model.pt'),'config':cfg,'threshold':.7}
    (out/'training.json').write_text(json.dumps(training))
    (out/'evaluation_lock.json').write_text(json.dumps({'model_sha256':training['model_sha256'],'protocol':cfg,'threshold':.5}))
    with pytest.raises(ValueError,match='protocol changed'):
        evaluate(data,out)
