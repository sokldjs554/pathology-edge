# Progressive review entry implementation plan

> **For agentic workers:** use superpowers:executing-plans to implement the requested follow-up directly in this worktree.

**Goal:** First-time visitors see a large A/B comparison, case actions and one scoped result before detailed controls.

**Architecture:** Retain the existing static viewer, state and evidence validation. Consolidate presentation controls into one native details menu; remove the rail and duplicate comparison selectors. A compact outcome reads only verified saved case data. Keep current neutral colors.

**Tech Stack:** HTML/CSS/JavaScript and existing Playwright CI.

**Spec:** Current user review: initial A/B + improved/worsened cases + zoom/fit + one result; defer 4-pane, candidates, merge, layers, coordinates and experiment evidence. Existing authorization covers implementation and publication without another design approval.

## Global constraints

- No changed experimental data, new inference or altered user algorithms.
- Retain all advanced functions through explicit, accessible controls.
- Preserve same-position comparison, mobile use, error states and scope distinctions.
- Do not record user review of the new revision until confirmed.

## Review focus

- Case result stale after sample/mode changes: clear the compact summary.
- Menu dismissal and keyboard focus: Escape/outside click close; actions return focus meaningfully.
- Case navigation from data/single/merge layouts: restore the boundary comparison.
- Small viewport: menu must scroll and not push/clamp the image out of view.
- Stored evidence fails validation: never display unverified improvement.

## Tasks

- [x] Update index/studio/viewer presentation: one command area, no rail, advanced menu, compact outcome and result-first panel.
- [x] Adapt existing browser paths to open the real advanced controls; add first-entry, scoped result, menu focus and responsive regression coverage.
- [x] Run Node/static checks and full Chromium/WebKit + CPU CI. Inspect screenshots and fix observed failures.
- [x] Publish the same source, compare deployed files and run production browser checks; save screenshots and reports, update PR #3 and user instructions.

## Execution notes

- Baseline `bf972c2`: new browser requirements failed (missing advanced entry and compact outcome); existing 55 passed. Node/static checks passed after initial implementation.
- Retained the existing isolated UI branch and public Site audience. Sites helper is absent; existing hidden-stdin source helper verified source commit `d908780f0a4ee7a9e75b1eb60c438b3a78c2dcc5` before editing.
- Review identified conflicting combined-state CSS selectors from the earlier workbench; new entry stylesheet uses an explicit page scope so candidate and mobile grids retain the intended columns/rows.

- Independent source review found four issues: combined-state CSS grid conflicts, case routes from B-only/candidate layouts, stale case summary in candidate view, and panel focus. All were addressed in `62da05a` with route, dimension, summary and focus assertions. Case selection preserves an explicitly opened panel.
- Browser run `43744928147`: 56 passed / 3 failed per browser (reserved empty tray row, mobile opacity, case selector). Run `43745449208`: 60 passed / 1 failed (legacy mobile `display:none !important`). Fixed at source with a page-scoped override, retaining the other pages' rules.
- Pre-production checkpoint `cf8eec2`: checkout run `43745928614`, Chromium 61/61 and WebKit 61/61; no skips, failures or flaky tests. CPU run `43745928686`: 462 tests, 42 Dice values and 6 means match; Node 14/14. Desktop, four-pane, candidate and tablet/mobile captures inspected. No further UI edits after these checks.
- Sites version 13 deployed the matching source `733501c4e78b66eea660f5e70facb44c3e1567bf`. Publication retained the public audience. Production verification follows.

- First production run `43746550399` exposed a real async ordering regression: choosing 4-pane while a case image loads could be overwritten at completion. The paired-layout transition now occurs at request time; later 4-pane choice remains active. Leaving for B-only/data or NMS cancels the pending review intent. Added a deterministic browser test holding the case image response before changing layout.

- Final implementation `3c893c5`; test synchronization follow-up `27eb62a` has identical dist. Checkout run `43747305455` and production run `43747526658`: Chromium/WebKit 62/62 each, no skips/failures/flaky cases. CPU run `43747305456`: 462 passed; 42 Dice values and 6 means match; Node 14 passed.
- Published Sites version 14, source `01be56294db63114ba1944259e8b09ffb9384155`. All 2,195 deployed files match `27eb62a`. Final reports and production screenshots: `artifacts/ui-progressive/`. User review remains unconfirmed. Main and research worktrees were left unchanged.
