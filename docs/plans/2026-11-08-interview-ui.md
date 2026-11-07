# Interview review UI — authorized implementation plan

Preserve the existing workbench, source results and pan controls. User requested direct implementation and publication.

1. Verify main/production bytes and capture the current v4 UI (completed; baseline run 42400413971).
2. Export deterministic, post-hoc boundary examples from the saved PNG predictions and binary GT. Select 64px squares centered on baseline seams; exclude 32px exterior margin; score only the fixed ±8px boundary band. Keep both corrected and regressed pixels, signed local Dice, and source hashes. Never alter original experiments.
3. Add one compact purpose/workflow strip, one-click improved/worsened examples, a same-coordinate ROI and exact pixel highlights. Put details in the inspector. Preserve whole-image scope metrics.
4. Expose raw-precision aggregate deltas, per-image improvements/regressions and warm CPU median cost. Add accessible terminology and honest H&E/WSI/Ki-67 scope.
5. Verify selection/export with independent pixel reconstruction, existing Python/C++ and geometry tests, and real Chromium/WebKit via repository CI. Inspect screenshots, publish exact source, verify live source hashes and repeat production browser tests.
6. Save before/after screenshots, source provenance and contribution records. User checks remain pending.
