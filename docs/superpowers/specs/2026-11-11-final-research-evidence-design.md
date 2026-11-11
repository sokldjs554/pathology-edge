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

## User archive received / next component (2026-11-12 Asia/Seoul)
Received user research-evidence.zip SHA256136a3c0ebae3f32ee7970160700922179485b27fa40b6f07df791d4d965d3895. Integrity112files, expectedtwo model hashes, raw C++8x9 and user60region audit passed. User09_1 full FP3292→2975, FN28445→30376, allDice.4023726579→.3442200680; boundaryimproves whileinteriordeclines. Selected ROI FP164→509,FN1848→2361. User09_6 wholeFP1305→639,FN488→211 improves. Actual crops show angular local prediction pieces, but this does not establish tokenization as cause.

Choose one bounded testable hypothesis: a learned local residual head after ViT output logits can alter local shape; it cannot guarantee recovery of wholly missed nuclei. User implements LocalResidualHead.__init__/forward in learner_refinement.py. Contract: conv1 1→8, conv2 8→1, both kernel3/stride1/padding1/bias; ReLU between, residualadd toinputrawlogits, finalconv weight+bias zero initially,153params. Input/output finite floating nonempty B1HW,same shape/device/dtype, no sigmoid/threshold/in-place input writes. Framework provides input guard, wrapper, controlled trainer, tests. Do not fill the user bodies. Opt-in practice tests outside standard tests/ collection fail untiluserimplementation; ordinaryCI tests cover provided guard/wrapper/runnervia transparent synthetic heads.

Future controlled comparison: small_vit vs small_vit_refined, freshseed20261116, bothfromscratch16x20steps,same33/10split and loss/threshold protocol, backbone identical initialparameters, matchedcrops;33785 vs33632params. Noactualablation training in this turn whilelearnerstubpending; noassertimprovement. OriginalCNN–ViT and publicdemo untouched. Studentpracticeinignoredfreshworkfolderdownload, no userrepo pull/reset/overwrite.
