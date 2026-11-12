"""Categorical geometry contracts, not model-performance expectations."""
import numpy as np
import pytest
from scipy.ndimage import zoom
from pathology_edge.annotation_grid import AnnotationGrid


def test_identity_preserves_every_channel_and_returns_copy():
    a = np.arange(36, dtype=np.uint16).reshape(3,4,3)
    original = a.copy()
    out = AnnotationGrid((4,3),(4,3)).resample(a)
    np.testing.assert_array_equal(out, a)
    assert not np.shares_memory(out,a)
    out[0,0,0]=999
    np.testing.assert_array_equal(a,original)


def test_anisotropic_categorical_tuple_mapping():
    a = np.arange(36, dtype=np.uint8).reshape(3,4,3)
    out = AnnotationGrid((4,3),(3,4)).resample(a)
    expected = a[np.array([0,1,1,2])[:,None],np.array([0,2,3])[None,:]]
    np.testing.assert_array_equal(out,expected)
    assert set(map(tuple,out.reshape(-1,3))) <= set(map(tuple,a.reshape(-1,3)))


def test_edge_mapping_preserves_corners_and_common_level0_extent():
    grid=AnnotationGrid((398,377),(399,376))
    points=np.array([[0,0],[398,377],[128.5,201.5]])
    out=grid.to_target_edges(points)
    np.testing.assert_array_equal(out[:2],[[0,0],[399,376]])
    np.testing.assert_allclose(grid.to_source_edges(out),points,atol=1e-12)
    origin=np.array([7297,55226]);extent=np.array([317,299])
    np.testing.assert_allclose(origin+points/np.array([398,377])*extent,
                               origin+out/np.array([399,376])*extent,atol=1e-10)


@pytest.mark.parametrize('source,target', [((4,3),(3,4)),((7,8),(8,7)),((398,377),(399,376)),((353,385),(352,385)),((1,1),(2,2)),((2,2),(1,1))])
def test_matches_independent_scipy_categorical_resampling(source,target):
    w,h=source;tw,th=target
    a=(np.arange(h*w,dtype=np.uint32).reshape(h,w)%251).astype(np.uint8)
    expected=zoom(a,(th/h,tw/w),order=0,grid_mode=True,prefilter=False,mode='nearest')
    np.testing.assert_array_equal(AnnotationGrid(source,target).resample(a),expected)


def test_exclusions_and_binary_target_use_identical_pixel_map():
    code=np.array([[0,1,99],[253,2,253]],np.uint8)
    grid=AnnotationGrid((3,2),(2,3));out=grid.resample(code)
    np.testing.assert_array_equal(grid.resample(code==99),out==99)
    np.testing.assert_array_equal(grid.resample((code>=1)&(code<=12)),(out>=1)&(out<=12))
    assert grid.resample(code==99).dtype==np.bool_


@pytest.mark.parametrize('src,dst', [((3,3),(5,3)),((0,3),(1,3)),((3.,3),(3,3)),((True,3),(1,3)),((3,3),(3,False)),((3,),(3,3)),((3,3),('3',3))])
def test_rejects_invalid_or_larger_size_mismatch(src,dst):
    with pytest.raises(ValueError):AnnotationGrid(src,dst)


@pytest.mark.parametrize('array', [np.zeros((3,4),np.float32),np.zeros((3,4),object),np.zeros((3,5),np.uint8),np.zeros((3,4,0),np.uint8),np.zeros(12,np.uint8)])
def test_rejects_non_categorical_or_unaligned_array(array):
    with pytest.raises(ValueError):AnnotationGrid((4,3),(3,4)).resample(array)


@pytest.mark.parametrize('points', [np.array([1,2]),np.array([[1,np.nan]]),np.array([['1','2']]),np.array([[True,False]])])
def test_rejects_invalid_continuous_points(points):
    with pytest.raises(ValueError):AnnotationGrid((4,3),(3,4)).to_target_edges(points)


def test_reference_half_pixel_tie_is_reproducible_at_404_to_403():
    a=np.arange(404,dtype=np.uint16)[None,:]
    reference=zoom(a,(1,403/404),order=0,grid_mode=True,prefilter=False,mode='nearest')
    np.testing.assert_array_equal(AnnotationGrid((404,1),(403,1)).resample(a),reference)
