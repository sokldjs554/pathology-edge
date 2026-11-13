# Ki-67 Union Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Compare frozen detector/LoG union plus a trained RGB rejection gate against the existing detector without trading hidden FP/FN regressions for a favorable ratio.

**Architecture:** Keep all learned detectors and four-class classifiers frozen. A separate two-class CNN scores native32px candidate crops; validation selects a gate threshold and spacing only under the approved joint-count and recall constraints. Publish all three seed outcomes, and only evaluate feasible locked models on reused test/external images.

**Tech Stack:** Existing Python3.12/PyTorch/NumPy/SciPy/Pillow environment; no new dependencies. Native execution in the existing isolated `feat/auto-ki67` worktree, followed by independent branch review.

**Spec:** `docs/superpowers/specs/2026-11-13-ki67-union-gate-design.md`; user explicitly approved implementation and experiments after choosing the direction.

## Global Constraints

- train696/15case, validation227/4case; reuse test407/10case and BCData133 only after all selections lock.
- Frozen learned seeds20261117/18/19; union proposals0.01/4px plus frozen LoG0.1/8px, sigmas1.5/2.5/3.5.
- New gate:32px RGB, channels8/16/32, two padded3×3 convolutions per block, LeakyReLU0.1,2×2 pooling, flatten512→2. Adam0.001,12epoch,batch64,2CPUthreads.
- Train positive/negative1:1 with case-balanced sampling; negative proxies farther than12px and interior24px, maximum256/image; point labels are not exhaustive background truth.
- Thresholds0,.05,.1,.2,.3,.4,.5,.6,.7,.8,.9,.95,.99,1; spacing4/6/8.
- Require pooled FP/FN each≤matched A, one strictly less; prior LoG recall floors retained; every validation case recall≥90%A.
- Preserve all original learner/source/result/archive Git contents. No new user code/training credit or public demo change.
- User approved the design with “이 설계대로 구현·실험 진행”; routine implementation choices stay inside that authorization.

## Review Focus

1. A zero threshold, equal scores, duplicate coordinates and different detector score units must not alter deterministic provenance/retention semantics.
2. Empty candidates or finite weights producing nonfinite logits must fail safely without fabricated positive classifications.
3. Proxy-negative margins, border crops and missing negative cases must not silently create false labels or fail balanced sampling.
4. A no-feasible-seed run must not run test/external data or relax constraints; tampering after selection must stop inference.
5. Sparse checkout and constrained disk must preserve user work/history, use compressed predictions and report local-vs-CI validation accurately.

---

### Task1: Candidate union, binary scoring and fixed selection

**Files:** create `src/pathology_edge/ki67_union.py`, `tests/test_ki67_union.py`.

**Interfaces:** `merge_proposals(learned_xy,log_xy,shape_hw)->dict(points_xy,sources)`; `CandidateRejector(nn.Module)`; `retention_scores(rgb,points,model)->np.ndarray`; `retain_candidates(points,scores,threshold,min_distance)->dict`; `negative_proxy_indices(points,gt,shape_hw)->np.ndarray`; `validation_summary(samples,config)->dict`; `choose_trial(trials,baseline,floors)->dict`.

- [x] Write contracts: exact duplicates combine source bits; input source scores never compared; identical-score order y/x; threshold0 supported;6px matches are one-to-one.
- [x] Write empty/nonfinite/crop-border/proxy-margin tests; require no expert-background claim and no truth in scoring signature.
- [x] Write selection tests: joint counts, strict improvement, exact LoG floors, per-case90%, all-infeasible returnsNone, nonvalidation rejected, deterministic tie order.
- [x] Run focused tests and confirm missing-module failures; implement helpers and gate.
- [x] Verify gradient/update behavior and threshold0 NMS-prefix reuse against independently decoded threshold cases. Run focused suite, commit.

### Task2: Frozen experiment runner

**Files:** create `src/pathology_edge/ki67_union_experiment.py`, `scripts/run_ki67_union.py`, `tests/test_ki67_union_experiment.py`.

**Interfaces:** `prepare(prior,output)->protocol`, `fit(output)->selection`, `evaluate(output,external=False)->results`; stages reject reused output paths and changed hashes. Consume Task1 helpers and existing `load_sample`, classifiers, matching and dataset verification.

- [x] Test fail-closed stage ordering and hash locks, no-feasible skip, immutable original source/files, exclusion of test/external from training/selection.
- [x] Implement preparation with source/input SHA, control metrics, user-file hashes, existing split, bounded memory and free-space check; only compressed candidate/prediction persistence.
- [x] Implement train-only pool, case-balanced1:1 crop sampler, matched-candidate/GT jitter alternatives, deterministic augmentation and seed pairing.
- [x] Implement12epochs×3seeds selection. Record all42trials/epoch and failed seeds. Reuse descending-score NMS prefixes across thresholds only after Task1 equivalence test.
- [x] Lock all seeds before test/external. A/B/C/C0 and four fixed classifiers re-infer at their actual retained coordinates; external tumor-only evaluation. If none feasible, skip both later stages explicitly.
- [x] Run tiny synthetic pipeline tests without full-dataset training, commit.

### Task3: Actual run, independent audit and review artifact

**Files:** create `scripts/audit_ki67_union.py`, `scripts/export_ki67_union_review.py`, `tests/test_ki67_union_audit.py`, `docs/KI67_UNION_GATE.md`; results under a fresh `work` run and compressed/public subset under `artifacts/experiments`.

**Interfaces:** audit consumes protocol/locks/compressed saved candidates/predictions and recomputes matches/counts/selection independently; exporter consumes immutable stored results and displays scope/limits.

- [x] Test auditor detects tampered retained points, changed eligibility, mismatched masks/counts and missing failed-seed reports.
- [x] Freeze source and run train/validation only. After all seeds lock, conditionally run existing internal/external evaluations; no model changes after viewing them.
- [x] Independently recompute trial eligibility, selection ordering, TP/FP/FN/class counts/ratios and model/file preservation.
- [x] Export actual examples. If no seed is eligible, show validation failure with a diagnostic checkpoint clearly labeled, and no test/external result claims.
- [x] Browser verify selected examples, same-coordinate overlays, current metrics and1440/390px layout. Retain screenshots and immutable archive hashes.
- [x] Run focused regressions and stored Dice42/6 checks. Push code for clean CI full suite when local2GiB prerequisite cannot be met; record source of each check.
- [x] Independent whole-branch reviewer examines source, protocol, data exposure and results. Fix material defects, rerun relevant checks, update draft PR and publish evidence with explicit user-vs-provided execution scope.

## Self-review

Spec sections map to Task1 contracts/selection, Task2 data/training/locking and Task3 auditing/reporting. All five failure classes have explicit tests. No existing production defaults or learner files are changed. The user's explicit design approval includes this implementation/execution; an additional execution-method approval is unnecessary for native work inside that scope.
