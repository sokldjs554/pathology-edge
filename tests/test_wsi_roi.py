"""Reader contracts with an OpenSlide-shaped I/O fixture; no external download."""
from dataclasses import FrozenInstanceError

import numpy as np
import pytest
from PIL import Image


class SlideFixture:
    dimensions = (1000, 800)
    level_downsamples = (1.0, 4.25)

    def __init__(self):
        self.calls = []

    def read_region(self, location, level, size):
        self.calls.append((location, level, size))
        width, height = size
        yy, xx = np.mgrid[:height, :width]
        rgba = np.stack([xx % 256, yy % 256, (xx + yy) % 256,
                         np.full_like(xx, 255)], axis=-1).astype(np.uint8)
        rgba[0, 0] = [12, 34, 56, 0]
        return Image.fromarray(rgba)

    def close(self):
        raise AssertionError('The reader must not close a caller-owned slide')


def test_native_read_preserves_rgb_order_and_composites_transparency_white():
    from pathology_edge.wsi_roi import read_roi
    slide = SlideFixture()
    roi = read_roi(slide, (100, 200), 0, (7, 5))
    assert slide.calls == [((100, 200), 0, (7, 5))]
    assert roi.image.shape == (5, 7, 3) and roi.image.dtype == np.uint8
    np.testing.assert_array_equal(roi.image[3, 6], [6, 3, 9])
    np.testing.assert_array_equal(roi.image[0, 0], [255, 255, 255])
    assert roi.valid_mask.dtype == bool and roi.valid_mask.shape == (5, 7)
    assert not roi.valid_mask[0, 0] and roi.valid_mask[3, 6]
    assert roi.geometry.read_size_wh == roi.geometry.model_size_wh == (7, 5)
    assert roi.requested_size_wh == (7, 5)


def test_noninteger_level_read_uses_level0_origin_and_actual_metadata():
    from pathology_edge.wsi_roi import read_roi
    slide = SlideFixture()
    roi = read_roi(slide, (100, 200), 1, (12, 8), (6, 2))
    assert slide.calls == [((100, 200), 1, (12, 8))]
    assert roi.geometry.level == 1 and roi.geometry.level_downsample == 4.25
    assert roi.geometry.origin_level0_xy == (100, 200)
    assert roi.geometry.model_size_wh == (6, 2)
    assert roi.image.shape == (2, 6, 3) and roi.valid_mask.shape == (2, 6)
    assert roi.image.flags.c_contiguous


def test_edge_clipping_precedes_default_and_explicit_resize_dimensions():
    from pathology_edge.wsi_roi import read_roi
    slide = SlideFixture()
    roi = read_roi(slide, (900, 700), 1, (50, 30))
    assert slide.calls == [((900, 700), 1, (23, 23))]
    assert roi.requested_size_wh == (50, 30)
    assert roi.geometry.read_size_wh == roi.geometry.model_size_wh == (23, 23)
    resized = read_roi(slide, (900, 700), 1, (50, 30), (10, 20))
    assert resized.geometry.read_size_wh == (23, 23)
    assert resized.image.shape == (20, 10, 3)


def test_native_edge_keeps_last_row_and_column():
    from pathology_edge.wsi_roi import read_roi
    roi = read_roi(SlideFixture(), (997, 798), 0, (128, 128))
    assert roi.geometry.read_size_wh == (3, 2)
    assert roi.image.shape == (2, 3, 3)
    np.testing.assert_array_equal(roi.image[1, 2], [2, 1, 3])


def test_resize_uses_rgb_bilinear_and_mask_nearest_without_axis_swap():
    from pathology_edge.wsi_roi import read_roi
    slide = SlideFixture()
    roi = read_roi(slide, (0, 0), 0, (8, 4), (4, 2))
    # Independent reference from the fixture pixels and the declared library kernels.
    rgba = SlideFixture().read_region((0, 0), 0, (8, 4))
    rgb = Image.alpha_composite(Image.new('RGBA', rgba.size, 'white'), rgba).convert('RGB')
    expected = np.asarray(rgb.resize((4, 2), Image.Resampling.BILINEAR))
    mask = Image.fromarray(np.asarray(rgba)[..., 3] == 255)
    np.testing.assert_array_equal(roi.image, expected)
    np.testing.assert_array_equal(roi.valid_mask, np.asarray(mask.resize((4, 2), Image.Resampling.NEAREST)))


@pytest.mark.parametrize('origin,level,size,model_size', [
    ((-1, 0), 0, (10, 10), None), ((1000, 0), 0, (10, 10), None),
    ((0.5, 0), 0, (10, 10), None), ((True, 0), 0, (10, 10), None),
    ((0, 0), -1, (10, 10), None), ((0, 0), 2, (10, 10), None),
    ((0, 0), True, (10, 10), None), ((0, 0), 0, (0, 10), None),
    ((0, 0), 0, (10, 3.5), None), ((0, 0), 0, (10,), None),
    ((0, 0), 0, (True, 10), None), ((0, 0), 0, (10, 10), (2, 0)),
    ((999, 799), 1, (10, 10), None),
])
def test_invalid_or_empty_geometry_fails_before_read(origin, level, size, model_size):
    from pathology_edge.wsi_roi import read_roi
    slide = SlideFixture()
    with pytest.raises(ValueError):
        read_roi(slide, origin, level, size, model_size)
    assert slide.calls == []


@pytest.mark.parametrize('downsample', [0, -1, float('nan'), float('inf'), True])
def test_invalid_slide_downsample_fails_before_read(downsample):
    from pathology_edge.wsi_roi import read_roi
    slide = SlideFixture()
    slide.level_downsamples = (downsample,)
    with pytest.raises(ValueError):
        read_roi(slide, (0, 0), 0, (10, 10))
    assert slide.calls == []


def test_geometry_normalizes_mutable_pairs_and_rejects_impossible_footprint():
    from pathology_edge.wsi_roi import RoiGeometry
    origin = [100, 200]
    geometry = RoiGeometry(origin, 1, 4.25, [12, 8], [6, 2], [1000, 800])
    origin[0] = 900
    assert geometry.origin_level0_xy == (100, 200)
    assert geometry.read_size_wh == (12, 8)
    with pytest.raises(FrozenInstanceError):
        geometry.level = 0
    with pytest.raises(ValueError):
        RoiGeometry((990, 790), 1, 4.25, (3, 3), (2, 2), (1000, 800))


def test_wrong_reader_image_size_is_rejected():
    from pathology_edge.wsi_roi import read_roi
    class BrokenSlide(SlideFixture):
        def read_region(self, location, level, size):
            return Image.new('RGBA', (2, 3), 'red')
    with pytest.raises(ValueError, match='size'):
        read_roi(BrokenSlide(), (0, 0), 0, (10, 10))


def test_footprint_consumer_rejects_unknown_mode_before_learner_call():
    from pathology_edge.wsi_roi import RoiGeometry, roi_patch_manifest
    g = RoiGeometry((0, 0), 0, 1., (100, 100), (100, 100), (1000, 800))
    with pytest.raises(ValueError, match='mode'):
        roi_patch_manifest(g, 'arbitrary')


def test_adapter_and_consumer_require_validated_geometry():
    from pathology_edge.learner_wsi import roi_points_to_level0
    from pathology_edge.wsi_roi import roi_patch_manifest
    with pytest.raises(ValueError, match='RoiGeometry'):
        roi_points_to_level0(np.array([[0, 0]]), {})
    with pytest.raises(ValueError, match='RoiGeometry'):
        roi_patch_manifest({}, 'no_overlap')
