# Candidate localization implementation plan

> **For agentic workers:** Use superpowers:executing-plans natively; one fresh final reviewer. Existing isolated feat/auto-ki67 worktree.

**Goal:** Correct integer score handling and test a prespecified three-seed localization correction, without converting experimental failure into claimed success.
**Architecture:** Frozen proposal union → candidate-native32px CNN with separate metadata and bounded XY offset → existing fixed classifiers. Primary corrected-center selection, matched checkpoint offset-off diagnostic.
**Tech Stack:** Existing NumPy/SciPy/PyTorch/Pillow; no dependency install.
**Spec:** `docs/superpowers/specs/2026-11-14-ki67-localization-design.md`.

## Global Constraints

Preserve source/weights/run archives/learner files/demo; new run folder. Train696/val227 fixed; no test/external until all3 lock. seeds20261117/18/19;12epochs;balanced64;Adam.001;2threads;32px reflected crops;12px radius; CE+SmoothL1beta.25. Existing14thresholds×3distances and all original selection constraints. Report all failures and one round only. User explicitly requested both fixes; routine native implementation choices remain within that authorization, no repeated execution permission request.

## Review Focus

1. uint dtype wrapping or float32 cutoff coercion must not alter priority/cutoff semantics.
2. XY offsets must rotate/flip with crops; padding and rounding must preserve coordinate frames.
3. Empty candidates, nearest-point ties, invalid shapes and nonfinite model/offset values fail safely.
4. GT/split/class cannot leak into image-only prediction; positive/negative proxy labels remain explicitly limited.
5. Historical source lock changes must not overwrite old results; no-eligible runs must skip holdout access and three-seed stability must be judged on the declared scope.

### Task1: score fix and invariant evidence
- [x] Add unsigned threshold/suppression and float32 cutoff regressions; observe7failed/26passed.
- [x] Normalize validated scores before negation/comparison; combined42passed.
- [x] Compare old float64 saved retention with frozen implementation, preserve historical evidence hashes; commit and clean CI full suite.

### Task2: candidate localization module
Files `src/pathology_edge/ki67_localization.py`, `tests/test_ki67_localization.py`.
Interfaces reflected_crops(rgb,points,size=32), proxy_targets(points,gt,shape)->labels/offsets/nearest, transform_sample(crop,offset,k,flip_y,flip_x), LocalizationGate, predict_localized(rgb,points,metadata,model,normalizer)->scores/corrected_xy/offsets, decode_localized(points,scores,threshold,distance).
- [x] RED tests literal crop boundary pixels, positive<=12/negative>12 border/empty rules, geometric rotations/flips, norm bound and rounding, model updates and NaN/overflow.
- [x] Implement minimal helpers, native RGB/metadata scorer and safe integer-coordinate output. GREEN focused suite, commit.

### Task3: protocol and actual three-seed run
Files `src/pathology_edge/ki67_localization_experiment.py`, `scripts/run_ki67_localization.py`, `tests/test_ki67_localization_experiment.py`.
- [x] RED stage ordering/no eligible and case/GT-balanced sampling, hash tampering checks.
- [x] Implement frozen prepare/fit/evaluate; reused fixed helpers, compressed scores/corrected centers, separate diagnostics. Ensure training classes and evaluation GT never enter prediction.
- [x] Commit source before running, train3×12 and lock all seeds. Conditional reused holdout evaluation; no selection relaxation or search after failed result.

### Task4: audit, review and delivery
Files `scripts/audit_ki67_localization.py`, `scripts/export_ki67_localization_review.py`, focused audit tests; docs/results.
- [x] RED tampered-correction/config/eligibility tests; independent saved-output aggregation/selection and checkpoint replays.
- [x] Run audit and actual browser1440/390; preserve screenshots. Export explicit scope/offset-on/off and all seed outcomes.
- [ ] Focused tests, stored Dice audit, clean exact-commit full CI, independent final review and fixes if important. Push existing draft PR, archive/download checks, user review pending.

Status: implementation, three-seed run,1512/681 audit,75 focused tests and1440/390 browser checks complete. Full eligibility0/3; original joint-only counts12/10/5. Final artifact review/CI/download confirmation tracked in experiment verification, not inferred from these checkboxes. User screen review remains pending.
