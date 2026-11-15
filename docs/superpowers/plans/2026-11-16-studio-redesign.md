# Studio redesign implementation plan
> Use superpowers:executing-plans. User already requested direct implementation and corrected the visual direction; no repeated design approval.

Goal: three visibly distinct functional review layouts.
Architecture: retain source/candidate engines; studio controller adds layouts/reference views; scoped shared CSS replaces the silhouette across routes.
Spec: ../specs/2026-11-16-studio-redesign.md

- [ ] Observe the laptop-layout regression fail before implementation.
- [ ] Add main-view layout controls, original/truth reference canvases, shared camera rendering and gestures. Files: dist/index.html, dist/studio-ui.js, dist/app.js, dist/workbench-ui.js.
- [ ] Replace the old three-column layout with mode rail, bottom filmstrip, optional drawer and side data table. File: dist/studio.css. Apply shared shell and horizontal case/ROI collections to wsi.html and ihc.html.
- [ ] Verify all existing workflows, actual source pixels, mode-specific laptop/mobile screenshots, unchanged experiment hashes and fresh independent review.
- [ ] Publish to the same Site, verify deployed bytes and browser flows, update PR and documentation. Do not mark user verification complete.

Constraints: no model/result mutation, no new runtime dependency, no substitute local browser. Use existing remote Chromium/WebKit workflow. Existing user-authored algorithms remain untouched.
