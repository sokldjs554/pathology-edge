# Paired Seed Repeats Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline. Steps use checkbox syntax for tracking.

**Goal:** Run and audit the accepted loss comparison across three fixed new seeds without touching user source files.
**Architecture:** One standalone stdlib runner freezes source/protocol and invokes the existing CLI in fresh processes. Its read-only summarizer rejects incomplete or inconsistent runs.
**Tech Stack:** Python 3.12, existing PyTorch/NumPy training environment, pytest.
**Spec:** `docs/superpowers/specs/2026-11-10-paired-seed-repeats-design.md`

## Global Constraints

- Seeds `[20261110,20261111,20261112]`; modes `bce_only`, `learner_dice`; 16 epochs/20 steps; no test evaluation.
- Reuse existing model, accepted learner bodies and training loop without edits.
- Freeze package source, reference configuration, manifest and Git state before any run; each process uses frozen source.
- Refuse existing output; preserve failed/partial attempts; no retry, subset mean or best-seed selection.
- Distinguish user execution from Codex real experiments and synthetic test fixtures.

## Review Focus

- Missing/duplicate or mislabelled arms must not yield an apparently complete mean: fixture rejection tests.
- Corrupt checkpoints, source or manifest mismatches must fail audit: fixture mutation tests.
- NaN/out-of-range history or wrong epoch/threshold selection must fail: history/selection fixtures.
- Failure and preexisting output must preserve user files and prior artifacts: runner failure/overwrite tests.
- Snapshot import and real six-run protocol must agree with the audit: real experiment plus source/control hash evidence.

### Task 1: Runner and audited paired summary

**Files:** `scripts/run_loss_repeats.py`, `tests/test_loss_repeats.py`.
**Interfaces:** `freeze(repo, data, output, *, record_path=False) -> dict`, `summarize(output) -> dict`, `run(repo, data, output) -> dict`; CLI `--data`, optional `--output`, or read-only `--summarize`.

- [x] Write fixtures with six reports and explicit positive/negative/tied paired outcomes; assert mean/sample SD and selection checks.
- [x] Add rejection tests for missing report, changed controls/env/model/source/manifest, nonfinite history, wrong best selection and overwrite/failure preservation.
- [x] Run RED, implement minimal snapshot/run/audit functions, run targeted and default suites GREEN.
- [x] Commit task with results recorded in ledger.

### Task 2: Actual verification and user handoff

**Files:** STEP_41 review, STEP_42 protocol/commands, contribution/navigation docs, `artifacts/learning/step42-*` evidence.
**Consumes:** runner CLI and frozen six-run outputs.

- [x] Record U53 accepted boundary answer; mark repeat execution U54 pending.
- [x] Run all six actual experiments in a new ignored directory against prepared TNBC data; audit complete result, preserve all signs and costs.
- [x] Verify frozen imports/source/protected original file hashes; inspect final JSON and document links.
- [x] Publish a pinned standalone runner + checksum command, requiring no Git update and preserving user files; verify download before final handoff.
- [x] Obtain one fresh whole-branch review under executing-plans, address material findings, commit and integrate within existing authorization.
