# WSI ROI Coordinate Preparation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan inline. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prepare a real WSI ROI/resize path and one reserved user coordinate adapter without replacing the user's implementation work.

**Architecture:** A small `wsi_roi` module owns validated metadata, RGB reads and patch-footprint routing. `learner_wsi.roi_points_to_level0` remains a user-owned stub; accepted `local_to_level0` is not changed. Existing native exports and published experiments remain frozen during preparation.

**Tech Stack:** Python 3.12, NumPy, Pillow, optional OpenSlide 1.4.7/4.0.1, pytest.

**Spec:** `docs/superpowers/specs/2026-11-10-wsi-roi-coordinate-design.md`

## Global Constraints

- No user adapter answer code; only requirements, signature, provided validation and tests.
- Coordinates are continuous image-edge `(x,y)`; sizes are `(width,height)`; ndarray layout is `(height,width,channels)`.
- Actual OpenSlide scalar downsample is used; selected-level read origin remains level-0.
- Clip to complete pixel footprints before determining resize dimensions; reject zero-area reads.
- Keep native export/runtime results, models and `dist/` unchanged; no new performance/clinical claims.
- Preserve the user's modified loss file byte-for-byte during any later Codespaces update.

## Review Focus

- Right/bottom partial reads must use actual size, not requested size, for scale: test clipped read metadata and a learner example.
- Noninteger downsample must not be rounded: test fake metadata 4.25 and real slide level 1/2.
- Invalid/bool sizes, invalid levels or empty edge reads must fail before I/O: parametrized reader tests.
- Width/height and x/y must not swap under anisotropic resize: asymmetric hand example and real image shapes.
- Prepared path must not masquerade as completed user integration: stub/opt-in tests, unchanged native artifacts, explicit docs and provenance.

### Task 1: Reader and validated geometry

**Files:** Create `src/pathology_edge/wsi_roi.py`, `tests/test_wsi_roi.py`.

**Interfaces:** `RoiGeometry(origin_level0_xy, level, level_downsample, read_size_wh, model_size_wh, slide_size_level0_wh)`; `RoiRead(image, valid_mask, geometry, requested_size_wh)`; `read_roi(slide, origin_level0_xy, level, read_size_wh, model_size_wh=None)`.

- [ ] Write tests for native RGB equality, actual metadata downsample, right/bottom clipping (1000x800 slide, origin 900/700, downsample 4.25 → 23x23), asymmetric resize, transparency and invalid arguments before I/O.
- [ ] Run targeted pytest and observe missing-feature failures.
- [ ] Implement only the reader and validation described by the spec.
- [ ] Run targeted and default suite; require green default tests before proceeding.

### Task 2: Reserved user adapter and footprint consumer

**Files:** Create `src/pathology_edge/learner_wsi.py`, `tests/learner/test_wsi_coordinates.py`; extend `wsi_roi.py`.

**Interfaces:** `roi_points_to_level0(points_xy, geometry) -> ndarray`; `roi_patch_manifest(geometry, mode) -> list[dict]` with current native patch schema.

- [ ] Add opt-in contracts with hand example (10,20)→(1080,2320) for origin(1000,2000), d4, read400x200, model200x50; native corners, noninteger downsample, empty/no-mutation, unclipped points, inherited invalid input, clipped-read geometry and legacy native grid parity.
- [ ] Confirm opt-in failures at the absent/reserved implementation, not passing through an answer supplied by Codex.
- [ ] Provide the stub and Codex consumer routing; test its bad geometry/mode rejection independently, while semantic mapping tests remain pending.
- [ ] Default suite passes; opt-in mapping contracts remain expected failures and are recorded as incomplete.

### Task 3: Real evidence and user handoff

**Files:** `docs/STEP_40.md`, contribution/progress docs, `artifacts/learning/step39-review.json`, `step40-preparation.json` and verification logs.

- [ ] With the pinned CMU slide, read native R1 and compare saved RGB pixels; read level 1, level 2 and an edge crop with asymmetric model dimensions. Record dimensions/downsample/hashes; no inference or learner mapping claim.
- [ ] Verify the documented update procedure in a temporary Git fixture, including failed update and preservation of the dirty user file; no live user file mutation.
- [ ] Record U51's accepted explanation, U52 reserved next code task, and separate Codex preparation.
- [ ] Run default tests and existing static/audit checks, check protected artifact hashes, inspect docs/JSON/links; fresh whole-branch review under executing-plans before integration.

After the user submits code, a separate task will run the actual mapping contracts and integrate/verify the native and nonnative geometry path. It is not completed by this preparation plan.
