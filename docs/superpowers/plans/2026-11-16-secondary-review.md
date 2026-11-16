# WSI / IHC progressive disclosure

User-approved scope: simplify only WSI and IHC. Preserve the purple/white shell, stored data and evidence; no TNBC changes. Current deployed source matches 136ebef dist (2196 files); UI version 20.

1. Add behavioral browser checks and capture current views. Expect WSI inspector and IHC aggregate visibility assertions to fail before changes.
2. WSI: default inspector closed, one primary toolbar, collapsible display controls; processing records and duplicate tracing grouped in inspector. Keep stored-result, no-GT and current coverage visible. Preserve camera, selected ROI and overlays on panel changes.
3. IHC: source image plus one selected-cell inspector (crop, labels, score, error sentence, compact class scores). Collapse aggregate results and methods/sources. Keep provided-center scope visible. Maintain mobile image and cell access without overlays obscuring controls.
4. Adapt existing tests only for the changed access paths. Run Node tests and full Chromium/WebKit CI; examine desktop/notebook/mobile captures. Independent code review, then publish the existing Site and repeat the full browser suite on public URLs. Verify source and deployment parity; record screenshots, exact commits, checks and user-verification pending.

Interfaces: existing DOM IDs and JSON schemas remain. Only wsi/ihc HTML, their UI handlers and a page-specific stylesheet change. No model/data edits. Panel grouping must keep automatic candidate selection revealing its details.

Review focus: resize coordinates, responsive fit, error/empty states, evidence reachability, stale cell results, and inadvertent TNBC/shared CSS changes.
