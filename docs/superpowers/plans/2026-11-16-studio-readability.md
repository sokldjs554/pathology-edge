# Studio readability follow-up

User review: first entry must explain A/B comparison; four-panel views need a two/four choice and visible maximize controls; shared-screen text and buttons need readable sizes; WSI provenance should be collapsed; route navigation must use one vocabulary.

Implementation decisions within the requested edit:
- Open the existing comparison workspace with A/B two-panel view. Make the stored improved/worsened boundary actions prominent. Image-only entry says B result exploration.
- Add explicit two/four buttons. Four-panel comparison temporarily collapses the filmstrip to recover vertical space; returning to two restores its previous state. All four panes have labelled maximize/restore controls and preserve the shared camera.
- Increase controls, table and note typography; scroll small workspaces internally rather than shrink image canvases. Close WSI provenance by default without removing sources or scope limits.
- Preserve all experiment data and original user-written algorithms. No new inference.
- Verify behavior with existing remote Chromium/WebKit CI, actual production screenshots and static-asset parity; no managed local browser is available. Publish to the existing public Site and update PR #3. Do not record new user review as completed.
