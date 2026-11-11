# Three paired refinement seeds: predeclared protocol

This is a **new three-seed experiment**, declared before additional training.
It evaluates the user's completed `LocalResidualHead` against the same small
ViT baseline. It does not reuse or pool either previous seed-20261116 result.
Every arm in the new experiment trains again from scratch from one exact frozen
Python source snapshot in one worker environment.

## Seeds and execution order

| Seed | First arm | Second arm |
| --- | --- | --- |
| 20261116 | SmallViT baseline | SmallViT + user head |
| 20261117 | SmallViT + user head | SmallViT baseline |
| 20261118 | SmallViT baseline | SmallViT + user head |

These seeds are fixed; there is no seed search or replacement of a failed seed.
Alternating order partially counterbalances execution order (three pairs cannot
give an equal number of first positions to both arms). All six arms must finish
and pass the saved-output audits before aggregate success is reported.
Failed or partial attempts remain failed and are preserved in their own folders.

The old `run_refinement_comparison.py` launcher still uses only seed 20261116.
The only model-source change needed for this experiment is that the provided
preflight now accepts the three declared seeds. The head implementation,
backbone, training code, data and existing results are unchanged. Because that
preflight changes a frozen source hash, the repeat runner trains **all three
pairs anew** and labels them `new-three-seed-experiment`; it does not claim
byte-identical source with the historical pair.

## Historical reference and provenance

The development reference is:

```text
/workspace/pathology-edge/work/refinement-source.l95sfsd4/work/my-vit-refinement.664c19527955
```

Its frozen source came from commit
`1744544ec2f88bff1e3eac8a7bfe99b9335d9d48`. Its worker used Python 3.12.14,
PyTorch 2.15.0+cpu, an AMD EPYC 9V74, five visible CPUs and four Torch threads.
The earlier user-supplied seed-20261116 run used a different environment and
remains a separate result. A seed number does not make their measurements
exchangeable or supply another independent seed.

The optional `--reference` argument independently audits the historical
seed-20261116 pair, records its summary, protocol and complete evidence hashes,
and verifies the original reference files are unchanged after the new run.
It never copies that pair into the aggregate or skips new training. The caller
must label the new run `development-reference` or `user-supplied`. Reference
metadata is contextual; all three newly trained pairs must match the new run's
actual worker fingerprint exactly. The new run can be audited after relocation
without access to the historical reference path.

## Fixed comparison and selection

- Baseline: from-scratch `SmallViTSegmenter`, 33,632 trainable parameters.
- Refined: the same backbone plus the user's 153-parameter head, 33,785 total.
  The head starts as an exact identity on raw logits. Both the head and backbone
  train end to end.
- Within each seed, both arms start with identical backbone tensors and consume
  identical crop/augmentation sequences. Different seeds must have distinct
  initial backbone hashes. All three identity/initialization preflights run
  before the first arm trains.
- Training: 16 epochs, 20 steps per epoch, batch size 8, 128-pixel crops,
  Adam with learning rate 0.001, BCE plus the user's soft Dice loss, horizontal
  and vertical flips, and 90-degree rotations. Torch uses four threads.
- Data: the existing frozen TNBC manifest, 33 training images, ten validation
  images from two groups, and seven held-out test images. No split changes.
  Manifest and image/mask hashes are checked; test images are never decoded
  for inference or model selection.
- Selection: greatest validation image-macro Dice over all 16 epochs and
  thresholds 0.35, 0.5 and 0.65, retaining the first exact tie. Each arm selects
  its own checkpoint and threshold on the same reused validation images.
- Validation: 128-pixel non-overlapping tiles, seam radius eight pixels,
  and the existing minimum component area of 12. All, boundary and interior
  Dice use the same saved probabilities and independently recounted pixels.

The repeat protocol freezes the current source, both orchestrators, manifest,
worker fingerprint, preflight results, seeds and order before training. Every
pair additionally freezes its own source and protocol and audits model hashes,
source hashes, manifest, epoch history, checkpoint/threshold selection,
initial backbone, augmentation trace, and saved probabilities. The six arms
produce 180 image-region checks (6 × 10 × 3), not 180 independent observations.
Read-only summarization uses the current trusted auditor and never executes
archived Python or loads a model checkpoint.

## Predeclared summaries and limits

For each region, report each arm's three image-macro Dice values, their mean and
sample standard deviation. Compute the refined-minus-baseline delta **within
each seed** first, then report the three paired deltas, their mean, sample
standard deviation and win/tie/loss counts. A tie is exactly zero before any
rounding. The paired delta's standard deviation is not inferred from the two
arms' marginal standard deviations.

For each of the same ten validation images, retain its group ID, all three
seed-specific baseline/refined Dice values and paired deltas for every region.
Summarize that image's paired effects over the three seeds with the same
mean, sample standard deviation and win/tie/loss counts. These are repeated
measurements of **ten unique images**, not 30 independent images. Do not pool
image-seed observations into an independent-image test or confidence interval.

Three seeds measure sensitivity to initialization and crop/augmentation
sequence on this reused validation set. They do not eliminate validation
selection bias, demonstrate significance or general superiority, or provide
independent test, external or clinical validation. Timing and absolute
whole-worker peak RSS are descriptive, with execution-order and shared-machine
variation. Parameter counts differ by 153.

## Commands

Run only after reviewing this protocol and the runner:

```bash
/workspace/work/venv/bin/python scripts/run_refinement_repeats.py \
  --repo /workspace/pathology-edge-loss \
  --data /workspace/pathology-edge/data \
  --reference /workspace/pathology-edge/work/refinement-source.l95sfsd4/work/my-vit-refinement.664c19527955 \
  --provenance-label development-reference
```

The runner prints a fresh `RUN_DIR` under this checkout's `work/`. An explicit
`--output` is supported but must not already exist. Audit later without writes
or inference:

```bash
/workspace/work/venv/bin/python scripts/run_refinement_repeats.py \
  --summarize /absolute/path/to/completed/run \
  --data-override /workspace/pathology-edge/data
```

`summary.json` contains the six architecture rows, three audited pair summaries,
paired regional statistics and ten per-image effect summaries. The optional
reference's summary appears separately in `reference-summary.json` and never
contributes to those statistics.
