"""Protect loss selection, provenance and training output safety."""
import hashlib
import json
import math
import sys

import numpy as np
import pytest
import torch
from PIL import Image

from pathology_edge import cli, experiment


@pytest.fixture
def tiny_data(tmp_path):
    root = tmp_path / "data"
    root.mkdir()
    records = []
    for i, split in enumerate(("train", "validation")):
        rgb = np.full((128, 128, 3), [150 + i, 90, 140], dtype=np.uint8)
        mask = np.zeros((128, 128), dtype=np.uint8)
        mask[32:80, 40:90] = 255
        image, label = root / f"image{i}.png", root / f"mask{i}.png"
        Image.fromarray(rgb).save(image)
        Image.fromarray(mask).save(label)
        records.append(dict(id=str(i), group_id=str(i), split=split,
                            image=image.name, mask=label.name,
                            image_sha256=experiment.sha256(image),
                            mask_sha256=experiment.sha256(label)))
    (root / "manifest.json").write_text(json.dumps({"records": records}))
    return root


def test_default_loss_keeps_bce_plus_image_dice():
    loss, label = experiment._training_loss("baseline")
    x = torch.zeros((1, 1, 2, 2), dtype=torch.float64, requires_grad=True)
    y = torch.tensor([[[[1., 0.], [1., 0.]]]], dtype=torch.float64)
    value = loss(x, y)
    assert value.item() == pytest.approx(math.log(2) + 0.4)
    value.backward()
    assert torch.isfinite(x.grad).all()
    assert label == "BCE + soft Dice"


def test_bce_only_removes_dice_and_keeps_gradients():
    loss, label = experiment._training_loss("bce_only")
    x = torch.zeros((1, 1, 2, 2), dtype=torch.float64, requires_grad=True)
    y = torch.tensor([[[[1., 0.], [1., 0.]]]], dtype=torch.float64)
    value = loss(x, y)
    assert value.item() == pytest.approx(math.log(2))
    value.backward()
    torch.testing.assert_close(x.grad, torch.tensor([[[[-.125, .125], [-.125, .125]]]], dtype=x.dtype))
    assert label == "BCE only"


def test_learner_term_is_added_to_bce(monkeypatch):
    from pathology_edge import learner_losses
    # The real learner function is intentionally pending. This double tests
    # the consumer's addition/routing, not the user's future mathematics.
    monkeypatch.setattr(learner_losses, "soft_dice_loss",
                        lambda x, y: x.square().mean() + 0.125)
    loss, _ = experiment._training_loss("learner_dice")
    x = torch.zeros((1, 1, 2, 2), requires_grad=True)
    value = loss(x, torch.zeros_like(x))
    assert value.item() == pytest.approx(math.log(2) + 0.125)
    value.backward()
    assert torch.isfinite(x.grad).all()


def test_unknown_loss_rejected_before_data_or_output(tmp_path):
    out = tmp_path / "untouched"
    with pytest.raises(ValueError, match="loss"):
        experiment.train(tmp_path / "missing", out, loss_mode="typo")
    assert not out.exists()


@pytest.mark.parametrize("name", ["model.pt", "training.json", "protocol.json",
                                 "evaluation.json", "evaluation_lock.json"])
def test_saved_experiment_cannot_be_overwritten(tmp_path, name):
    protected = tmp_path / name
    protected.write_bytes(b"original")
    with pytest.raises(RuntimeError):
        experiment.train(tmp_path / "missing", tmp_path)
    assert protected.read_bytes() == b"original"


def test_cli_bce_training_records_actual_mode(tiny_data, tmp_path, monkeypatch):
    out = tmp_path / "run"
    monkeypatch.setattr(sys, "argv", ["pathology-edge", "train", "--data", str(tiny_data),
                                    "--output", str(out), "--epochs", "1", "--steps", "1",
                                    "--loss", "bce_only"])
    cli.main()
    report = json.loads((out / "training.json").read_text())
    assert report["config"]["loss"] == "BCE only"
    assert report["config"]["loss_mode"] == "bce_only"
    assert report["config"]["test_used_for_selection"] is False
    assert len(report["history"]) == 1
    assert report["train_images"] == report["validation_images"] == 1
    assert report["model_sha256"] == hashlib.sha256((out / "model.pt").read_bytes()).hexdigest()
    assert not (out / "evaluation.json").exists()


def test_learner_run_records_source_hash(tiny_data, tmp_path, monkeypatch):
    from pathlib import Path
    from pathology_edge import learner_losses
    monkeypatch.setattr(learner_losses, "soft_dice_loss", lambda x, y: x.square().mean())
    out = tmp_path / "learner"
    report = experiment.train(tiny_data, out, epochs=1, steps=1, loss_mode="learner_dice")
    assert report["config"]["loss_mode"] == "learner_dice"
    assert report["config"]["loss_source_sha256"] == hashlib.sha256(
        Path(learner_losses.__file__).read_bytes()).hexdigest()
    assert report["config"]["loss"] == "BCE + learner soft Dice"


def test_nontraining_command_rejects_loss_option(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["pathology-edge", "prepare", "--loss", "bce_only"])
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2
    assert "train" in capsys.readouterr().err


@pytest.mark.parametrize("kind", ["not_tensor", "integer", "rank", "channels", "empty",
                                 "shape", "dtype", "nonbinary", "nan", "inf_target",
                                 "smooth_zero", "smooth_nan", "smooth_bool"])
def test_provided_loss_validation_rejects_invalid_inputs(kind):
    from pathology_edge.learner_losses import _validate_loss_inputs
    x, y, smooth = torch.zeros(1, 1, 2, 2), torch.zeros(1, 1, 2, 2), 1.0
    if kind == "not_tensor": x = []
    elif kind == "integer": x = x.long()
    elif kind == "rank": x = x[0]
    elif kind == "channels": x = x.expand(1, 2, 2, 2)
    elif kind == "empty": x = x[:0]
    elif kind == "shape": y = y[:, :, :1]
    elif kind == "dtype": y = y.double()
    elif kind == "nonbinary": y.fill_(0.5)
    elif kind == "nan": x.fill_(float("nan"))
    elif kind == "inf_target": y.fill_(float("inf"))
    elif kind == "smooth_zero": smooth = 0
    elif kind == "smooth_nan": smooth = float("nan")
    elif kind == "smooth_bool": smooth = True
    with pytest.raises(ValueError):
        _validate_loss_inputs(x, y, smooth)
