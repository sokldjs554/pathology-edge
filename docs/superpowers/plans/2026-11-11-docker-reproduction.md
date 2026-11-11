# Docker reproduction implementation plan

Goal: finish the remaining current-image reproduction gap without changing the user's Codespace.

Architecture: manual GitHub Actions job on hosted Ubuntu 24.04 builds the existing root Dockerfile. It runs the immutable image ID with network disabled, writes evidence to an ignored directory, and uploads logs even on failure. This platform choice is Codex's implementation decision within the user's ordered improvement request.

Spec and scope: [STEP_50](../../STEP_50.md). No scientific outputs, models, UI assets or user implementation are changed. Interview writing stays deferred.

- [x] Confirm user PR #1 merge and record U61 with remote commit/CI evidence.
- [x] Add workflow and container check script using existing tests/audit/static validator; validate shell and YAML before publishing.
- [x] Independently review source identity, failed-command propagation, skip handling, evidence retention, and contribution attribution.
- [ ] Run a real hosted Docker build and inspect container checks and artifact evidence. Do not substitute host-only results for Docker verification.
- [ ] Record actual run and tested source. Ask the user to inspect just the completed run's Summary; keep that contribution pending until reported.

Validation: shell syntax and extracted inline Python syntax, existing full pytest, live manual workflow, C++ import, locked package equality, before/after source hashes, Dice42/6, static demo and HTTP bytes. A failed command must fail its step while preserving prior logs. Local existing suite: 201 passed in 11.76s. Protected scientific/model/demo files: 2392 hashes unchanged. No new mirror tests are needed for orchestration of the existing checks.
