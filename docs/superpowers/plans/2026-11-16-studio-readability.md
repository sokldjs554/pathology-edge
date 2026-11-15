# Studio readability follow-up

User review: first entry must explain A/B comparison; four-panel views need a two/four choice and visible maximize controls; shared-screen text and buttons need readable sizes; WSI provenance should be collapsed; route navigation must use one vocabulary.

Implementation decisions within the requested edit:
- Open the existing comparison workspace with A/B two-panel view. Make the stored improved/worsened boundary actions prominent. Image-only entry says B result exploration.
- Add explicit two/four buttons. Four-panel comparison temporarily collapses the filmstrip to recover vertical space; returning to two restores its previous state. All four panes have labelled maximize/restore controls and preserve the shared camera.
- Increase controls, table and note typography; scroll small workspaces internally rather than shrink image canvases. Close WSI provenance by default without removing sources or scope limits.
- Preserve all experiment data and original user-written algorithms. No new inference.
- Verify behavior with existing remote Chromium/WebKit CI, actual production screenshots and static-asset parity; no managed local browser is available. Publish to the existing public Site and update PR #3. Do not record new user review as completed.

## Completed verification

- UI commit: `2852b335654e1739d73b02be89d970234eada9c4`; Sites version 12, source `d908780f0a4ee7a9e75b1eb60c438b3a78c2dcc5`.
- Checkout browser run `43741673952` and production run `43742062792`: Chromium and WebKit each passed all 55 tests, with no skipped, unexpected or flaky tests.
- CPU run `43741679797`: 462 Python tests passed; 42 stored Dice values and 6 image means matched. All 14 Node logic tests passed.
- All 2,193 deployed files match the UI commit. The seven changed dist files are UI source/styles only; stored experiment assets are unchanged.
- Source review identified filmstrip restoration across responsive breakpoints. Fixed and independently rechecked for both initially visible and initially hidden filmstrips. Mobile canvas height failures were corrected and rerun successfully.
- Production screenshots, full browser reports, deployment hashes and verification metadata are saved in `artifacts/ui-readability/`. User verification of this revision remains pending.
