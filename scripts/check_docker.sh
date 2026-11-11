#!/usr/bin/env bash
# Run inside the built image. The workflow supplies a fresh evidence directory.
set -euo pipefail
cd /app
EVIDENCE_DIR="${1:?Pass the mounted evidence directory}"
unset PYTEST_ADDOPTS PYTHONOPTIMIZE PYTHONPATH

sha256sum --check --strict --quiet "$EVIDENCE_DIR/source-files.sha256"
cp /etc/os-release "$EVIDENCE_DIR/container-os.txt"
python - "$EVIDENCE_DIR" <<'PY'
from importlib import metadata
import json, platform, sys
from pathlib import Path
import pathology_edge
from pathology_edge import _patch_cpp

out = Path(sys.argv[1])
expected = Path('/app/src/pathology_edge')
package, cpp = Path(pathology_edge.__file__).resolve(), Path(_patch_cpp.__file__).resolve()
if package != expected / '__init__.py' or cpp.parent != expected:
    raise RuntimeError(f'Unexpected imports: {package}; {cpp}')
versions = {}
for line in Path('requirements-lock.txt').read_text().splitlines():
    if line and not line.startswith('#'):
        name, wanted = line.split('==', 1)
        versions[name] = {'expected': wanted, 'actual': metadata.version(name)}
(out / 'dependency-versions.json').write_text(json.dumps(versions, indent=2) + '\n')
if any(v['expected'] != v['actual'] for v in versions.values()):
    raise RuntimeError('Installed package versions differ from the lock')
record = dict(python=sys.version, executable=sys.executable, platform=platform.platform(),
              package=str(package), cpp=str(cpp))
(out / 'container-environment.json').write_text(json.dumps(record, indent=2) + '\n')
print('Source hashes, locked versions and Python/C++ imports match.')
PY
python -m pip check 2>&1 | tee "$EVIDENCE_DIR/pip-check.log"
python -m pytest -q --junitxml "$EVIDENCE_DIR/pytest.xml" 2>&1 | tee "$EVIDENCE_DIR/pytest.log"
python scripts/audit_dice.py --output "$EVIDENCE_DIR/dice-audit.json" 2>&1 | tee "$EVIDENCE_DIR/dice-audit.log"
python scripts/validate_demo.py 2>&1 | tee "$EVIDENCE_DIR/static-demo.log"

# Exercise the same HTTP server command as the image default, on container loopback.
python -m http.server 8000 --directory dist --bind 127.0.0.1 > "$EVIDENCE_DIR/http-server.log" 2>&1 &
SERVER_PID=$!
trap 'kill "$SERVER_PID" 2>/dev/null || true' EXIT
python - "$EVIDENCE_DIR" <<'PY'
import hashlib, json, sys, time, urllib.error, urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

out = Path(sys.argv[1])
root = ET.parse(out / 'pytest.xml').getroot()
suites = list(root.iter('testsuite'))
counts = {key: sum(int(s.get(key, 0)) for s in suites)
          for key in ('tests', 'skipped', 'failures', 'errors')}
if counts['tests'] <= 0 or any(counts[k] for k in ('skipped', 'failures', 'errors')):
    raise RuntimeError(f'Test suite must run without skips/failures/errors: {counts}')
if counts['tests'] != len(list(root.iter('testcase'))):
    raise RuntimeError('JUnit test counts do not match its cases')
audit = json.loads((out / 'dice-audit.json').read_text())
if not (audit['dice_checks'] == 42 and audit['mean_checks'] == 6
        and audit['training_run'] is False and audit['model_inference_run'] is False):
    raise RuntimeError('Stored Dice audit scope differs')
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
for attempt in range(30):
    try:
        with opener.open('http://127.0.0.1:8000/', timeout=2) as response:
            served = response.read()
        break
    except urllib.error.URLError:
        if attempt == 29:
            raise
        time.sleep(0.1)
if served != Path('dist/index.html').read_bytes():
    raise RuntimeError('HTTP response differs from the saved demo')
record = dict(tests=counts, dice_checks=42, mean_checks=6, static_demo_check=True,
              http_index_sha256=hashlib.sha256(served).hexdigest(),
              dataset_experiment_run=False, browser_test_run=False,
              unit_tests_may_run_synthetic_model_operations=True)
(out / 'checks.json').write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record))
PY
sha256sum --check --strict --quiet "$EVIDENCE_DIR/source-files.sha256"
printf 'All container checks passed; tracked source files stayed unchanged.\n'
