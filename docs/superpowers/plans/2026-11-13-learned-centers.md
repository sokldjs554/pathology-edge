# Learned IHC Center Detector Implementation Plan

> Use superpowers:executing-plans inline; one fresh final reviewer.

**Goal:** Replace heuristic candidate positions with trained center predictions and measure the tradeoffs.
**Architecture:** Independent target/loss/decoder/model module and frozen staged runner; reuse fixed classifiers and existing point evaluator.
**Tech Stack:** Existing Python/PyTorchCPU/NumPy/SciPy/Pillow; no added packages.
**Spec:** docs/superpowers/specs/2026-11-13-learned-centers-design.md

## Global constraints

Existing15/4/10case split,3specifiedseeds,16epochs,batch8,lr.001,threads2; nativepixels.
Source/input/config/model freeze precedes reusedtest/external scoring. No learner changes.
External scope tumor-only; empty tumor denominator null with coverage; no clinical claims.

## Review focus

- XY vs image row/column, border clipping, overlappingGaussian peaks, empty/duplicate labels.
- Stable focal gradients for extreme logits and empty references; fail on malformed tensors.
- Equal-valued plateaus and NMS equality/ties; finite model/map validation before inference.
- Shape/geometry for224training vs640external; classes must be reinferred at new points.
- Validation-only selection, complete frozen manifests, allseeds, existing external exposure.

### Task1: Meaningful TDD for learned centers
Files: src/pathology_edge/ki67_centers.py; tests/test_ki67_centers.py.
Interfaces: center_target(points_xy,shape_hw,sigma=2)->float32HW;
center_focal_loss(logits,target)->scalar; CenterDetector()->B1HW logits;
peak_candidates(map)->XY/scores; decode_centers(map,threshold,min_distance)->points/scores;
predict_centers(rgb,model,config)->points_xy/scores/probability_map.
- [x] Write independent literal tests for target peak/neighbors/maxoverlap/border and invalids;
  focal value/gradient/extremes/empty; plateau representation/NMS; odd-sized input/noGT API.
- [x] Observe RED, implement, GREEN with existing point/classifier tests; commit.

### Task2: Locked training, internal/external evaluations
Files: src/pathology_edge/ki67_center_experiment.py; scripts/run_ki67_centers.py;
tests/test_ki67_center_experiment.py. Interfaces prepare/fit/evaluate/external CLI;
select_configuration(validation candidates/GT)->bestconfig/trials; per-seed results use
existing audit_auto_ki67 format so independent recount can operate unchanged.
- [x] RED tests for train/test rejection, case-macro selection, ties, integrity and fresh outputs.
- [x] Implement fresh staging, data/model/source verification, frozen classifier loading,
  native-size inference and complete matched metrics; GREEN. Freeze/run3seeds, lock before
  407/133 re-evaluation. No score-guided changes after either evaluation.
- [x] Independent recount all new predictions, baseline identity, one image-only replay.

### Task3: Reviewable evidence and delivery
Files: docs/KI67_LEARNED_CENTERS.md, scripts/export_ki67_centers_review.py,
artifacts/experiments/ki67-learned-centers-20261113/, new handoffZIP.
- [x] Generate actual held-out-record before/after examples incl old107-candidate case,
  fixedfirstseed best/worstF1 changes; all detector/classifier options. No reference centers
  passed to inference. Browsercheck desktop/mobile, display/model toggles, savednumbers.
- [x] Scopedlocal+fullCI, fresh final review, hash/ZIP/download check, push existingdraftPR.
  User U94 first-example display/toggle response is recorded separately; no blanket completion/generalization claim.

Preflight: Task1'sXYpoints -> Task2 classifier nativecropXY; Task2 standard prediction schema
-> existing independent audit; Task3 only saved/equally replayed results, not invented overlays.

Additional Task2 interface: ki67_center_inference.py::infer_rgb/load_bundle and scripts/infer_ki67_centers.py provide image-only inference from packaged models without prior private scoring folders. Tests cover new-center class assignment, empty denominator, invalid classifier, traversal/hash and unknown seed. Frozen training sources remain unchanged.

Validation-only amendment recorded in spec: initial ReLU trial preserved (seed19zeroF1);
diagnostic motivated one activation-only LeakyReLU0.1 trial, same3seeds/settings. No test/external
scoring before either decision. Current source557CItests passed at583be54. Final reviewer
checkpoint found no actionable issues and33newtests passed; wholeincrement readiness awaits
actual evaluation/artifact/browser evidence. No old test/external score-driven retuning.

Final: complete implementation and evidence reviewed at0f518dc; no findings. Source-head
CI557passed;6480recounts,576selectiontrials,12portableCLIcombinations,9heatmapreplays,
36browsercombinations all pass. Published113-fileZIP at8ba7d50:5,474,802bytes,
SHAa954552abde0d90ec761247b74971b0d5499119b723ac4948ce93a64f0e3b145.
HTTP200download,ZIPCRC andallmemberhashes verified. DraftPR2updated; no merge/demo
deployment. UserSTEP80/U94first-example display/toggle normal response recorded in step80-review.json; no new user inference/training/tests claimed.
