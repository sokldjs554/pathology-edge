# NuCLS SP.3 linked ROI evaluation plan

**Goal:** Evaluate the frozen baseline/refined models on all 51 public SP.3 U-control FOVs, after binding their annotations to five exact original WSI files.

**Architecture:** Use the existing strict HTTP range reader and pipeline. Keep acquisition and experiment outputs in a separate work directory, then publish audited derived results with reproducible scripts. This is a research evaluation, not a new product capability.

**Spec:** User approved the next public WSI/manual-ROI evaluation described in `docs/PUBLIC_DATA_UPLOAD_REVIEW.md`.

**Fixed controls:** Existing checkpoints SHA256 `0bb2af67ca4d4e403e5789359feb6b284f9207e6c7eb9bf4e521b7d0972f5898` / `b9d3892a257a06ed0b67bd4e8717a331d457272531b3501fadf1fbacd70f004f`; threshold 0.35; 128px no-overlap pipeline; no training, threshold selection, stain normalization, or annotation-driven registration. All 51 publicly listed SP.3 FOVs are included before predictions; technical failures remain reported. Five case groups, not 51 independent patients. No claim of a whole-WSI or clinical evaluation.

## Execution

- [x] Acquire 51 matching CSV/RGB/mask triplets and record source IDs/hashes. Inventory actual annotation types; observed 1,221 polylines and 2 rectangles among 1,223 rows, not 1,223 polygons.
- [x] Bind exact DX1 filenames to GDC UUID/MD5; decode level0 crops; compare to supplied RGB at its native dimensions; hash complete streams without storing multi-GB copies. Record every crop and scale; do not optimize alignment against prediction scores.
- [x] Implement and test label interpretation against synthetic fixtures: unknown codes rejected, outside/ambiguous pixels ignored, rectangles excluded inclusively, CSV/mask contour disagreements recorded/excluded. The published mask's explicit background code 253 and named nuclei codes define annotated support; do not infer that unannotated 0 pixels are background. Do not invent the missing intended-FOV metadata.
- [x] Freeze protocol/source/input hashes, run both models on original-derived crops (primary) and supplied RGB (rendering sensitivity). Save probabilities, masks, case/FOV metrics, error counts and evidence overlays. Count the rendering comparison as the same cases, not extra data.
- [x] Independently recount metrics from saved probabilities and audit hashes. Inspect same-location source/GT/error panels, preserve failures and previous results, publish a scoped report.

## Review focus

1. SP.3 rows labeled `rectangle` are not nuclei contours even though the overview says all boundaries are manual.
2. Mask class 0/99 does not represent confirmed background; separate explicit background 253.
3. Nuclei outside the intended annotation area may still be explicitly outlined; report annotated-support pixels, not exhaustive FOV/slide coverage.
4. Same TCGA patient may occur in previous external datasets; check IDs and distinguish new annotation data from a new independent cohort.
5. Exact WSI file identity, crop scaling, rendered RGB differences and source checksum are separate checks.

Execution is already authorized by the user; no additional design approval is needed. Research scripts and tests will be archived with the results. Existing learner code, app and experiment results remain unchanged.

## Execution rulings and evidence

Before any prediction, 36/51 RGB-mask pairs were found to differ by one pixel in width/height. Quarantine those pairs without resampling labels; evaluate the remaining15 FOVs/four cases. This costs coverage and may introduce selection bias; report the entire exclusion list. All51 triplets/five original WSI were acquired, but only15 FOVs were inferred. The original exhaustive51-FOV goal is therefore restricted, not falsely marked as51 evaluations.

Ruling: intended-FOV metadata was not found in the inspected folders. Use explicit mask support with0/99/rectangles/disagreements ignored; do not claim exhaustive FOV coverage. Nuclear extensions outside the intended FOV can contribute.

Ruling: A0SP overlaps a previously evaluated external patient. Report four evaluated case groups, only three newly evaluated patient IDs; no independent cohort claim.

Verification: support tests14 passed, scoped existing regression tests59 passed, saved-probability metrics240/240 and aggregate means96/96 reproduced. Five full original MD5 references match;153 raw assets and51 original crops hash-audited. Source, checkpoints and existing learner code unchanged. No new user-performed actions recorded.
