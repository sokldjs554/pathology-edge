# Candidate union / binary CNN evidence

Three paired seeds, 12 epochs each; 504 validation configurations per seed.
**0/3 eligible models. No new internal-test or BCData inference.**

- `protocol.json`, `protocol.sha256`: pre-training source/input lock.
- `selection.json`, `selection-lock.json`: all three seed outcomes, including failures.
- `validation-*.json.gz`, `validation-scores-*.npz`, `trials-*.json.gz`: all 227 validation images, saved exact float32 scores and 1,512 trials.
- `diagnostic-*.pt`: diagnostic best-F1 weights, not eligible selected models.
- `frozen_source/`: original training source; `audit.json`: independent metric/selection recount and 681 image/checkpoint replays.
- `internal-not-run.json`, `external-not-run.json`: explicit zero-inference outcome.
- `failure-analysis.json`: post-selection criterion diagnosis, not retuning.
- `review/index.html`: standalone six-example, four-panel review; `review/browser.json` and screenshots record 1440/390px checks.
- `preservation.json`: seven learner files unchanged; public demo Git diff empty.

The full audit CLI requires the original raw dataset and frozen prior checkpoints at protocol paths. A public checkout alone does not contain those raw inputs. The review HTML embeds only six public Patherea examples. No BCData raw images/coordinates are included. These are reused-validation research results, not clinical or whole-WSI verification. The user approved the design/execution; user review of this new screen is pending.
