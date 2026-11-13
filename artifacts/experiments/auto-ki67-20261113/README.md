# Automatic Ki-67 research evidence — 2026-11-13

Read `docs/AUTO_KI67_EXPERIMENT.md` for results and limitations, `docs/AUTO_KI67_EXTERNAL_PROTOCOL.md` for the frozen external scope. `viewer.html` is a self-contained **stored-result review**, not live model inference.

Implemented RGB-only automatic detection/classification/ratio estimation; compared the frozen color LR with three morphology CNN seeds. **The initial detector strongly overdetects. External performance improvement was not established.** All seeds and negative results remain in the evidence. Existing user-authored code and U86 contribution records are preserved; no new user execution/review is claimed.

## Files

- `protocol.json`, `selection-lock.json`, `training.log`, `cnn-*.pt`: fixed choices, validation selection and actual learned weights.
- `results.json`: all407 reused Patherea test images, ten case aggregates and all four arms.
- `external/`: all133 official BCData validation images, source/hash audit and tumor-only metrics. No fitting on external data.
- `independent-audit.json` and `external/independent-audit.json`: 1,628 + 532 independent point-based metric recounts; no extra inference.
- `desktop.png`, `mobile.png`, `browser-check.json`: actual Chromium rendering at1440px and390px and12 example/model combinations. Browser used localhost HTTP because managed `file://` navigation was blocked.
- `source/`: exact source bytes used by the experiment, independent auditor and figure exporter. Frozen source files avoid changing a historical protocol when later code evolves.
- `verification.json`: CI, learner preservation and scope. `MANIFEST.json` will enumerate SHA256 values.

Raw RGB/HDF5/mask datasets and full cell-level prediction records are not redistributed. Their hashes and reproducible commands allow authorized local acquisition and re-evaluation. Three Patherea crops/point overlays in the review figure are attributed to Patherea (CC BY-NC4.0); transforms are overlays and display scaling. BCData is for non-commercial research and its raw data/individual-cell coordinates are excluded.

## Reproduction (Linux / Codespaces)

Run from the repository root. Use a fresh output name; stages never overwrite a previous run. Existing learner files need not be edited. Existing project Python environment is adequate for Patherea. For external HDF5 input additionally install `h5py==3.15.1` (`requirements-ki67-external.txt`). No GPU is required.

Set `PATHOLOGY_IHC_DATA` to an authorized local extraction of the **hash-locked** Patherea Breast P1 v1.1 dataset. The `protocol.json` records original machine paths only for provenance; prepare a new run for your local path.

```bash
export PYTHONPATH="$PWD/artifacts/experiments/auto-ki67-20261113/source"
python -m pathology_edge.ki67_experiment prepare \
  --data-dir "$PATHOLOGY_IHC_DATA" --assets artifacts/ihc \
  --output work/my-auto-ki67
python -m pathology_edge.ki67_experiment fit --output work/my-auto-ki67
python -m pathology_edge.ki67_experiment evaluate --output work/my-auto-ki67
python scripts/audit_auto_ki67.py --run work/my-auto-ki67 \
  --output work/my-auto-ki67/independent-audit.json
```

These commands respectively audit/freeze inputs, train/choose using training+validation only, score the reused test set, and independently recount results. CPU version differences can change learned models; no bit-identical cross-platform result is promised. Already published old experiments remain unchanged.

For **actual image-only inference** using this run's frozen weights:

```bash
python -m pathology_edge.ki67_experiment infer \
  --run work/my-auto-ki67 --image /path/to/your/authorized-patch.png \
  --classifier cnn-20261113 --output work/my-auto-ki67/new-image.json
```

No annotation path is supplied. Unknown scales/stains remain outside demonstrated accuracy. To reproduce the supplied weights directly, copy `protocol.json`, `selection-lock.json`, `cnn-*.pt` into a fresh private run plus the existing `artifacts/ihc/{source-manifest.json,split.json,model.json}` whose hashes the protocol verifies. `infer` does not read the historical dataset path or annotations.

For external evaluation use the committed399-entry `external/entries.json` and prior-test-pixel hashes. To prepare a fresh external run through the CLI, supply the full official archive central-directory manifest matching SHA `c40aa87...f92` (original source audit) and `artifacts/experiments/bcdata-full-test-20261112/input-audit.json`. Alternatively copy the published external protocol/entries/prior-test hashes into a fresh private directory and use the original frozen model run: its protocol hash must match exactly. Run `python -m pathology_edge.ki67_external evaluate --run <frozen-run> --output <fresh-external-directory>`. It fetches133 images and266 HDF5 files by checked byte ranges, releases raw bytes after each image, and retains private point predictions for the independent audit. A future rerun of these same exposed images is a reproduction, not a new unseen validation.

The annotation matching convention is native6px, maximal cardinality first and minimal distance second, not a claim of reproducing the official paper's evaluation. No patient/slide mapping, independent clinical reference or exhaustive WSI labels were acquired.
