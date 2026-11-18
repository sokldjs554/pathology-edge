# Evidence-first comparison implementation plan

**Goal:** A first-time reviewer can see why patches are compared, how A and B differ, and a real result without searching for a boundary.

**Architecture:** Keep the saved-data viewer, camera, selection engine and all advanced tools. Replace the stacked entry area with a reading sidebar, large paired images, compact image toolbar and a scoped result strip. Initialize the root route on the existing recommended improvement; explicit image/case links retain their requested targets.

**Tech Stack:** Existing buildless HTML/CSS/JS, Canvas, Playwright Chromium/WebKit, existing Python CI.

User requested direct implementation and verification, with no further design approval round. Decisions below are implementation choices, not user-validated usability findings.

## Requirements and decisions

- Keep H&E palette. No landing-page cards or gradients.
- Plain method labels: A: 겹치지 않게 잘라 분석; B: 겹쳐 분석한 뒤 결과 결합. Explain 128px patch / 128px versus 64px step; label any diagram as explanatory.
- Root opens a real, explicitly labeled selected improvement. Regression is equally accessible. Never present the selected region as the average.
- Default case rendering shows each method's actual mask with visible contours; identical corrected/regressed highlights are OFF. Existing toggle remains available and accurately labeled.
- Small A/B/truth masks show the exact selected 64px box, without generating or changing predictions. Whole-box mask display is distinguished from metrics evaluated only on its boundary band.
- Keep candidate selection/table, NMS pair tracing, scope metrics, pan/zoom, navigator, two/four panes, expanded pane, mobile, WSI, IHC, loading/error/empty/retry and explicit deep links.
- No model/data/metric edits. No inference or new experiment. User verification remains pending.

## Implementation / verification

- [x] `dist/index.html`, `review-entry.css`, `review-entry.js`: reading/sidebar layout, scoped status, actual mask miniatures and plain labels. Desktop keeps image height; mobile becomes a compact header with scroll available, no horizontal overflow. Hide long guidance in four-pane/data layouts so existing usable image sizes remain.
- [x] `dist/app.js`, `review-ui.js`: exact foreground contour display; start a saved case only on unparameterized root. Explicit links and later user requests win; empty/missing cases fall back to image view. Update labels when switching to duplicate mode.
- [x] Add `web-tests/clarity.spec.js`: root startup, rendered-mask provenance, A/B unequal pixels, deep links, failure fallback, later selection, viewport controls and scope. Update only prior expectations intentionally changed; existing functionality assertions stay.
- [x] Run Node/static checks, full existing browser matrix and CPU checks. Inspect screenshots of first view, improvement/regression, masks, advanced/candidate/four-pane, mobile, WSI/IHC. Independent code review; resolve material issues.
- [x] Publish exact checked source; production browser matrix, file hash comparison, actual screenshot capture; commit verification and update draft PR without merging.

## Review focus

- Automatic case navigation must not overwrite a user sample/layout selection during asynchronous loading.
- Drawing contours must use actual stored foreground and not change masks used by Dice or highlights.
- Sidebar placement must not shrink candidate/expanded/four-pane views or hide popup tools.
- Changing image/mode must clear stale case miniatures, labels and scores.
- Explicit sample links and missing case metadata must remain usable; controls must work during recovery.

## Verification and review record

- Frozen UI: `cbe1910fb2bb2ee9df6d344de2edb662839c7dd4`. Deployment version 18, Site source `08e56df844ca1b057ad2bc0a2c0e39ee04089a09`.
- Checkout CI `43813930114` and public production CI `43814496194`: 73/73 expected in both Chromium and WebKit, zero skipped/unexpected/flaky.
- CPU CI `43813930136`: 462 passed, 42/42 stored Dice and 6/6 image means matched. Node: 14 passed. Static demo validation passed.
- Independent source review: resolved startup layout overwrite with a revision guard and delayed-loading tests; restored the mobile scope caption and added its visibility check; made the explanatory diagram qualification visible. Browser-discovered mobile geometry issues were corrected before the full final runs.
- Source-to-Site equality: all 2,196 dist files; live HTTP hashes: 10 selected files. Stored predictions, experimental results and learner code unchanged.
- Actual production screenshots inspected: first view, regression, duplicate comparison, four panes, candidate data, mobile, WSI and IHC. Detailed records: [first-visit verification](../../UI_FIRST_VISIT.md).
- This is implementation and browser evidence, not a user/interviewer usability study. User review of this revision remains pending.
