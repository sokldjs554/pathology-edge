"""Framework tests use transparent stand-ins, never the learner's answer."""
import importlib
from pathlib import Path

import pytest
import torch
from torch import nn

from pathology_edge.vit import SmallViTSegmenter
from test_model_repeats import completed_pair, data, pair  # shared evidence fixtures


def load_refinement():
    path = Path(__file__).parents[1]/'src/pathology_edge/refinement.py'
    assert path.exists(), 'Refinement wrapper is not implemented'
    return importlib.import_module('pathology_edge.refinement')


def test_identity_head_preserves_backbone_initial_weights_and_raw_output():
    refinement = load_refinement()
    torch.manual_seed(20261116)
    baseline = SmallViTSegmenter().double()
    torch.manual_seed(20261116)
    wrapped = refinement.RefinedViTSegmenter(head_factory=nn.Identity).double()
    assert refinement.backbone_sha256(baseline) == refinement.backbone_sha256(wrapped)
    x = torch.randn(2, 3, 17, 25, dtype=torch.float64)
    expected, actual = baseline(x), wrapped(x)
    assert actual.shape == (2, 1, 17, 25)
    assert actual.dtype == x.dtype and actual.device == x.device
    assert torch.equal(actual, expected)
    assert (actual < 0).any()  # raw logits, not sigmoid probabilities


class ScaleProbe(nn.Module):
    """A scalar probe, deliberately not the exercise's convolutional head."""
    def __init__(self):
        super().__init__()
        # Consumes RNG: constructing this before the backbone breaks matching.
        self.scale = nn.Parameter(torch.rand(()) + 2)

    def forward(self, logits):
        return logits * self.scale


def test_head_receives_logits_and_gradients_reach_head_and_backbone():
    refinement = load_refinement()
    torch.manual_seed(20261116)
    baseline = SmallViTSegmenter()
    torch.manual_seed(20261116)
    wrapped = refinement.RefinedViTSegmenter(head_factory=ScaleProbe)
    assert refinement.backbone_sha256(wrapped) == refinement.backbone_sha256(baseline)
    x = torch.randn(1, 3, 16, 24, requires_grad=True)
    expected = baseline(x) * wrapped.refinement_head.scale.detach()
    actual = wrapped(x)
    assert torch.equal(actual, expected)
    actual.square().mean().backward()
    assert torch.isfinite(x.grad).all() and x.grad.abs().sum() > 0
    assert wrapped.refinement_head.scale.grad.abs() > 0
    assert wrapped.backbone.patch_embed.weight.grad.abs().sum() > 0
    assert refinement.backbone_sha256(wrapped) == refinement.backbone_sha256(baseline)
    with torch.no_grad():
        wrapped.backbone.head.bias.add_(1)
    assert refinement.backbone_sha256(wrapped) != refinement.backbone_sha256(baseline)


@pytest.mark.parametrize('change', ['shape', 'dtype', 'nan'])
def test_wrapper_rejects_a_head_that_breaks_output_contract(change):
    refinement = load_refinement()
    class BrokenHead(nn.Module):
        def forward(self, logits):
            if change == 'shape':
                return logits[..., :-1]
            if change == 'dtype':
                return logits.double()
            return logits * float('nan')
    model = refinement.RefinedViTSegmenter(head_factory=BrokenHead)
    with pytest.raises(ValueError, match='logits|shape|dtype'):
        model(torch.zeros(1, 3, 16, 16))


def test_validation_rejects_standin_as_real_learner_head():
    refinement = load_refinement()
    with pytest.raises(ValueError, match='conv1|153|convolution'):
        refinement.validate_local_residual_head(nn.Identity())


def test_worker_selects_refined_wrapper_and_never_substitutes_a_finished_head(monkeypatch):
    from pathology_edge import model_comparison, learner_refinement
    class PendingHead(nn.Module):
        def __init__(self):
            raise NotImplementedError('learner still pending')
    monkeypatch.setattr(learner_refinement, 'LocalResidualHead', PendingHead)
    assert isinstance(model_comparison.build_model('small_vit'), SmallViTSegmenter)
    with pytest.raises(NotImplementedError, match='learner still pending'):
        model_comparison.build_model('small_vit_refined')
    with pytest.raises(ValueError, match='architecture'):
        model_comparison.build_model('invented')


