PathologyEdge: missed centers and recall tradeoffs

Open review.html in a browser. It displays stored results, not new inference.
Start with STEP_82.md; user review remains pending.

Read KI67_RECALL_DIAGNOSIS.md for all three seed outcomes, adverse F1 results, and scope.
No training in this increment. Seed20261117 alone meets fixed validation recall floors.
The previous default and all prior experiments remain unchanged.
BCData raw RGB, reference coordinates and per-cell predictions are excluded.
External aggregate/per-image results and full local audit report are included.

Optional public numerical audit (from this extracted folder, Python+NumPy+SciPy):
python scripts/audit_ki67_recall.py --run . --scope public --report my-public-audit.json
This checks validation and internal predictions only; it does not independently
recount omitted external coordinates and does not run new model inference.

Model replay needs original datasets/prior hash-locked experiment folders; absolute
paths in protocol.json document the execution machine, not folders on your machine.
Source and existing inference model package:
https://github.com/sokldjs554/pathology-edge/tree/feat/auto-ki67
https://raw.githubusercontent.com/sokldjs554/pathology-edge/8ba7d50e37579dd2e2782d8fd40549375d024896/artifacts/handoff/PathologyEdge-LearnedCenters-20261113.zip

Images/points: Patherea Breast-P1 v1.1, Dejan Stepec et al., CC BY-NC4.0.
https://huggingface.co/datasets/ds2268/patherea
https://creativecommons.org/licenses/by-nc/4.0/
Derived material adds predicted points, metrics and display overlays.
Research/education only; not clinical or whole-WSI validation.
