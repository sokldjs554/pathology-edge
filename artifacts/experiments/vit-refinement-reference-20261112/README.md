# Submitted residual head: development reference comparison

This is a **development-environment run**, not the user's Codespaces execution. It uses the user's submitted `LocalResidualHead`, accepted in source commit `1744544ec2f88bff1e3eac8a7bfe99b9335d9d48`. The 13-test user report is separate from this training evidence.

| Validation region | SmallViT | + User residual head | Change |
|---|---:|---:|---:|
| Whole image | 0.570565 | 0.583877 | +0.013312 |
| 128px tile boundary | 0.558802 | 0.550175 | −0.008627 |
| Interior | 0.560474 | 0.576742 | +0.016268 |

The selected checkpoints are epoch12/threshold0.35 and epoch13/threshold0.35. Across the same10 validation images, whole-image Dice increases on7 and decreases on3; all rows are in `per-image.json`. Whole-image mean improvement does not imply boundary improvement. `09_1` declines again in this new comparison, but the compared models and seed differ from the earlier CNN/ViT run.

Seed20261116, train33/validation10,16epochs×20steps,batch8,crop128,Adam0.001,BCE+the accepted soft Dice are fixed. The common ViT initial tensor hash is identical, and both workers have the same crop/augmentation trace. ViT dropout is zero. Parameters:33,632→33,785. Both models start from scratch; no old checkpoint is reused. The learned head's153 parameters are nonzero in the selected checkpoint; the final layer started at zero.

Environment: EPYC9V74,5 logical CPUs,4 Torch threads,Python3.12.14,CPU Torch2.15.0. Training+epoch-validation time:12.544s→22.520s. Median validation-image CPU pipeline:19.553ms→28.085ms. Absolute whole-worker peak RSS:465.398→481.566MiB. Timings are descriptive observations, not a controlled speed benchmark. Detailed scope and original float values are in the reports.

`evidence.zip` contains71 payload files plus `manifest.json`: frozen source/runner, protocols, preflight, both checkpoints,16-epoch histories,20 saved validation probabilities, source/data hashes, original before/after records, and launcher records. The local exercise file is preserved and its class AST matches the pinned accepted class. Its code is not executed as an alternate source; pinned imports/helper remain in use. Archive SHA and audit checks are in `review.json`.

A read-only audit of the extracted `run` directory can relocate the data:

```bash
python scripts/run_refinement_comparison.py --summarize /path/to/extracted/run --data-override data
```

Run this from the repository root, using the tested project Python environment. It recalculates60 validation metric regions from saved probabilities and ground truth without training or inference. Both new-source and original-checkout/ignored-exercise preservation checks passed. The uploaded `research-evidence.zip` and prior public model outputs are unchanged.

The same previously used validation10 images/2groups select epoch and threshold, with one new paired seed. No independent test, external, WSI-wide ground-truth or clinical validation was performed. Do not infer a generally superior architecture or a proven biological cause. The residual head operates within each128px input tile; it does not exchange pixels across separate inference tiles.
