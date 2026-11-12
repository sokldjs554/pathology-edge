# Full official BCData test: qualified diagnostic evaluation

All **402 PNG + 804 HDF5** source files were acquired and byte/CRC/SHA checked.
The strict initial protocol failed on same-label repeated coordinates and three empty shape `(0,)` arrays.
A documented amendment was fixed **before new-image inference**. It evaluated **65,165 unique centers**
after removing 267 repeated records from 65,432 original rows, with no ROI omitted.

Full-set accuracy: **19.9678%**; mean per-ROI tumor-positive-ratio error: **44.7427 pp**.
New 392-image subset: **19.7166% / 45.2652 pp**. The old 10-image subset is separately reported and
exactly reproduces its earlier results. This is a native-pixel GT-center diagnostic check, not an
unmodified-source benchmark, patient-independent validation, detector evaluation, or clinical/WSI score.

See the [report](../../../docs/BCDATA_FULL_TEST.md), [results](results.json),
[independent verification](verification.json), and [all extremal-case references](case-references.json).
`protocol.json` and `strict-input-audit.json` retain the failed original conditions;
`diagnostic-protocol.json`, `input-audit.json`, and `inference-lock.json` document the amended run.

The [official page](https://sites.google.com/view/bcdataset),
[paper](https://link.springer.com/chapter/10.1007/978-3-030-59722-1_28), and
[official archive](https://drive.google.com/file/d/16W04QOR1E-G3ifc4061Be4eGpjRYDlkA/view)
are the sources. Non-commercial research only; raw-data redistribution rights were not established.
This bundle contains own code, protocols, manifests/hashes, per-ROI counts, and aggregate results.
Original images/HDF5, coordinate maps, cell predictions, and local comparison HTML remain in ignored `work/`.

## Reproduction

Use Python 3.12.14 and the pinned dependencies in `requirements.txt`. Independently acquire the originals
under a private `BCDATA_PARENT` containing `BCData/images/test/` and `BCData/annotations/test/`.
Every file must match `input-manifest.json`. For permitted acquisition, `acquire.py` uses bounded
HTTP206 ranges and refuses full ZIP responses; it never downloads or executes external code.

From the repository root, using a fresh output directory:

```bash
python3.12 -m venv work/bcdata-replay-venv
work/bcdata-replay-venv/bin/python -m pip install -r artifacts/experiments/bcdata-full-test-20261112/requirements.txt
BCDATA_PARENT=/absolute/path/to/independently_acquired_data
EVIDENCE=artifacts/experiments/bcdata-full-test-20261112
RUN=work/bcdata-full-replay
PYTHON=work/bcdata-replay-venv/bin/python

"$PYTHON" "$EVIDENCE/test_canonicalize.py"
"$PYTHON" "$EVIDENCE/evaluate.py" audit \
  --data-dir "$BCDATA_PARENT" --output-dir "$RUN" \
  --canonical-points "$RUN/canonical-points.jsonl.gz"
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  "$PYTHON" "$EVIDENCE/evaluate.py" evaluate \
  --data-dir "$BCDATA_PARENT" --output-dir "$RUN" \
  --canonical-points "$RUN/canonical-points.jsonl.gz" \
  --private-predictions "$RUN/predictions.jsonl.gz"
"$PYTHON" "$EVIDENCE/verify.py" \
  --data-dir "$BCDATA_PARENT" --results-dir "$RUN" \
  --canonical-points "$RUN/canonical-points.jsonl.gz" \
  --predictions "$RUN/predictions.jsonl.gz" --output "$RUN/verification.json"
"$PYTHON" "$EVIDENCE/make_private_review.py" \
  --data-dir "$BCDATA_PARENT" --predictions "$RUN/predictions.jsonl.gz" \
  --output "$RUN/private-review.html"
```

Existing output files are refused. The verifier independently reopens original HDF5, reconstructs unique
centers and the duplicate map, checks every input hash and saved probability argmax, recounts every ROI
and subgroup, and compares fresh replay aggregates with the published run. It does not import evaluator
or project metric functions. Four synthetic regression tests cover empty arrays, duplicate ordering,
conflict exclusion, fractional/nonfinite/out-of-bounds exclusion without rounding, and malformed shapes.

The first run used 266,720,505 bytes of source files, 254,420,585 transferred range bytes, and about
55 seconds for local feature extraction/inference/reporting. Acquisition used four workers; the 30 prior
probe files were reused after validation. Full original archive SHA-256 is unavailable because the full
archive was not downloaded. See `acquisition.json` and `sources.json`.

All 402 ratio denominators were defined. The predicted denominator contains only predicted tumor classes;
42,100 of 65,165 supplied tumor centers were predicted as nontumor. The smallest ratio error (`109.png`,
0.07049 pp) still has only 30.08% correct cell labels. Three worst-ratio ties (`367/378/379`) each have
100 pp error. These are descriptive results; no clinical thresholds or patient-level confidence intervals
were inferred, and physical-resolution equivalence was not established.
