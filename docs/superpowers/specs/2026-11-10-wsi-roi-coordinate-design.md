# WSI ROI coordinate exercise design

The user approved the job-match priority order and delegated selection of one useful coding exercise at a time. This implements the preparation for priority 2, preserving their completed loss comparison and reserved learner code. Python, NumPy, Pillow and existing OpenSlide are retained. Interface and clipping choices below are Codex decisions within that scope, not additional user decisions.

## Approaches

1. Keep only native origin addition: smallest, but does not connect the user's coordinate function to pyramid/resize metadata.
2. **Prepare an actual ROI reader and patch-footprint consumer, with the metadata-to-transform function reserved for the user.** Chosen by Codex: narrow enough for one exercise and checks real OpenSlide metadata without changing published measurements.
3. Generalize the whole inference/viewer pipeline now: entails resampled model validity, centroids, thresholds and new measured results. Deferred; unnecessary for this exercise.

## Contract

- `wsi_roi.RoiGeometry`: frozen validated metadata: integer nonnegative `origin_level0_xy`, nonnegative integer `level`, finite positive `level_downsample`, positive integer `(width,height)` pairs `read_size_wh`, `model_size_wh`, `slide_size_level0_wh`. The read footprint must fit the slide. Preserve noninteger downsample; never infer it from `2**level` or rounded dimension ratios.
- `read_roi(slide, origin_level0_xy, level, read_size_wh, model_size_wh=None) -> RoiRead`: caller owns the OpenSlide handle. Origin is always in level-0 units; requested read size is in selected-level pixels. Clip right/bottom to the number of complete selected-level pixel footprints that fit: floor(remaining level-0 extent/downsample). Reject an empty result. Record actual and requested sizes separately; default model size is the actual clipped size. White composite RGBA padding/transparent pixels, bilinear RGB resize, nearest-neighbor resized source-opacity mask. A valid-mask value describes sampled original opacity, not a guarantee about an interpolation kernel. Never close the caller handle.
- User-owned `learner_wsi.roi_points_to_level0(points_xy, geometry)`: only derive the two resize scales from actual read/model dimensions and call their accepted `local_to_level0`. Codex supplies the declaration/type guard. Keep the body `NotImplementedError` until submitted. Points are continuous image-edge coordinates (useful for boxes), not automatically corrected pixel-center indices; no clipping or rounding. Return float64 `(N,2)`, permit empty points, preserve inputs and existing numeric validation.
- `roi_patch_manifest(geometry, mode)`: existing 128px grid and 0/64 overlap; call reserved learner adapter for patch corners. Model-frame valid patch sizes exclude trailing padding. Native output must match current `wsi_export.patch_manifest` numerically. It is unavailable until the learner body is completed; no fallback answer implementation.

## Scope and acceptance

Codex completes reader, metadata validation, consumer routing and tests; learner contracts stay opt-in and fail at the reserved stub. The public native export and `dist/` remain unchanged during preparation. A later accepted submission enables the actual patch mapping and native integration; do not claim that integration or nonnative inference is complete now. No centroid half-pixel convention is silently added to the user's existing transform.

Verify native pixels against saved real ROIs, real level>0 metadata and non-square resizing, conservative edge clipping, invalid inputs before I/O, native grid parity after the learner implementation, and unchanged published artifacts. Do not infer accuracy from WSI geometry (no nuclear GT).

The user's Codespace is at `790a336` with only `learner_losses.py` modified. Any update instructions must preserve this exact file, make a verified backup before temporary restoration, and restore it even if updating fails. User execution/tests remain pending until outputs are received.
