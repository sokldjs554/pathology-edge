# Codespaces Training Reproduction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the user reproduce the existing TinyUNet training in a browser-hosted Ubuntu 24.04/Python 3.12 workspace and retain their own execution evidence.

**Architecture:** Add a development container with the existing Linux CPU dependency lock. Install the repository in editable mode only after the live workspace is mounted. Reuse the existing data and training CLIs, with a fresh `work/` output directory per run.

**Tech Stack:** GitHub Codespaces, Ubuntu 24.04, Python 3.12, the existing PyTorch CPU lock, C++17/pybind11, Bash.

**Spec:** [Approved sequence and role split](../../JOB_MATCH_2026-11-10.md). The user subsequently selected GitHub Codespaces for execution. The exact Ubuntu 24.04 container and post-create editable install are Codex implementation choices.

## Global Constraints

- Preserve the baseline model, saved results and deployed `dist/` files.
- Keep model/loss/comparison implementation reserved for the user's later exercise; do not replace it with Codex-authored experiment changes.
- Do not auto-download data, train, evaluate held-out data or deploy when a Codespace starts.
- Keep the existing seed 20261107, 16 epochs, 20 steps/epoch and training/validation split for the first reproduction.
- Keep user execution pending until their output is received. Label Codex container and host runs separately.
- No new package dependencies or architecture changes; install `requirements-lock.txt`.

## Review Focus

- Editable installation must resolve to the mounted workspace rather than a baked-in copy; check the imported module path inside the container.
- Ubuntu and Python must be the configured versions; inspect `/etc/os-release`, Python and package imports in the built image.
- Each learner run must use a new output directory; verify the documented `mktemp` commands preserve previous outputs.
- Installation or training errors must retain nonzero status even through `tee`; use `pipefail` in the documented Bash sequence.
- Published model/results must remain byte-identical; compare recorded source hashes and Git diffs after reproduction.

## Task 1: Codespaces container and reproduction instructions

**Files:**
- Create `.devcontainer/Dockerfile`, `.devcontainer/devcontainer.json`.
- Create `docs/STEP_34.md` for one user goal: baseline training reproduction.
- Update `README.md`, `docs/RUNBOOK.md`, `docs/NEXT_STEPS.md`, `docs/CONTRIBUTIONS.md`.
- Save Codex execution evidence under `artifacts/learning/step34-*`.

**Interfaces:**
- Consumes the existing `python -m pathology_edge.cli prepare` and `train --data ... --output ... --seed 20261107 --epochs 16 --steps 20` commands.
- Produces an Ubuntu 24.04 container with `/opt/venv/bin/python`, an editable mounted source checkout, and instructions for `training.json`, `protocol.json`, `model.pt` and `train.log` in a new run folder.

- [x] Write minimal container configuration. Configuration is verified through real image build and execution rather than tests that assert file contents.
- [x] Build it locally, execute its post-create command against the mounted checkout, check OS/interpreter/import paths and run the existing full Python suite.
- [x] Reproduce the unchanged 16-epoch training in the built Ubuntu container; inspect the complete log, model metadata and training history. Do not execute held-out evaluation.
- [x] Document setup and one sequential user run, expected outputs, failure evidence and contribution boundaries.
- [x] Verify protected files, documentation links and final diff; prepare the reviewed changes for publication on `main` so Codespaces can use the configuration.

## Verification and final review

Local Docker build and exact post-create/environment commands passed on Ubuntu 24.04.5/Python 3.12.3. Both the Debian host and Ubuntu container passed 107 existing tests and reproduced the 16-epoch baseline history, configuration, selected epoch/threshold and model weights/SHA256. All 2,464 original artifact/dist hashes stayed unchanged. Evidence is in `artifacts/learning/step34-preparation.json`.

One independent read-only review found that `export VAR="$(mktemp ...)"` could mask directory-creation failure. The guide now separates assignment/export and chains setup, metadata capture and training with `&&`. Controlled execution of the exact documented block verified that directory and metadata failures stop before training and training failure propagates through `tee`.

Hosted Codespaces startup remains pending user output. Later model comparison is intentionally deferred until the user's reproduction report. Neither is represented as completed by this local preparation.

## Follow-up boundaries

The next comparison exercise depends on the user's reproduction report and is not implemented here. WSI scale integration and model comparisons remain later approved priorities. Host verification can proceed while the user opens their environment.
