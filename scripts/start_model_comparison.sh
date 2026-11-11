#!/usr/bin/env bash
# Codespaces launcher; frozen model source and separate original-checkout audit.
set -euo pipefail
cd /workspaces/pathology-edge &&
test -f data/manifest.json &&
mkdir -p work &&
PATHOLOGY_VIT_SOURCE="$(mktemp -d /workspaces/pathology-edge/work/vit-source.XXXXXX)" &&
git fetch origin 917038feb5c80b1c7175d94ba44c208d9940220d &&
git worktree add --detach "$PATHOLOGY_VIT_SOURCE" 917038feb5c80b1c7175d94ba44c208d9940220d &&
python - "$PATHOLOGY_VIT_SOURCE" <<'PY'
import runpy
import sys
import uuid
from pathlib import Path

original = Path.cwd()
source = Path(sys.argv[1]).resolve()
work = source / "work"
work.mkdir(exist_ok=True)
(work / "SOURCE_PATH.txt").write_text(str(source) + "\n")
print("SOURCE_DIR=" + str(source), flush=True)
helper = runpy.run_path(str(source / "scripts/run_model_comparison.py"))
before = helper["original_state"](original)
helper["dump"](work / "original-before.json", before)
try:
    helper["run"](source, original / "data", work / ("my-cnn-vit." + uuid.uuid4().hex[:12]))
finally:
    after = helper["original_state"](original)
    helper["dump"](work / "original-after.json", after)
    if before != after:
        raise RuntimeError("Original checkout changed; inspect original-before/after.json")
    print("ORIGINAL_FILES_PRESERVED=true", flush=True)
PY
