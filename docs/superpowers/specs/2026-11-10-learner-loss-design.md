# Learner loss and one controlled ablation

The user authorized sequential portfolio improvements and reserved meaningful
implementation for themselves. STEP_34 training and model-selection interpretation
are now confirmed. This small addition prepares STEP_35; it does not fill in the
learner's mathematical function or claim their next tests/training have run.

Approaches considered by Codex: a loss ablation exercises tensor reductions and
autograd on the existing CPU model; augmentation changes emphasize sampling;
architecture changes add confounders and runtime. Codex chooses the loss ablation
within the already authorized single-comparison exercise. No new dependency,
GPU, UI, dataset or clinical claim is needed.

User interface: `src/pathology_edge/learner_losses.py:soft_dice_loss(logits,
target, smooth=1.0) -> torch.Tensor`. Codex supplies validation of nonempty
floating `(N,1,H,W)` tensors, matching shape/dtype/device, finite logits, binary
targets, and a finite positive real smoothing constant. The user writes only the
calculation after validation: sigmoid probabilities, per-image spatial/channel
Dice with smoothing in numerator and denominator, then batch-mean loss. Preserve
dtype/device/autograd; no threshold, NumPy conversion or detachment. Keep the
body unimplemented until the user's submission.

Codex provides opt-in learner contracts and a small training extension:
`--loss baseline|bce_only|learner_dice`. Default baseline retains existing loss,
protocol contents and numerical behavior. BCE-only is the control; learner mode
adds the user's Dice loss to mean BCE-with-logits. Variant protocols identify the
mode and the learner source hash where applicable. Reject reuse of saved model,
protocol or evaluation output. New modes are training-only CLI options.

The eventual user comparison runs both arms in the same Codespace, with identical
seed 20261107, 16 epochs, 20 steps, data, model, optimizer and selection rules.
Only Dice-term inclusion changes. Select on validation, never on the previously
opened test set. No improvement is promised. Current user task is writing one
function and running its contract tests; comparison training follows review.

Codex may independently test infrastructure and run baseline/BCE-only validation
experiments while the learner writes their function, with separate evidence.
Existing `artifacts/`, published `dist/`, model.py and user work stay unchanged.
