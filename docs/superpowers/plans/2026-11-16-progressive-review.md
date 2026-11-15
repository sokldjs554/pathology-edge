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

- [ ] Update index/studio/viewer presentation: one command area, no rail, advanced menu, compact outcome and result-first panel.
- [ ] Adapt existing browser paths to open the real advanced controls; add first-entry, scoped result, menu focus and responsive regression coverage.
- [ ] Run Node/static checks and full Chromium/WebKit + CPU CI. Inspect screenshots and fix observed failures.
- [ ] Publish the same source, compare deployed files and run production browser checks; save screenshots and reports, update PR #3 and user instructions.
