# WSI native ROI display implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Display original RGB for the three analyzed WSI regions without re-encoded JPEG loss, and avoid excessive automatic enlargement.

**Architecture:** Reuse each existing 1024×1024 ROI PNG as an SVG image in the existing level-0 overlay, below prediction layers. Keep OpenSeadragon as the unchanged whole-slide camera and background. Cap automatic fits at one CSS pixel per source pixel while preserving their target center; manual enlargement remains available and labeled.

**Tech Stack:** Existing plain JS, SVG, OpenSeadragon, Playwright Chromium/WebKit.

**Spec:** User-approved scope in this conversation: WSI first, original ROI PNG, appropriate zoom; retain existing results and comparisons. No IHC reconstruction or image sharpening.

## Global constraints
- Preserve every image, mask, model, experimental number and native coordinate.
- WSI outside the three RGB ROIs remains the existing JPEG pyramid.
- No learned or synthetic detail; no new inference or accuracy claim.
- Keep the purple/white workbench; reuse toolbar/status space and existing source details.
- No new runtime dependencies or new large assets.

## Review focus
1. RGB placement must match both panes and prediction coordinates, including a panned/clipped ROI.
2. PNG failure, invalid dimensions or timeout must retain the JPEG fallback with an explicit warning and retry.
3. Automatic fit must preserve its requested center at desktop and narrow viewports.
4. PNG must remain independent of prediction opacity/visibility; panel toggles must preserve the camera.
5. Retry must not leave stale image load callbacks, source badges or RGB layers.

## Task 1: Native image and source state
Files: dist/wsi.js, dist/wsi.html; tests: web-tests/wsi-native.spec.js.
- [x] Add browser regression checks for native source href/level-0 boxes, actual rendered PNG pixels, ROI switches, failed PNG and retry.
- [x] Run the new checks on the baseline; confirm missing native display failure.
- [x] Decode existing PNGs with dimension validation and the existing finite load timeout. Track readiness/failure separately from prediction overlays.
- [x] Add decoded ROI images before predictions in the existing SVG layer; expose the actual center image source in the existing position bar.
- [x] Retain base tiles on failure and route retry through image loading. Update source details with the exact mixed display scope.

## Task 2: Readable native zoom
Files: dist/wsi.js, dist/wsi.html, dist/secondary-review.css; tests: web-tests/wsi-native.spec.js, web-tests/wsi.spec.js.
- [x] Add checks that jumps reach the stored target at at most 100%, manual zoom remains available, and original 1:1 restores exactly 100% at the same center.
- [x] Cap fit-derived image zoom at 1 and retain the fit center; move the existing native button to the main zoom group.
- [x] Label manual enlargement using the existing position line, with the CSS pixel definition in help.
- [x] Adapt existing test navigation to the moved button, preserving its assertions.

## Task 3: Verify and publish
- [x] Verify ROI RGB against the retained SVS source and saved pixel hashes; do not regenerate assets.
- [x] Run source browser checks, inspect desktop/notebook/mobile captures, then deploy the existing public Site.
- [x] Confirm public source parity, focused public browser flows and pixel checks; retain captures and evidence.
- [x] Record source/deployment commit, true image-resolution limits and user confirmation pending.