def test_refinement_launcher_freezes_seed_and_pair(monkeypatch, tmp_path):
    import importlib.util
    import sys
    path = Path(__file__).parents[1]/'scripts/run_refinement_comparison.py'
    assert path.exists(), 'Refinement launcher is not implemented'
    spec = importlib.util.spec_from_file_location('refinement_launcher', path)
    launcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(launcher)
    calls = []
    monkeypatch.setattr(launcher.pair, 'run', lambda *args, **kwargs: calls.append((args, kwargs)))
    monkeypatch.setattr(sys, 'argv', ['run_refinement_comparison', '--repo', str(tmp_path),
                                    '--data', str(tmp_path/'data'), '--output', str(tmp_path/'work/new')])
    launcher.main()
    assert calls == [((tmp_path, tmp_path/'data', tmp_path/'work/new'),
                      dict(comparison='refinement', seed=20261116))]


def completed_refinement(pair, out, data):
    """Adapt opaque saved evidence, never constructing a real learner head."""
    completed_pair(pair, out, data, seed=20261116)
    (out/'small_vit').rename(out/'small_vit_refined')
    (out/'tiny_unet').rename(out/'small_vit')
    for architecture, count in [('small_vit', 33632), ('small_vit_refined', 33785)]:
        path = out/architecture/'training.json'
        report = pair.read(path)
        report.update(architecture=architecture, parameter_count=count, initial_backbone_sha256='a'*64)
        pair.dump(path, report)
    plan = pair.read(out/'protocol.json')
    plan.update(comparison='refinement', architectures=['small_vit', 'small_vit_refined'])
    pair.dump(out/'protocol.json', plan)
    pair.dump(out/'refinement-preflight.json', dict(seed=20261116, all_checks_passed=True,
              parameter_counts={'small_vit': 33632, 'small_vit_refined': 33785}, initial_backbone_sha256='a'*64))
    return out


def test_refinement_summary_names_actual_comparison_and_keeps_original_summary(pair, data, tmp_path):
    original = completed_pair(pair, tmp_path/'original', data)
    old = pair.summarize(original)
    assert 'delta_vit_minus_cnn' in old and 'delta_refined_minus_baseline' not in old
    run = completed_refinement(pair, tmp_path/'refinement', data)
    summary = pair.summarize(run)
    assert 'delta_refined_minus_baseline' in summary and 'delta_vit_minus_cnn' not in summary
    assert [row['parameter_count'] for row in summary['rows']] == [33632, 33785]
    assert summary['delta_refined_minus_baseline']['all'] < 0
    assert summary['initial_backbone_sha256'] == 'a'*64
    assert summary['validation_metric_regions_checked'] == 60


@pytest.mark.parametrize('change', ['seed', 'count', 'backbone', 'preflight', 'missing', 'partial'])
def test_refinement_audit_rejects_invalid_or_incomplete_controls(pair, data, tmp_path, change):
    run = completed_refinement(pair, tmp_path/'refinement', data)
    if change == 'seed':
        plan = pair.read(run/'protocol.json')
        plan['seed'] = 20261117
        pair.dump(run/'protocol.json', plan)
    elif change in ('count', 'backbone'):
        path = run/'small_vit_refined/training.json'
        report = pair.read(path)
        report['parameter_count' if change == 'count' else 'initial_backbone_sha256'] = 33632 if change == 'count' else 'b'*64
        pair.dump(path, report)
    elif change == 'preflight':
        (run/'refinement-preflight.json').unlink()
    elif change == 'missing':
        (run/'small_vit_refined/training.json').unlink()
    else:
        pair.dump(run/'status.json', dict(status='running', all_checks_passed=True))
    with pytest.raises((ValueError, FileNotFoundError)):
        pair.summarize(run)
