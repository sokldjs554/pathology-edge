# Linked Workbench Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a visibly reorganized pathology viewer with synchronized panes and linked candidate data.
**Architecture:** Preserve the current canvas/state engine. Add a small pure candidate-data helper and a UI controller, with explicit refresh hooks into the existing selection and phase lifecycle.
**Tech Stack:** Static HTML/CSS/JS, Node tests, Python artifact validation.
**Spec:** docs/superpowers/specs/2026-11-16-linked-workbench-design.md

## Global Constraints
- No experiment/model/data changes; user-owned source is untouched.
- Browser QA must be reported unverified if managed browser controls remain unavailable.
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
- [ ] Write and run tests for original-index retention, exact ID queries, viewport/edge filters, empty lists and clipped crops; observe missing module failure.
- [ ] Implement immutable helpers and run `node --test web-tests/*test.cjs`.

### Task 2: Linked workbench layout and controls
**Files:** dist/index.html, dist/workbench.css, dist/workbench-ui.js, dist/app.js, web-tests/workbench.spec.js
**Interfaces:** WorkbenchUI.refresh() reads the existing state and selection, renders the dock and crop; existing selectObject performs image navigation.
- [ ] Add browser regression cases for row-to-view linking, image switches, maximize/restore and mobile overflow; run only if managed browser QA is available.
- [ ] Reorganize actual DOM, integrate refresh hooks, implement controls and responsive styling.
- [ ] Run JS syntax, data tests and static artifact linkage; verify original result/asset hashes.

### Task 3: Verify and publish
**Files:** docs/UI_LINKED_WORKBENCH.md, deployment artifact/metadata
- [ ] Run available existing non-browser checks and record exact scope, limitations and source commit.
- [ ] Review implementation for state reset, accessibility, visible/hidden panes and preserved numeric data.
- [ ] Push reviewed code, publish to the existing site if possible, verify deployed source/asset bytes.

Pre-flight: Task 2 consumes Task 1 original-index rows and bounded crop; no conflict. Task 3 consumes the unchanged exported assets from Task 2.
User requested direct implementation; proceed without another design/plan approval gate.
