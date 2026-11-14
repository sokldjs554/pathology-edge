# Final Transfer Comparison Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Finish one genuinely new pretrained comparison and all fixed diagnostic evaluations, then close the performance iteration.

**Architecture:** Frozen official SqueezeNet1.1 features plus trainable dense decoder; paired random-feature control. New modules preserve prior source-hashed runs. Fixed classifiers and independently checked references connect actual detections to end-to-end scores.

**Tech Stack:** Existing Python/PyTorch/NumPy/SciPy/Pillow; no torchvision binary install.

**Spec:** ../specs/2026-11-15-ki67-final-transfer-design.md

## Global Constraints

- User authorized final attempt; no repeated permission or interpretation quiz.
- Seeds20261117/18/19,24epochs,train696/validation227,original recall gates.
- All3 models locked before heldout; no external retuning; unadopted diagnostic execution allowed prospectively.
- Preserve seven learner files and existing deployment. Never label automated work user-completed.

## Review Focus

- Incorrect/missing pretrained tensor must fail strict loading; frozen encoder must not update.
- Non-square/odd native sizes must return same-shaped logits without coordinate resize.
- Unequal case counts must produce equal total sampling probability per case, independent of heldout rows.
- Missing seed/changed checkpoint or protocol must block evaluation; ineligibility alone must not silently skip it.
- Empty predicted tumor denominator must retain coverage failure, not disappear from favorable MAE.

### Task1: Model and paired training

Files: src/pathology_edge/ki67_transfer.py,ki67_transfer_experiment.py; tests/test_ki67_transfer.py; scripts/run_ki67_transfer.py.

- [ ] Write failing model/gradient/native-shape/sampler/selection tests and confirm failure.
- [ ] Implement TransferCenterDetector(state), balanced_probabilities(records), diagnostic_choice(trials,baseline), prepare/fit_worker/seal.
- [ ] Verify official source, license, download SHA and loaded tensor equality; freeze data audit/source protocol.
- [ ] Run paired six jobs once and seal all selected/diagnostic results.

### Task2: Fixed automatic and external evaluation

Files: src/pathology_edge/ki67_transfer_evaluation.py; scripts/run_ki67_transfer_evaluation.py; tests/test_ki67_transfer_evaluation.py.

- [ ] Test seed coverage, immutable locks, diagnostic inclusion and undefined ratio coverage.
- [ ] Implement fixed paired CNN classification at predicted centers; evaluate validation227, reusedtest407/BCData133, prospectiveDeepLIIF597.
- [ ] Validate every external reference/CRC/hash/membership; record all seed outcomes, no selective exclusions.

### Task3: Audit and close

Files: scripts/audit_ki67_transfer.py; docs/KI67_FINAL_TRANSFER.md; artifacts/experiments/ki67-final-transfer-20261115/.

- [ ] Independently recompute selected NMS/metrics and selected checkpoint outputs; audit encoder/head initialization and unchanged learner files.
- [ ] Run appropriate tests and existing CI; obtain fresh full-change review and fix actual errors.
- [ ] Publish report/evidence/receipt in existing draft PR; verify downloadable evidence hash. Record final success/miss without another tuning round.
