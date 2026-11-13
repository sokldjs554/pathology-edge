# Learned IHC centers: controlled detector replacement

User authorized the next improvement after U93: improve localization itself. This is an
increment to the existing research pipeline, not a deployment, clinical assay or WSI run.
Implementation choices below are the assistant's; they are not user-authored decisions.

## Approaches and chosen scope

1. Expand LoG scales: inexpensive but still relies on manually selected appearance rules.
2. Small fully convolutional center heatmap: chosen, uses available point labels and CPU,
   allows changing localization while freezing classification. No pretrained weights.
3. Full point-transformer/foundation detector: greater compute/dependency burden; not this step.

Use existing TinyUNet(width=4), from scratch, one native-resolution logit map. Initialize
output bias=-2.19. Gaussian targets: max across centers, sigma2px, radius6px, peak1,
outside radius0; clipped at image boundary. Never sum overlapping peaks or interpret
the map sum as a cell count. Centers must be unique integer XY inside the image.
Modified focal objective: positive peaks use (1-p)^2 softplus(-logit); other pixels use
p^2 (1-target)^4 softplus(logit). Sum per image / max(number of peaks,1), average batch.
This is an independently implemented small center-map adaptation, not a CenterNet or
Patherea-P2P reproduction. Motivation: Zhou/Wang/Krähenbühl, Objects as Points (2019),
https://arxiv.org/abs/1904.07850 ; no upstream source copied.

## Fixed experiment

Existing Patherea split:696train/15cases,227validation/4cases,407reusedtest/10cases.
All released train/validation patches have >=1 annotated center. Four classes collapse
to one localization target. Gaussian tails and unannotated pixels are derived supervision,
not manual nuclear masks/non-cell truth. Original annotation polygon support absent;
coverage/omission uncertainty remains (https://arxiv.org/html/2412.16425v2 section4).

Train3 seeds20261117/20261118/20261119;16epochs;Adam lr.001;batch8;CPU2torch threads.
Augment train only: pairedrot90/flips; per-image RGB factors U(.9,1.1). Native224pixels.
No changes to the seven user-authored scopes, datasets, previous models/artifacts or demo.
Validation each epoch: threshold [.1,.2,.3,.5] x minimum separation[4,6,8] native pixels.
Select maximum case-macro localizationF1; ties higher case-macro recall, earlier epoch,
higher threshold, larger separation. No test/external labels used for selection.
Peak candidates are3x3 local maxima; connected equal-valued plateaus yield one point
nearest their centroid (ties y,x); then deterministic score-descending Euclidean NMS.

After locking source/input/weights/configs, score all3 detectors with each of the4 fixed
classifiers (LR and CNN20261113/14/15). Re-infer classes at NEW points; do not reuse
old classes at new centers. Recount all points using existing max-cardinality/min-distance
matching <=6nativepx; report FP/FN/recall and4classF1, case/image ratioMAE and coverage.
Keep baseline and previous filter results unchanged. Report all seeds, not a best test seed.

BCData: reuse the prior133 official-validation images and canonical tumor-only references.
Verify raw image SHA against prior acquisition manifest, stream without retaining raw data.
Native640input, no new scale tuning. Filter predictions to tumor classes0/1 for scoring;
report2classF1 and image-level ratioMAE/coverage, not full4class performance or cases.
Both407and133 are previously exposed evaluations; no fresh external/generalization claim.
No patient/slide independence, verifiedMPP, whole-WSI GT or clinical validation is added.

## Outputs / validation

New modules+runner, tests, frozen checkpoints/sources/protocol, full per-image metrics,
private prediction coordinates, independent numerical audits, offline before/after review,
screenshots and a compact ZIP. Raw BCData/individual coordinates not redistributed.
One user review step after delivery; record pending until response. User code7scopes unchanged.
No guaranteed gain or automatic promotion. Full tests run in fresh CI; local scoped tests
avoid old repository-copy tests on a nearly full volume. Source/data evidence is preserved.
