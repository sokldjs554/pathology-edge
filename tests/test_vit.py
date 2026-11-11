"""Protect spatial layout and training behavior of the small ViT baseline."""

import pytest
import torch
from torch.nn import functional as F

from pathology_edge.vit import SmallViTSegmenter


def test_unpatchify_preserves_patch_pixel_and_batch_positions():
    # Hand-labelled positions distinguish token order from within-patch order.
    tokens = torch.zeros(2, 6, 64)
    tokens[0, 0, 0] = 1
    tokens[0, 0, 1] = 2
    tokens[0, 0, 8] = 3
    tokens[0, 1, 0] = 4
    tokens[0, 2, 63] = 5
    tokens[0, 3, 0] = 6
    tokens[0, 4, 9] = 7
    tokens[0, 5, 63] = 8
    tokens[1, 1, 10] = 9
    tokens[1, 5, 63] = 10

    expected = torch.zeros(2, 1, 16, 24)
    expected[0, 0, 0, 0] = 1
    expected[0, 0, 0, 1] = 2
    expected[0, 0, 1, 0] = 3
    expected[0, 0, 0, 8] = 4
    expected[0, 0, 7, 23] = 5
    expected[0, 0, 8, 0] = 6
    expected[0, 0, 9, 9] = 7
    expected[0, 0, 15, 23] = 8
    expected[1, 0, 1, 10] = 9
    expected[1, 0, 15, 23] = 10

    actual = SmallViTSegmenter()._unpatchify(tokens, 2, 3)
    torch.testing.assert_close(actual, expected)


@pytest.mark.parametrize("shape", [(2, 3, 128, 128), (1, 3, 17, 26), (1, 3, 1, 1)])
def test_forward_returns_finite_logits_at_original_resolution(shape):
    model = SmallViTSegmenter().eval()
    with torch.no_grad():
        logits = model(torch.randn(shape))
    assert logits.shape == (shape[0], 1, shape[2], shape[3])
    assert torch.isfinite(logits).all()


def test_partial_patches_use_right_bottom_zero_padding_then_crop():
    torch.manual_seed(7)
    model = SmallViTSegmenter().eval()
    x = torch.randn(1, 3, 17, 26)
    with torch.no_grad():
        actual = model(x)
        padded = model(F.pad(x, (0, 6, 0, 7)))
    torch.testing.assert_close(actual, padded[:, :, :17, :26])


def test_forward_returns_raw_logits():
    model = SmallViTSegmenter().eval()
    with torch.no_grad():
        model.head.weight.zero_()
        model.head.bias.fill_(2.0)
        actual = model(torch.zeros(1, 3, 9, 10))
    torch.testing.assert_close(actual, torch.full((1, 1, 9, 10), 2.0))


def test_segmentation_loss_reaches_embedding_attention_positions_and_head():
    torch.manual_seed(9)
    model = SmallViTSegmenter()
    x = torch.randn(2, 3, 17, 26)
    target = torch.randint(0, 2, (2, 1, 17, 26)).float()
    F.binary_cross_entropy_with_logits(model(x), target).backward()

    parameters = [model.patch_embed.weight, model.position_embedding,
                  model.head.weight, model.norm.weight]
    parameters.extend(layer.self_attn.in_proj_weight for layer in model.layers)
    for parameter in parameters:
        assert parameter.grad is not None
        assert torch.isfinite(parameter.grad).all()
        assert torch.count_nonzero(parameter.grad) > 0


def test_transformer_layers_start_with_distinct_attention_weights():
    torch.manual_seed(11)
    model = SmallViTSegmenter()
    first = model.layers[0].self_attn.in_proj_weight
    second = model.layers[1].self_attn.in_proj_weight
    assert first.data_ptr() != second.data_ptr()
    assert not torch.equal(first, second)


def test_state_dict_round_trip_preserves_logits(tmp_path):
    torch.manual_seed(13)
    original = SmallViTSegmenter().eval()
    x = torch.randn(1, 3, 17, 26)
    with torch.no_grad():
        expected = original(x)
    path = tmp_path / "vit.pt"
    torch.save(original.state_dict(), path)
    restored = SmallViTSegmenter().eval()
    restored.load_state_dict(torch.load(path, weights_only=True))
    with torch.no_grad():
        actual = restored(x)
    torch.testing.assert_close(actual, expected, rtol=0, atol=0)


@pytest.mark.parametrize("x", [
    None,
    torch.zeros(3, 8, 8),
    torch.zeros(1, 1, 8, 8),
    torch.zeros(0, 3, 8, 8),
    torch.zeros(1, 3, 0, 8),
    torch.zeros(1, 3, 8, 0),
    torch.zeros(1, 3, 8, 8, dtype=torch.uint8),
    torch.zeros(1, 3, 8, 8, dtype=torch.complex64),
])
def test_forward_rejects_inputs_outside_nonempty_float_bchw_rgb_contract(x):
    with pytest.raises(ValueError, match="floating|BCHW|RGB|nonempty"):
        SmallViTSegmenter()(x)


def test_forward_accepts_token_limit():
    model = SmallViTSegmenter().eval()
    with torch.no_grad():
        actual = model(torch.zeros(1, 3, 256, 256))
    assert actual.shape == (1, 1, 256, 256)


@pytest.mark.parametrize("shape", [(1, 3, 257, 256), (1, 3, 8, 8200)])
def test_forward_rejects_more_than_1024_tokens_after_padding(shape):
    with pytest.raises(ValueError, match="1024.*tokens|tokens.*1024"):
        SmallViTSegmenter()(torch.zeros(shape))
