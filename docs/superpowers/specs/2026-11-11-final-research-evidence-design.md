# Final research evidence follow-up design

User approved all four ranked follow-ups on 2026-11-11. Preserve the completed C++ and ViT work and all existing scientific/demo outputs. Keep user-owned implementation and execution pending until actual submissions; interview prose remains deferred.

## Approach and scope
Extend existing frozen runners, not the production/demo pipeline. Archive the user's existing Codespaces C++/ViT runs without retraining. The shared workspace has development-reference runs only; it must not label those as the user's runs. Generate portable, hash-checked evidence and read-only error analysis from saved validation probabilities. Compare one worst loss and one largest improvement selected by per-image Dice delta, with all ten rows retained. Images show GT, predictions and FP/FN, never inferred biological causes.

Freeze three paired architecture seeds 20261113, 20261114, 20261115 before additional training, same 33 train / 10 validation split, 16 epochs x 20 steps, crop128, batch8, Adam .001, BCE+accepted learner Dice, thresholds .35/.5/.65, four Torch threads. The original seed is reusable only with audited matching data, scientific protocol, effective source and environment. Do not pool reference and user environments. Run order alternates across added pairs. Timing remains descriptive. Test images are hashed, never decoded/evaluated by these runs. No external or clinical claims.

User implementation is reserved: select one small model-component change after actual error evidence is reviewed; provide contract and tests before an answer. We may prepare the comparison machinery, but must not mark this user task complete or invent an error-driven improvement before their source arrives.

## Completion evidence
1. Exporter tested for relocation, tampering, symlinks, missing/partial runs and overwrite refusal; actual user export/import pending. Refresh Docker evidence at a pinned source including new code via existing GitHub workflow.
2. Read-only saved-output audit and static comparison figures; full-image and chosen crop coordinates/counts reproducible. Development-reference report may be produced now and clearly labeled; user's 09_1 / 09_6 analysis waits for their files.
3. One user-owned model change plus controlled comparison, gated by observed errors and user code. No automatic change or success claim.
4. Three audited paired seeds with all results, sample SD, paired deltas and wins/ties/losses; no cherry-picking, no mixing different environments/sources. Development run separate from future user's run.

## Constraints
Fresh output directories only; no replacing learned functions, training outputs, test results, public demo or model.pt. User can export from existing original checkout without git pull/reset/stash. No dependencies added. Archives hold allowlisted experiment files only, reject symlinks and traversal, include SHA256 manifest and do not execute code from archives. UI is out of scope. Existing Docker results remain valid for their old source.
