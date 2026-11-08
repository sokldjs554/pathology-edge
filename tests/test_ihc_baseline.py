"""Guard the split, point-label, and frozen-model boundaries of the IHC study."""
import importlib
import importlib.util

import numpy as np
import pytest
from PIL import Image


def module():
    assert importlib.util.find_spec("pathology_edge.ihc_baseline") is not None, "IHC baseline is not implemented"
    return importlib.import_module("pathology_edge.ihc_baseline")


def test_case_split_is_order_independent_and_never_splits_a_case():
    m = module()
    train = [f"case_{case:04d}_region_0_patch_{patch}_O.png" for case in range(1, 7) for patch in range(2)]
    test = ["case_0007_region_0_patch_0_O.png"]
    assignment, info = m.make_split(train, test, seed=19, validation_cases=2)
    reordered, _ = m.make_split(train[::-1], test, seed=19, validation_cases=2)
    assert assignment == reordered
    assert len(info["train"]["case_ids"]) == 4
    assert len(info["validation"]["case_ids"]) == 2
    assert info["test"]["case_ids"] == ["case_0007"]
    for case in range(1, 7):
        assert assignment[f"case_{case:04d}_region_0_patch_0_O.png"] == assignment[f"case_{case:04d}_region_0_patch_1_O.png"]


def test_split_rejects_same_case_even_when_images_differ():
    with pytest.raises(ValueError, match="case"):
        module().make_split(["case_0001_region_0_patch_0_O.png", "case_0002_region_0_patch_0_O.png"],
                            ["case_0001_region_2_patch_2_O.png"], validation_cases=1)


def masks():
    return {name: np.zeros((8, 8), np.uint8) for name in (
        "positive_tumor_cell", "negative_tumor_cell", "normal_cell", "others_positive", "others_negative")}


def test_point_masks_preserve_xy_and_class_without_inventing_boundaries():
    ms = masks()
    ms["positive_tumor_cell"][1, 5] = 255
    ms["others_negative"][6, 2] = 255
    xy, labels = module().read_points(ms)
    np.testing.assert_array_equal(xy, [[5, 1], [2, 6]])
    np.testing.assert_array_equal(labels, [0, 3])


@pytest.mark.parametrize("bad", ["area", "normal", "collision", "value"])
def test_incompatible_labels_fail_closed(bad):
    ms = masks()
    ms["positive_tumor_cell"][1, 1] = 255
    if bad == "area":
        ms["positive_tumor_cell"][1:3, 1:3] = 255
    elif bad == "normal":
        ms["normal_cell"][4, 4] = 255
    elif bad == "collision":
        ms["negative_tumor_cell"][1, 1] = 255
    else:
        ms["negative_tumor_cell"][4, 4] = 128
    with pytest.raises(ValueError):
        module().read_points(ms)


def test_local_color_features_clip_at_image_edges_and_keep_hue_finite():
    m = module()
    red = np.zeros((20, 20, 3), np.uint8)
    red[..., 0] = 255
    features = m.extract_features(red, np.array([[0, 0], [10, 10]]))
    assert features.shape == (2, len(m.feature_names()))
    assert np.isfinite(features).all()
    np.testing.assert_allclose(features[0], features[1], atol=1e-12)
    np.testing.assert_allclose(features[0, :3], [1, 0, 0])


def test_training_only_scaler_and_json_export_reproduce_predictions():
    m = module()
    x = np.array([[-3., -3.], [-3., -2.], [-3., 3.], [-3., 2.], [3., -3.], [3., -2.], [3., 3.], [3., 2.]])
    y = np.array([0, 0, 1, 1, 2, 2, 3, 3])
    # A held-out shifted distribution must not alter the fitted scaler.
    xv = np.array([[-1.5, -1.75], [-1.5, 2.25], [2.5, -1.75], [2.5, 2.25]])
    model, selection = m.select_model(x, y, xv, np.arange(4), candidates=(1.,))
    np.testing.assert_allclose(model["scaler"]["mean"], [0., 0.])
    np.testing.assert_allclose(model["scaler"]["scale"], [3., np.sqrt(6.5)])
    assert selection["selected_C"] == 1.
    np.testing.assert_array_equal(m.predict_proba(xv, model).argmax(axis=1), [0, 1, 2, 3])
    assert selection["export_probability_max_abs_error"] < 1e-12


def test_confusion_and_ratio_use_tumor_only_denominator():
    m = module()
    truth = np.array([0, 0, 1, 1, 2, 2, 3, 3])
    pred = np.array([0, 1, 1, 1, 3, 2, 3, 0])
    result = m.classification_metrics(truth, pred)
    assert result["confusion_matrix"] == [[1, 1, 0, 0], [0, 2, 0, 0], [0, 0, 1, 1], [1, 0, 0, 1]]
    assert result["macro_f1"] == pytest.approx((.5 + .8 + 2 / 3 + .5) / 4)
    ratios = m.tumor_ratios(truth, pred)
    assert ratios["gt"] == .5
    assert ratios["predicted"] == .4
    assert ratios["absolute_error_percentage_points"] == pytest.approx(10.)
    assert m.tumor_ratios(np.array([2, 3]), np.array([2, 3]))["absolute_error_percentage_points"] is None


def test_examples_show_multiple_cases_and_crop_actual_pixels(tmp_path):
    # Selecting the first eight cells would show only case 1 and hide variation.
    m = module()
    data = tmp_path / "data"
    (data / "images").mkdir(parents=True)
    cells = []
    for i, case in enumerate([1] * 8 + [2, 2, 3, 3]):
        name = f"case_{case:04d}_region_0_patch_{i}_O.png"
        pixels = np.full((224, 224, 3), i, np.uint8)
        Image.fromarray(pixels).save(data / "images" / name)
        cells.append({"image": name, "case_id": f"case_{case:04d}", "x": 0, "y": 223})
    target = np.zeros(12, dtype=int)
    output = tmp_path / "public"
    examples = m._export_examples(data, output, cells, target, target, np.tile([1., 0, 0, 0], (12, 1)))
    assert len(examples) == 8
    assert len({example["case_id"] for example in examples}) == 3
    for example in examples:
        source = np.asarray(Image.open(output / "examples" / (example["id"] + "-source.png")))
        crop = np.asarray(Image.open(output / "examples" / (example["id"] + "-crop.png")))
        x0, y0, x1, y1 = example["crop_bbox"]
        np.testing.assert_array_equal(crop, source[y0:y1, x0:x1])
        assert example["point_in_crop"] == [0, 47]
