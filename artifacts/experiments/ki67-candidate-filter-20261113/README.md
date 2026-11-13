# Candidate-filter research addendum · 2026-11-13

Internal localization F1 improved0.098239→0.125999; external BCData tumor-class F1 fell in all4arms. Keep as a research comparison; not adopted in the public demo.

Open `review.html` in a browser. First example:107→90candidates, TP3→3, FP104→87, FN4→4. Toggle removed-candidate display. User review is pending.

`patherea-results.json` / `bcdata-results.json`: full image/case counts, ratios, coverage, prior/filtered metrics. Whitespace was compacted; JSON values are identical to audited run files (provenance.json records both hashes).
`gate.json`: exported correspondence-proxy filter, not clinical cellness probability.
`protocol.json`, `threshold-selection.json`, `selection-lock.json`: pre-scoring controls and locked hashes.
`frozen_source/`: byte-identical experiment sources from a1ec2b9, plus package initializer.
Audits recount original private point arrays without importing the new evaluator; original BCData RGB/HDF5/individual point coordinates are not redistributed. Full rerun requires the prior complete experiment folders and licensed original data, not this package alone.

Patherea figure images/point annotations: https://huggingface.co/datasets/ds2268/patherea (CC BY-NC4.0). Prediction overlays added. BCData: https://sites.google.com/view/bcdataset (non-commercial research; summary data only here).

This is an addendum, not a replacement for earlier full delivery archives:
- ThroughU86: https://raw.githubusercontent.com/sokldjs554/pathology-edge/ff486a3be0f01fcdc98e9aad5dd67d6a7424d39e/artifacts/handoff/PathologyEdge-Final-Handoff-20261113.zip
- Original automatic experiment: https://raw.githubusercontent.com/sokldjs554/pathology-edge/751f92e5c83069d1bdb651b4b7dce6e9b0d36726/artifacts/handoff/PathologyEdge-AutoKi67-Addendum-20261113.zip
- Current report: https://github.com/sokldjs554/pathology-edge/blob/feat/auto-ki67/docs/KI67_CANDIDATE_FILTER.md

No fresh external, clinical or whole-WSI ground-truth validation. Seven existing user-authored scopes unchanged; no new user execution/review claimed.

Attribution: Dejan Štepec et al., “Patherea: Cell Detection and Classification for the 2020s,” Medical Image Analysis (2025), https://doi.org/10.1016/j.media.2025.103868. Dataset license: https://creativecommons.org/licenses/by-nc/4.0/ . Original RGB images are embedded in the review page; point/retention overlays and UI were added. No endorsement by the authors is implied. This dataset license does not declare a new blanket license for the project code.
