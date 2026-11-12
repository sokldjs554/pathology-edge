NuCLS SP.3 linked annotated-support evaluation, 2026-11-13 KST.
51 RGB/CSV/mask triplets acquired;36 shape-mismatched pairs quarantined BEFORE inference.
15 FOVs/four case groups evaluated with frozen models, original and supplied RGB.
Five original SVS streams were verified against GDC MD5; full5GB files are NOT included.
Original crop byte ranges/metadata/hash records are in original-acquisition.json.
No training, threshold tuning, clinical validation or whole-WSI ground-truth validation.
A0SP overlaps a previously evaluated external patient; not four new independent patients.

Extract into a fresh directory. With project Python dependencies installed:
python audit_results.py .
The audit reads stored files only; no model loading, inference or training.
python -m pytest -q test_support.py
Do not run the archived worker inside an existing result directory: it is the original research runner, not a transactional rerun CLI.
The original acquisition scripts need requests,tifffile,imagecodecs,numpy,Pillow and the archived evaluation/source on PYTHONPATH.
probe_sources.py records the historical metadata-query script and depends on the project's earlier public slide catalogue; source-files.json preserves its complete selected outputs.

Published NuCLS datasets license: CC0 1.0; cite Amgad et al., NuCLS, https://arxiv.org/abs/2102.09099.
Official manual annotation description: https://sites.google.com/view/nucls/multi-rater
Format: https://sites.google.com/view/nucls/data-format
Original WSIs: https://portal.gdc.cancer.gov/ (exact public UUIDs recorded).
The project model/pipeline sources are preserved under evaluation/source; user-authored LocalResidualHead is unchanged.
All acquisition/this experiment/audit were run in the provided development environment, not reported as new user executions.
