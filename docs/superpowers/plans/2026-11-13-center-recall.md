# Center Recall Implementation Plan

> Execute inline with superpowers:executing-plans; one fresh final reviewer.

**Goal:** Explain validation false negatives and evaluate a recall-constrained decoder.
**Architecture:** New diagnosis/selection helpers, frozen replay runner, saved-result review.
**Tech Stack:** Existing Python/PyTorch/NumPy/SciPy/Pillow; no new dependencies.
**Spec:** docs/superpowers/specs/2026-11-13-center-recall-design.md

## Global constraints

Frozen three seeds20261117/18/19 and four classifiers; validation227/4cases only
for decisions; match radius6px; original results and learner files unchanged.
Expanded threshold/distance grid and feasibility criteria are specified in the spec.
No training, no ratio-based selection, no silent fallback, no fresh-holdout claim.

## Review focus

- Dense neighboring annotations: one-to-one assignment differs from nearest-point coverage.
- Empty maps/references and exact6px boundary; every FN belongs to exactly one stage.
- Class confusion and unmatched candidates must reconcile to predicted class counts.
- Recall constraints are checked before maximizing F1, using validation only.
- Frozen inputs/source and selected configurations must be checked before evaluation.

### Task 1: Diagnosis and selection
Files: src/pathology_edge/ki67_center_diagnostics.py;
tests/test_ki67_center_diagnostics.py.
Interfaces: diagnose_candidates(points,scores,gt,classes,config)->stage counts and
reference reasons; selection accepts validation-tagged trial summaries and floors.
- [ ] RED tests for stage attribution, class counts, boundary/empty and infeasible selection.
- [ ] Implement, GREEN, commit.

### Task 2: Frozen validation replay and comparison
Files: scripts/run_ki67_recall.py; new artifacts/experiments/ki67-recall-20261113/.
Interfaces: prepare/validate/evaluate stages, fresh outputs, hash-locked inputs/source;
prediction schema compatible with summarize/audit_auto_ki67.
- [ ] Replay validation only; diagnose allseeds and select within fixed constraints.
- [ ] Freeze selection; evaluate feasible arms on reused407/133; keep adverse outcomes.
- [ ] Independently audit matching/metrics, locked sources and unchanged learner hashes.

### Task 3: Review and delivery
Files: report, STEP82 pending review, standalone HTML, evidence ZIP.
- [ ] Actual case visualization of missed/recovered points and positive/negative counts.
- [ ] Browser desktop/mobile, full suite and existing checks; final fresh code review.
- [ ] Commit/push draft PR; check download hashes. Give one user review step.

## Ledger

Base c72f6c4; existing linked worktree verified clean and fast-forwarded.
User asked to proceed; routine implementation choices made here, no new approval needed.
Preflight: diagnosis consumes raw sorted peaks; decoder selection outputs existing config
schema; new predictions use existing evaluator and frozen classifiers.
