# Studio redesign implementation plan
> Use superpowers:executing-plans. User already requested direct implementation and corrected the visual direction; no repeated design approval.

Goal: three visibly distinct functional review layouts.
Architecture: retain source/candidate engines; studio controller adds layouts/reference views; scoped shared CSS replaces the silhouette across routes.
Spec: ../specs/2026-11-16-studio-redesign.md

- [x] Observe the laptop-layout regression fail before implementation.
- [x] Add main-view layout controls, original/truth reference canvases, shared camera rendering and gestures. Files: dist/index.html, dist/studio-ui.js, dist/app.js, dist/workbench-ui.js.
- [x] Replace the old three-column layout with mode rail, bottom filmstrip, optional drawer and side data table. File: dist/studio.css. Apply shared shell and horizontal case/ROI collections to wsi.html and ihc.html.
- [x] Verify all existing workflows, actual source pixels, mode-specific laptop/mobile screenshots, unchanged experiment hashes and fresh independent review.
- [x] Publish to the same Site, verify deployed bytes and browser flows, update PR and documentation. Do not mark user verification complete.

Constraints: no model/result mutation, no new runtime dependency, no substitute local browser. Use existing remote Chromium/WebKit workflow. Existing user-authored algorithms remain untouched.

Review: the initial browser run passed 48/52, exposing IHC panel hiding and small-view height constraints. Independent review also found the mobile A-to-data hidden-canvas transition and combined hidden-state CSS specificity. All fixes passed the final checkout Chromium/WebKit suites (53 each). First screenshots exposed inherited 100%-width slide cards and fit-scale thumbnails; fixed the filmstrip width and use native source resolution for desktop image entry. A subsequent mobile visual review found a 75px-high data-view canvas; the new readability regression failed before a minimum-height/scroll correction, then passed in both browsers.

Final evidence: UI d722879, Sites v11, checkout run 43737632265 and production run 43737884212 both 53/53 per browser; CPU run 43737636357 passed 462 tests; 2,193 deployed files match. PR #3 updated; main and research checkouts preserved. User review remains pending.
