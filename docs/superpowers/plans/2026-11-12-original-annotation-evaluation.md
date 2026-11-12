# Original image / annotation evaluation plan

> **For agentic workers:** Execute the already authorized data verification and evaluation; independent WSI and IHC tasks have separate output directories.

**Goal:** Bind actual source bytes to annotations and evaluate linked examples, preserving prior results.
**Architecture:** Frozen research protocols and hash manifests, direct original WSI tile decoding, official BCData test-file pairing, saved predictions and independent recounts.
**Tech Stack:** Existing Python/PyTorch/NumPy pipelines; isolated TIFF/JPEG codecs and HTTP byte ranges for WSI; existing HDF5 reader for IHC.
**Spec:** User instruction: compare actual originals and annotations, secure linked cases, then evaluate. Prior scope: docs/CLINICAL_WSI_VALIDATION_STATUS.md.

## Global constraints
- No retraining, threshold tuning, label-dependent registration, source-result overwrites, or new claims of clinical/full-slide accuracy.
- H&E fixed user seed20261116 SmallViT pair, threshold0.35, patch128/no_overlap.
- IHC existing frozen40-feature classifier at supplied centers, native pixels.
- Unlabelled/ambiguous/box-only nuclear regions remain excluded; case/ROI denominators explicit.
- BCData raw images, cell records and patient data are not republished; keep source access and hashes.

## Review focus
- Same case but different DX1/TS1 slide must not be substituted; record missing exact GDC matches.
- HTTP200/truncation/wrong Content-Range must fail range reads; test with fake responses.
- Crop must decode only intersecting native TIFF tiles and agree with a complete synthetic tiled TIFF crop.
- Every fetched WSI block must agree with streamed whole-file bytes before claiming the crop belongs to that hash.
- BCData old10/new392 must be separate; undefined Ki67 denominators must not silently become zero.

## WSI deliverable
- [ ] Lock first ROI of remaining3cases in the same initial manual-folder listings before predictions.
- [ ] Download raw RGB/mask/CSV; derive valid masks using existing audited rules.
- [ ] Read original SVS by byte range, compare entire stream size/MD5 where published and SHA256, preserve metadata and block checks.
- [ ] Decode native ROI, map fixed edge coordinates, compare providedRGB; no score-dependent adjustment.
- [ ] Evaluate direct-original and provided-RGB inputs separately; second is a paired rendering sensitivity check, not independent data.
- [ ] Save raw probabilities, annotated coverage, counts, figures, independently audited results.

## IHC deliverable (delegated)
- [ ] Lock all402officialtest PNG/HDF5pairs before new predictions, retaining original10known examples.
- [ ] Verify1206entries by CRC/size/SHA, annotation bounds/classes/conflicts; no replacement of failures.
- [ ] Evaluate frozen model and independently recount aggregated and perROI results; publish lawful subset only.

## Integration
- [ ] Independently review acquisition, arithmetic and scientific claims.
- [ ] Run relevant tests and original-result preservation checks; publish docs and evidence with precise scope.
