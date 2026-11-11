# User refinement evidence

The exact received archive and read-only audit are documented in [the final audit](../../../docs/USER_REFINEMENT_AUDIT.md).

This is the user Codespaces run, separate from `vit-refinement-reference-20261112`. No uploaded source was executed and no checkpoint was deserialized. The portable `re-audited-summary.json` records the relocated audit path; all other values exactly match the user summary. After checking archive paths and file hashes, the trusted repository script can audit the extracted run with `--data-override`:

```bash
python scripts/run_refinement_comparison.py --summarize /path/to/extracted/my-vit-refinement.0881ce7d2afe --data-override data
```

Run from the repository root with the tested Python environment. This recounts stored validation pixels without inference or training.
