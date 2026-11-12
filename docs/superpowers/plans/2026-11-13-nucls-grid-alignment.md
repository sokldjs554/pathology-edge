# NuCLS one-pixel annotation-grid alignment

**Goal:** Resolve the36 quarantined RGB/mask grid mismatches without relabeling nuclei or selecting transforms using model scores; preserve the original15-FOV experiment.

**Evidence:** Official NuCLS inferred-anchor exporter explicitly resizes categorical masks with nearest-neighbor order0 for float-rounding differences. That is not proof of the historical raw SP.3 exporter. The51 original WSI/RGB pairs are already source/hash/coordinate checked; all36 mismatches are at most1px per axis. This follow-up adopts and documents the author's categorical grid convention rather than claiming recovery of unavailable subpixel annotation history.

**Design:** RGB is the fixed reference grid covering the filename's level0 bounds. Apply a half-pixel nearest-neighbor index map to the complete categorical mask and the existing target/valid/exclusion masks. Transform displayed CSV coordinates with the same edge-coordinate affine mapping. Identity for15 equal-shape pairs must be exact. Never interpolate integer class/instance IDs, retune thresholds, crop away boundary annotations, or edit raw files. Larger or unverified mismatches fail closed.

- [x] Add `src/pathology_edge/annotation_grid.py` with strict size/type validation, nearest index mapping and explicit edge-coordinate transforms; first test identity, anisotropy, categorical tuples, corners, invalid inputs and mismatches greater than1px.
- [x] Audit all51 pairs before inference: raw hashes, known crop identity,36 actual transformations,15 identity cases, class/instance IDs and known/ignored support mapping; compare nearest implementation against SciPy order0 grid-mode and record source URLs/versions. Preserve arbitrary class tuples.
- [x] Freeze model SHA/threshold0.35 and all per-pair transforms. Compute only the missing36 original-input predictions per model; reuse the original15 byte-identical inputs/labels/predictions. Publish separate15/36/51 and per-case summaries; no performance-based exclusions.
- [x] Recount saved probabilities, create before/after alignment figures for36 pairs and full result evidence. Audit unchanged earlier15 outputs and report the convention's limits, not full-WSI/clinical validity. Run scoped tests and independent review before publication.

**Constraints:** Existing user-written functions and baseline results remain intact. Source data/reference weights are from the hash-verified earlier evidence. Supplemental evidence references the immutable earlier ZIP rather than duplicating it. No user execution/review credited before confirmation. Execution is authorized; no design approval pause is needed.

Verification:27 new tests +59 existing scoped tests passed. All51 masks independently reconstructed;408 metric sets and160 means recounted. Three audit tamper cases rejected. Independent reviewer found no material blocker in code/results; report/publication verification follows. The historical exporter remains unreproduced.
