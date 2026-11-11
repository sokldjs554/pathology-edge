"""Provided integration and preflight for the user-owned local residual head."""
import hashlib
import json
from math import prod

import torch
from torch import nn

from .vit import SmallViTSegmenter

REFINEMENT_SEED = 20261116


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _check_output(output, logits):
    _require(isinstance(output, torch.Tensor) and output.shape == logits.shape,
             'Refinement logits must preserve B1HW shape')
    _require(output.dtype == logits.dtype and output.device == logits.device,
             'Refinement logits must preserve dtype and device')
    _require(output.is_floating_point() and bool(torch.isfinite(output).all()),
             'Refinement logits must be finite floating values')


class RefinedViTSegmenter(nn.Module):
    """Apply the learner head to the existing ViT's raw output logits.

    ``head_factory`` permits transparent synthetic heads in framework tests.
    Experiment workers always use the user's LocalResidualHead.
    """
    def __init__(self, *, head_factory=None):
        super().__init__()
        # The backbone consumes exactly the baseline's initialization RNG first.
        self.backbone = SmallViTSegmenter()
        if head_factory is None:
            from .learner_refinement import LocalResidualHead
            head_factory = LocalResidualHead
        self.refinement_head = head_factory()
        _require(isinstance(self.refinement_head, nn.Module), 'Expected a refinement module')

    @property
    def config(self):
        return dict(backbone=self.backbone.config, refinement='learner_local_residual_head',
                    head_channels=[1, 8, 1], head_kernel_size=3, head_parameters=153)

    def forward(self, inputs):
        logits = self.backbone(inputs)
        output = self.refinement_head(logits)
        _check_output(output, logits)
        return output


def backbone_sha256(model):
    """Hash named tensor values, shapes and dtypes without torch.save metadata."""
    backbone = model.backbone if isinstance(model, RefinedViTSegmenter) else model
    digest = hashlib.sha256()
    for name, tensor in sorted(backbone.state_dict().items()):
        value = tensor.detach().cpu().contiguous()
        metadata = json.dumps([name, list(value.shape), str(value.dtype)], separators=(',', ':'))
        digest.update(metadata.encode() + b'\n')
        digest.update(value.view(torch.uint8).numpy().tobytes())
    return digest.hexdigest()


def validate_local_residual_head(head):
    """Fail before training on an incomplete or incompatible learner component.

    This checks the declared structure and initial identity contract. The opt-in
    learner exercises additionally check the learned transformation and gradients.
    No reference implementation of the user-owned forward method is supplied.
    """
    for name, channels in [('conv1', (1, 8)), ('conv2', (8, 1))]:
        layer = getattr(head, name, None)
        _require(isinstance(layer, nn.Conv2d), f'Expected {name} convolution')
        _require((layer.in_channels, layer.out_channels) == channels and
                 layer.kernel_size == (3, 3) and layer.stride == (1, 1) and
                 layer.padding == (1, 1) and layer.dilation == (1, 1) and
                 layer.groups == 1 and layer.padding_mode == 'zeros' and layer.bias is not None,
                 f'Incorrect {name} convolution configuration')
    _require(sum(p.numel() for p in head.parameters()) == 153,
             'The learner head must have exactly 153 parameters')
    _require(all(p.requires_grad and bool(torch.isfinite(p).all()) for p in head.parameters()),
             'Learner head parameters must be finite and trainable')
    _require(torch.count_nonzero(head.conv2.weight).item() == 0 and
             torch.count_nonzero(head.conv2.bias).item() == 0,
             'The final convolution must start with zero weight and bias')
    with torch.no_grad():
        for shape in [(1, 1, 1, 1), (2, 1, 7, 9)]:
            logits = torch.linspace(-3, 3, steps=prod(shape)).reshape(shape)
            original = logits.clone()
            output = head(logits)
            _check_output(output, logits)
            _require(torch.equal(logits, original), 'Learner head modified input logits in place')
            _require(torch.equal(output, original), 'Learner head must initially preserve raw logits exactly')


def refinement_preflight(seed=REFINEMENT_SEED):
    """Validate user code and identical initialization before either arm trains."""
    _require(type(seed) is int and seed == REFINEMENT_SEED, 'Refinement seed is frozen at 20261116')
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(seed)
        baseline = SmallViTSegmenter()
        torch.manual_seed(seed)
        refined = RefinedViTSegmenter()
        validate_local_residual_head(refined.refinement_head)
        baseline_hash, refined_hash = backbone_sha256(baseline), backbone_sha256(refined)
        _require(baseline_hash == refined_hash, 'Initial ViT backbone weights differ')
        parameters = {'small_vit': sum(p.numel() for p in baseline.parameters()),
                      'small_vit_refined': sum(p.numel() for p in refined.parameters())}
        _require(parameters == {'small_vit': 33632, 'small_vit_refined': 33785},
                 'Unexpected refinement comparison parameter counts')
    return dict(seed=seed, all_checks_passed=True, parameter_counts=parameters,
                initial_backbone_sha256=baseline_hash)
