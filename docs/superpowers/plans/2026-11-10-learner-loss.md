# Learner Loss Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prepare one user-owned differentiable loss exercise and controlled CPU ablation.
**Architecture:** Preserve the legacy loss as default; add an opt-in learner module and loss selector to the existing train CLI. Keep learner math as a stub.
**Tech Stack:** Existing Python/PyTorch/pytest, no new dependencies.
**Spec:** [Learner loss design](../specs/2026-11-10-learner-loss-design.md).

## Global Constraints

- User implements only `soft_dice_loss`; Codex never fills its answer.
- Keep original model.py, saved/public results and default protocol unchanged.
- Variants use fresh output; no test evaluation or UI deployment.
- Same seed 20261107, epochs 16, steps 20; later user comparisons run on one runtime.
- Separate Codex tests/runs from pending user code/tests/training.

## Review Focus

- Batch Dice must be image-macro, not one pooled batch; check hand-computed 10/21 case.
- Gradients must remain connected and finite, including extreme logits; gradcheck and sign contracts.
- Baseline selection must remain the old function and produce identical stored protocol/weights.
- Pending learner code must not break ordinary runs; learner tests opt in and selector is lazy.
- Refuse overwriting any existing training/evaluation outputs; parser rejects loss flags outside train.

## Task 1: Exercise, training integration and evidence

**Files:** create `src/pathology_edge/learner_losses.py`, `tests/learner/test_soft_dice_loss.py`, `tests/test_training_losses.py`, `docs/STEP_35.md`; modify `experiment.py`, `cli.py` and progress docs; add `artifacts/learning/step35-preparation.json`.
**Interfaces:** learner `soft_dice_loss(logits: Tensor, target: Tensor, smooth: float=1.0)`; `_training_loss(mode)` returns callable plus protocol label; `train(..., loss_mode='baseline')`; `--loss` CLI option.

- [x] Write/run infrastructure tests red: real BCE value/gradient, legacy equivalence, learner routing (test-only substitute), invalid mode/command, protected outputs, real one-epoch training report.
- [x] Supply validation and learner stub; add opt-in contracts for 0.4 scalar example, empty foreground, image-macro mean, smoothing, float32/64, finite extremes, backward and gradcheck. Leave learner math pending; `--run-learner` is expected red until submission.
- [x] Implement minimal selector, CLI wiring, variant metadata and output guards. Run green infrastructure and full default suite; explicitly count skipped learner tests.
- [x] Run fresh baseline and BCE-only 16-epoch Codex experiments; compare baseline history/protocol/model SHA with frozen reference and retain separate variant evidence. No held-out evaluation.
- [x] Confirm U46 interpretation, document U47 one-function task, examples/test commands and pending contribution scope. Record reference/default artifacts unchanged.
- [x] Fresh read-only whole-branch review and final checks complete; changes prepared for commit/publication through the existing main workflow.

The user-authorized staged workflow supersedes redundant skill approval menus.
The pending learner implementation is an explicit completion exception: Codex
finishes infrastructure, not the user's function or its successful contract run.

## Final result

132 default tests passed and 8 learner tests were skipped; opt-in learner tests intentionally fail until the user implements the body. Independent review found no Critical/Important issues. One deferred minor: explicit `--loss baseline` is accepted on nontraining commands although nondefault modes are rejected. No numerical effect; tracked in step35-preparation.json. Baseline and BCE-only validation runs completed; no held-out evaluation or actual learner training was performed.
