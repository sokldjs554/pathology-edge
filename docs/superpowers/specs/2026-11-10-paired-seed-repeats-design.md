# Paired seed repetition design

The user approved proceeding through the job-match priorities, delegated routine implementation and asked for one user task at a time. WSI coordinate code and crop interpretation are now complete. This is priority 3: repeat the existing BCE-only versus BCE + user soft Dice comparison. Implementation remains in Python/Codespaces with the existing TinyUNet and training CLI. Protocol details below are Codex choices, not a fabricated user design decision.

## Approaches

1. Reuse the previously seen 20261107 pair and add two seeds: cheaper but mixes historical environments/source and includes a known outcome.
2. **Run both arms freshly for three new fixed seeds:** chosen; consistent frozen source/data, no result-based seed selection, modest CPU cost.
3. Add a ViT/model architecture now: optional later comparison; changes both scope and CPU cost before the existing hypothesis is repeated.

## Protocol and deliverable

A standalone `scripts/run_loss_repeats.py` downloaded into ignored `work/` must run against the user's existing source without Git pulls or overwriting their loss/coordinate files. Freeze all package Python sources, the runner, Git HEAD/status/diff, manifest and reference controls into a new output directory before launching fresh subprocesses. All children import the frozen source via PYTHONPATH and run the existing train CLI; no train-loop edits.

Seeds are exactly `[20261110,20261111,20261112]`, chosen before new outcomes. Each has `bce_only` and `learner_dice`; order is A/B, B/A, A/B to partially alternate order. Fix 16 epochs, 20 steps/epoch, existing 33/10 split, batch 8, TinyUNet width 8, optimizer/augmentation and thresholds .35/.5/.65. Choose each arm's epoch/threshold by the existing maximum validation image-macro Dice, preserving first-tie behavior. The validation set has already been used for selection; repetitions do not make it independent test evidence. Existing data loader hashes all 50 source image/label files, but only train/validation are used in training/model selection. No held-out evaluation, new model architecture, clinical claim or UI refresh.

Persist the run path to `work/step42-repeat-run-path.txt` before training. Print each run/epoch and retain logs. Any error preserves partial output and records failure; no automatic retry or replacement seed. Existing output directories are refused. `--summarize RUN_DIR` is read-only: require all six runs, matching frozen controls, manifest and source hashes, environment consistency, model hashes, finite/range-valid histories, exact epoch sequence and correct selection. Do not average a partial set. Summaries show every seed/arm, mean and sample SD (ddof=1), paired B-A differences/mean/SD and wins/ties/losses, and training times. No best-seed deployment or speed/generalization claim.

Codex will validate both fixtures and a complete fresh real six-run experiment, separately labelled. User's next single task is to run the six-run command and submit its final summary. Their execution remains pending until reported.

## Limits

Three training seeds describe observed optimizer/sampling variation on the same data, not patient/group uncertainty. Existing test images were already viewed; no new test score is requested. Same-seed arm comparisons share initialization/data randomness under the unchanged training loop, but cannot establish identical hardware load. CPU timings are descriptive. Original models, published artifacts and accepted learner functions remain untouched.
