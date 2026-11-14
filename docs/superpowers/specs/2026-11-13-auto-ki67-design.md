# Image-only Ki67 patch analysis and prospective comparison

The user authorized: automatic patch Ki67 analysis -> separate external evaluation design -> improvement comparison. The existing dataset, user-authored seven scopes, scientific outputs, demo and issued handoffs remain unchanged. These are research patches, not a clinical assay or whole-slide validation.

First deliver an image-only reference pipeline: multiscale normalized LoG on mean RGB optical density finds candidate centers; the frozen existing40-feature classifier labels them. Class0/(class0+class1) is the predicted tumor-positive fraction; zero denominator is null. Ground-truth coordinates are NEVER prediction inputs.

An added morphology classifier is the improvement to compare: a small independently implemented48px CNN, trained only on Patherea's existing15 training cases, selected on existing4 validation cases. Three fixed seeds20261113/14/15. Same detector and predicted positions for every classifier; report each model separately and never select a winning seed using test results. These are assistant implementation choices, not user-authored code or a paper reproduction.

Dataset: hash-verified Patherea Breast-P1 v1.1,1,330 images/29cases/19,972 annotated centers, CC BY-NC4. Fixed existing696/227/407 image and15/4/10case split. The407-image test is a reused test set, not newly unseen. Locate a separate external image set and establish its labels/overlap/annotation completeness before including it. Known MoNuSeg/NuCLS H&E outcomes and BCData402 outcomes must not become unseen-test claims. A new IHC improvement does not reverse the earlier H&E result.

Matching uses class-blind maximum-cardinality, minimum-distance one-to-one assignment, <=6native pixels. Wrong matched class incurs a class FP and FN; unmatched points count too. Report localizationP/R/F1, four-class end-to-end F1, matched-only accuracy separately, cell count errors, image/case positive-ratio error, and denominator-zero coverage. Point labels are not nucleus contour masks.

Freeze9 detector settings before validation: response{.03,.06,.10}, separation{4,6,8}px; LoG sigma{1.5,2.5,3.5}. Select by validation case-macro localizationF1, ties higher response then larger separation. Freeze selected detector, classifier hashes and source before any current held-out scoring. Training/selection/test storage remain separate; fresh outputs only. Save every image's predictions and per-case outcomes including failures. Repeatability is not independent clinical validation.

CNN choices: 3->16->32->64 channels, two3x3-conv/ReLU blocks per stage and maxpool2; global average, linear4;48x48 RGB/255; Adam1e-3; batch64;12epochs; inverse-frequency class weights computed on training only; training flips/rot90 and per-channel multiplicative jitter0.9..1.1. Validation macroF1 at GT centers chooses epoch, earliest on tie. Seeds all published; no calibration claim. Training input centers are legitimate annotations; prediction input has no annotations.

Allowed evaluation figures show native original patches, provided centers, automatic centers, matches and misses. Any chosen success/failure criterion is explicit. Reserve user actions for a single review step after evidence is ready; don't manufacture a new user execution.
