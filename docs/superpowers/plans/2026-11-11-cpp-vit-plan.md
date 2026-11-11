# C++ / ViT implementation plan

Goal: prepare both authorized improvements while assigning one user task at a time.
Spec: [design](../specs/2026-11-11-cpp-vit-design.md).

Already isolated at `/workspace/pathology-edge-loss`, base9ce624b; existing201tests pass. No new dependencies.

- [ ] C++ independent runner, safety/parity tests, one real benchmark, STEP_51.
- [ ] SmallViTSegmenter, token-to-pixel geometry/gradient/state/input tests.
- [ ] Separate `model_comparison.py` trainer and `run_model_comparison.py` runner; source snapshots, immutable outputs, manifest/crop-trace/checkpoint verification; synthetic failure tests.
- [ ] Full existing suite, scientific file hashes, real seed20261113 TinyUNet/ViT pair, honest validation-only results and timing scope.
- [ ] Independent review; publish code and measured evidence; pin user's C++ download to a committed SHA.
- [ ] User C++ execution/report; pending until actually received. ViT execution/interpretation assigned after this first step.

Review focuses: mismatched token ordering, shared encoder initialization, data/seed/control drift, accepted score selected from false history, failure reported as success, accidental original-file overwrite, CPU benchmarks contaminated by concurrent training, report scope implying new test or clinical evidence.
