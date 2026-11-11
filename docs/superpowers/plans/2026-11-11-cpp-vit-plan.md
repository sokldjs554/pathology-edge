# C++ / ViT implementation plan

Goal: prepare both authorized improvements while assigning one user task at a time.
Spec: [design](../specs/2026-11-11-cpp-vit-design.md).

Already isolated at `/workspace/pathology-edge-loss`, base9ce624b; existing201tests pass. No new dependencies.

- [x] C++ independent runner, safety/parity tests, one real benchmark, STEP_51.
- [x] SmallViTSegmenter, token-to-pixel geometry/gradient/state/input tests.
- [x] Separate `model_comparison.py` trainer and `run_model_comparison.py` runner; source snapshots, immutable outputs, manifest/crop-trace/checkpoint verification; synthetic failure tests.
- [x] Real seed20261113 TinyUNet/ViT pair, 60 region pixel audits, honest validation-only results and timing scope. Full suite/protected files checked in final validation.
- [x] Independent review; fixed failed-run re-summary with regression tests. Final269tests, old Dice42/6, protected2392files pass. C++ download pinned to478670e.
- [ ] Publish code and measured evidence; verify remote commit/download.
- [ ] User C++ execution/report; pending until actually received. ViT execution/interpretation assigned after this first step.

Review focuses: mismatched token ordering, shared encoder initialization, data/seed/control drift, accepted score selected from false history, failure reported as success, accidental original-file overwrite, CPU benchmarks contaminated by concurrent training, report scope implying new test or clinical evidence.
