# Existing detector refit implementation plan

> **For agentic workers:** Native superpowers:executing-plans; one fresh final reviewer. Existing isolated feat/auto-ki67 worktree.

**Goal:** Test remaining detector fitting against all unchanged performance constraints with3 frozen seeds.
**Architecture:** Frozen CenterDetector → new24epoch Adam refit → native center peaks → unchanged fixed classification. Independent audit and saved-result A/B review.
**Tech Stack:** Existing PyTorch/NumPy/SciPy/Pillow; no dependency installs.
**Spec:** docs/superpowers/specs/2026-11-14-ki67-center-refit-design.md

## Global Constraints
Same seed17/18/19;train696/val227;24additional epochs,Adam.001,batch8,2threads;Gaussian sigma2;same augmentation. thresholds(.01,.02,.03,.05,.075,.1,.15,.2,.3,.5,.7,.9),distances4/6/8. Epoch0 diagnostic only. Same jointFPFN+LoG floors+.9case constraint. No test/external parsing until all3lock;all3denominator;noeligible skips. Never modify historical/user code/demo. Fresh optimizer explicitly declared. One fixed round.

## Review Focus
1. Initial weights must match parent checkpoints, no accidental model reinitialization or fake optimizer-resume claim.
2. Epoch0 cannot be adopted as trained improvement; missing seeds/settings cannot pass stability.
3. Score cutoff precision, zero-point images and case IDs must preserve native geometry and counts.
4. Current protocol and every frozen source/input/selection/output hash must reject drift before evaluation.
5. New-center classification and tumor-only BCData metrics require actual re-inference and authoritative GT, no cached original-center labels.

### Task1: fixed runner and training
Create src/pathology_edge/ki67_center_refit.py,scripts/run_ki67_center_refit.py,tests/test_ki67_center_refit.py.
Interfaces prepare(prior,output),checked(output,selected=False),refit_optimizer(model),configuration_trials(samples,epoch),choose_refit(trials,baseline),fit(root),evaluate(root,external=False). Uses existing center target/loss/predictor,union retain/summarize/choose,JSON/hash/data helpers.
- [x] Tests first: optimizer retains literal pretrained weights, zero-epoch exclusion evenifbest, train/test rows rejected by validation grid, empty candidates, strict thresholds and source/protocol/selection hashes, noeligible without holdout loads, denominator includes3.
- [x] ObserveRED; implement; focusedGREEN. Save all peak arrays+offsets per epoch, final optimizer/RNG state, explicit skips and provenance. Commit before actual run.
- [x] Prepare/fit all3,lock,conditional internal/external stages. No result-based protocol changes.

### Task2: independent audit and review
Create scripts/audit_ki67_center_refit.py,scripts/export_ki67_center_refit_review.py,tests/test_ki67_center_refit_audit.py.
Interfaces audit(root)->report,export(root,review)->standaloneHTML; input saved refs/peaks, locked configs/checkpoints.
- [x] RED for mismatched epoch/offsets/native bounds and missing seed; implement independent selection/count replay and initial+chosen raw checkpoint verification. Eligible holdout gets GT/model/classifier replay.
- [x] Run actual audit2700trials and checkpoints; build same-coordinate A/B examples min/maxFP+FN perseed. Browser1440/390 counts, overlays,navigation,overflow; screenshots.

### Task3: delivery
- [x] Local relevant tests and stored Dice audit; clean full CI due local disk preconditions. Fresh final review of whole new range and any important fixes.
- [x] Preserve original/results and write truthful report, manifest and standalone ZIP. User new review pending; U104 unchanged. Selection0/3, performance stability unmet.
- [ ] Publish evidence, verify public download SHA, and update existing draft PR. Publication verification is the final delivery step.

Actual run: frozen source d28c812, code audit53a6c08,3×24epochs,2700 audited settings,1362 checkpoint-image replays,eligible0/3,holdout inference0. Highest-F1 B epochs19/23/24. Independent final code and artifact reviews: no Critical/Important findings. Browser6examples1440/390 passed; file:// blocked by managed browser, local HTTP with embedded assets passed. Source CI668 tests+Dice42/6+static checks.
