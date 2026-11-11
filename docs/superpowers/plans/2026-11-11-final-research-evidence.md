# Final Research Evidence Implementation Plan

> **For agentic workers:** execute tasks with isolated file ownership; independent evidence export and repeat-runner work may run in parallel. Use the project tests and one fresh review before integration.

**Goal:** Complete every independently executable part of the four approved follow-ups and make user-dependent steps concrete without falsely marking them done.
**Architecture:** Portable experiment evidence, read-only visual audit, paired-seed extension of existing runner. Keep reference and user runs separate; defer the user model-body implementation.
**Tech Stack:** Python stdlib, NumPy, Pillow, existing PyTorch/pytest, GitHub Actions Docker workflow.
**Spec:** docs/superpowers/specs/2026-11-11-final-research-evidence-design.md

## Global Constraints
See spec: preserve original outputs and source, no test decoding, no new dependencies, reject unsafe archives, predeclare seeds 20261113/14/15, retain failed outputs. User implementation and user archive availability are dependencies, not implied completion.

## Review Focus
- Archive traversal/symlink/extra files must fail before writes outside destination.
- Old runs' absolute data paths must relocate without silently changing original evidence.
- Partial/corrupted or mismatched-environment runs cannot become successful pooled reports.
- Visualization counts and crops must derive from saved probabilities and GT; no biological cause inferred from color alone.
- User code and original source stay unchanged during export/training, including worker failure.

### Task 1: Portable evidence
Files: scripts/export_research_evidence.py, tests/test_research_evidence.py. Interface: export_bundle(cpp_run, vit_run, output), verify_bundle(bundle). Standard-library standalone exporter, no inference. Include required source, protocols, original states, model/history, predicted probability, raw C++ timings; SHA manifest. Reject symlinks, output overlap, overwrite, missing/failed runs and inconsistent submitted model hashes. Test before implement, then verify actual reference-copy and corruption failures. User execution is a later single step.

### Task 2: Repeat experiment
Files: scripts/run_model_comparison.py, src/pathology_edge/model_comparison.py (CLI seed only), scripts/run_model_repeats.py, tests/test_model_repeats.py and existing runner tests. Interfaces: backward-compatible run(..., seed=SEED, architecture_order=ARCHITECTURES), summarize(..., data_override=None). Pin complete seeds before training; fresh workers, alternating order, fail-closed audits; freeze all code/data/env and compare allowed source differences explicitly for reused original. Tests cover seed mismatch, incomplete pair, order, data relocation, no overwrite, no silent aggregation of environments. Run development reference pairs after code freeze.

### Task 3: Error analysis
Files: scripts/analyze_model_errors.py, tests/test_model_error_analysis.py. Interface: analyze(run, data, output, provenance_label). Audit run via trusted current auditor with data override; select deterministic max/min Dice delta, retain all images. Export GT/RGB/prediction/FP/FN PNG panels and JSON metrics/crop/selection, static index.html. Test exact synthetic counts, source preservation, invalid probability/GT, ties and absent direction. Generate a labeled development-reference report and inspect rendered figures. User-specific report awaits archive.

### Task 4: Integration and handoff
Files: docs/RESEARCH_FOLLOWUP.md, docs/STEP_56.md, evidence validation records. Full suite + saved Dice audit; protected output manifest; fresh whole-branch review; commit/publish source and run pinned Docker workflow, preserve results. Provide one executable export command and expected output. Record pending user archive, user model code, and actual user repeat execution separately. Do not claim all four completed before dependencies arrive.
