# Linked Workbench Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Deliver a visibly reorganized pathology viewer with synchronized panes and linked candidate data.
**Architecture:** Preserve the current canvas/state engine. Add a small pure candidate-data helper and a UI controller, with explicit refresh hooks into the existing selection and phase lifecycle.
**Tech Stack:** Static HTML/CSS/JS, Node tests, Python artifact validation.
**Spec:** docs/superpowers/specs/2026-11-16-linked-workbench-design.md

## Global Constraints
- No experiment/model/data changes; user-owned source is untouched.
- Browser QA must distinguish the existing remote CI browsers from unavailable local managed browser controls.
- WSI/IHC pages retain their behavior and styles.

## Review Focus
- Loading/error or image switches must never retain candidates from a previous image.
- Filtering/sorting must preserve source indexes, even with empty results.
- Maximize must keep the same image coordinates and restore comparison.
- Narrow screens must retain access to examples, results, and candidates.
- Candidate scores must not be presented as calibrated confidence or clinical cell counts.

### Task 1: Candidate data and selection contract
**Files:** dist/workbench-data.js, web-tests/workbench-data.test.cjs
**Interfaces:** WorkbenchData.rows(objects, {query, bounds, edgeOnly}) returns objects with original indexes; cropBox(object, width, height) returns bounded source-image crop.
- [x] Write and run tests for original-index retention, exact ID queries, viewport/edge filters, empty lists and clipped crops; observe missing module failure.
- [x] Implement immutable helpers and run `node --test web-tests/*test.cjs`.

### Task 2: Linked workbench layout and controls
**Files:** dist/index.html, dist/workbench.css, dist/workbench-ui.js, dist/app.js, web-tests/workbench.spec.js
**Interfaces:** WorkbenchUI.refresh() reads the existing state and selection, renders the dock and crop; existing selectObject performs image navigation.
- [x] Add browser regression cases for row-to-view linking, image switches, maximize/restore and mobile overflow; run through the existing remote browser workflow when local controls are unavailable.
- [x] Reorganize actual DOM, integrate refresh hooks, implement controls and responsive styling.
- [x] Run JS syntax, data tests and static artifact linkage; verify original result/asset hashes.

### Task 3: Verify and publish
**Files:** docs/UI_LINKED_WORKBENCH.md, deployment artifact/metadata
- [x] Run available existing non-browser checks and record exact scope, limitations and source commit.
- [x] Review implementation for state reset, accessibility, visible/hidden panes and preserved numeric data.
- [x] Push reviewed code, publish to the existing site if possible, verify deployed source/asset bytes.

Pre-flight: Task 2 consumes Task 1 original-index rows and bounded crop; no conflict. Task 3 consumes the unchanged exported assets from Task 2.
User requested direct implementation; proceed without another design/plan approval gate.

## Execution record
- Task 1: original-index and bounded-crop tests failed before implementation, then passed. A viewport upper-edge regression was reproduced and aligned with the existing half-open viewer filter.
- Task 2: implemented explicit state hooks and independent workbench styling; 2186 pre-existing static files initially matched the old version. Later native-pixel fixes also modify viewer-math.js; experimental data and image assets remain untouched.
- Final review: independent static reviewer reported one important issue (short-screen dock clipping). Fixed with scrollable constrained workspace and a targeted browser test. No minor findings deferred.
- Ruling: the Sites source helper is not installed. Reuse the existing site-source checkout and the existing credential-on-stdin Git/publish helper, preserving the verified commit/archive contract.
- Ruling: do not start an alternate local browser. Use the repository's existing remote Chromium/WebKit workflow; clearly distinguish it from local hands-on QA.
- Ruling: existing pixel-size assertions assumed the old sidebar widths and no pane border. Retain their intended content-fit guarantees using measured pane content bounds and relative single-pane expansion.

- Final browser-test correction: await the saved boundary case ID and expected center before testing pane expansion, so the test does not compare with the previous asynchronous view. This changes test synchronization only.
- Publication: Sites version 8 succeeded; 2,191 deployed static files match `f823bac`. Main and research worktrees remain clean. Branch integration stays reviewable in a PR rather than merging main during this UI task.
- Production browser verification: Chromium and WebKit each passed all 51 tests against the public version 8 URL, with no skips or retries. Screenshots were refreshed from that production run.
