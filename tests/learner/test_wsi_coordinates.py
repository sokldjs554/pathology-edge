"""STEP_40 contracts for the accepted user adapter; included in default CI."""
import numpy as np
import pytest


def geometry(**changes):
    from pathology_edge.wsi_roi import RoiGeometry
    values = dict(origin_level0_xy=(1000, 2000), level=1, level_downsample=4.0,
                  read_size_wh=(400, 200), model_size_wh=(200, 50),
                  slide_size_level0_wh=(10000, 10000))
    return RoiGeometry(**(values | changes))


def test_anisotropic_resize_and_no_input_mutation():
    from pathology_edge.learner_wsi import roi_points_to_level0
    points = np.array([[10, 20], [0, 0]], dtype=np.int32)
    before = points.copy()
    points.flags.writeable = False
    result = roi_points_to_level0(points, geometry())
    assert result.dtype == np.float64 and result.shape == (2, 2)
    np.testing.assert_allclose(result, [[1080, 2320], [1000, 2000]])
    np.testing.assert_array_equal(points, before)


def test_native_edges_and_empty_points():
    from pathology_edge.learner_wsi import roi_points_to_level0
    g = geometry(level=0, level_downsample=1., read_size_wh=(150, 130), model_size_wh=(150, 130))
    np.testing.assert_array_equal(roi_points_to_level0(np.array([[0, 0], [150, 130]]), g),
                                  [[1000, 2000], [1150, 2130]])
    result = roi_points_to_level0(np.empty((0, 2)), g)
    assert result.shape == (0, 2) and result.dtype == np.float64


def test_fractional_downsample_is_not_replaced_with_a_power_of_two():
    from pathology_edge.learner_wsi import roi_points_to_level0
    g = geometry(level_downsample=4.25, read_size_wh=(100, 80), model_size_wh=(50, 80))
    np.testing.assert_allclose(roi_points_to_level0(np.array([[1., 2.5]]), g), [[1008.5, 2010.625]])


def test_points_are_not_rounded_or_clipped_to_model_extent():
    from pathology_edge.learner_wsi import roi_points_to_level0
    np.testing.assert_allclose(roi_points_to_level0(np.array([[-.25, .5], [210, 60]]), geometry()),
                               [[998, 2008], [2680, 2960]])


def test_uses_actual_read_size_after_edge_crop():
    from pathology_edge.learner_wsi import roi_points_to_level0
    from pathology_edge.wsi_roi import read_roi
    from PIL import Image
    class EdgeSlide:
        dimensions = (500, 400)
        level_downsamples = (1.0,)
        def read_region(self, location, level, size):
            return Image.new('RGBA', size, 'white')
    roi = read_roi(EdgeSlide(), (490, 380), 0, (40, 30), (20, 10))
    assert roi.geometry.read_size_wh == (10, 20) and roi.requested_size_wh == (40, 30)
    np.testing.assert_allclose(roi_points_to_level0(np.array([[20, 10], [10, 5]]), roi.geometry),
                               [[500, 400], [495, 390]])


def test_preserves_existing_invalid_point_rejection():
    from pathology_edge.learner_wsi import roi_points_to_level0
    for points in (np.zeros((2, 3)), np.array([1, 2]), np.array([[np.nan, 0]]), np.array([[True, False]])):
        with pytest.raises(ValueError):
            roi_points_to_level0(points, geometry())


def test_native_footprint_consumer_matches_existing_export():
    from pathology_edge.wsi_roi import roi_patch_manifest
    from pathology_edge.wsi_export import patch_manifest
    g = geometry(level=0, level_downsample=1., read_size_wh=(150, 130), model_size_wh=(150, 130))
    for mode in ('no_overlap', 'overlap'):
        assert roi_patch_manifest(g, mode) == patch_manifest(150, 130, (1000, 2000), mode)


def test_scaled_patch_footprints_exclude_trailing_padding():
    from pathology_edge.wsi_roi import roi_patch_manifest
    g = geometry(read_size_wh=(300, 260), model_size_wh=(150, 130))
    rows = roi_patch_manifest(g, 'no_overlap')
    assert len(rows) == 4
    assert rows[-1]['origin_local'] == [128, 128]
    assert rows[-1]['bbox_local'] == [128, 128, 150, 130]
    assert rows[-1]['bbox_level0'] == [2024, 3024, 2200, 3040]
    assert rows[-1]['valid_size'] == [22, 2]
