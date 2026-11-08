"""Read every deployed static asset and compare it with a clean dist commit.

Only a previously inspected Cloudflare challenge template may be removed from
HTML, after hashing all of its bytes except request-specific ray/time fields.
No arbitrary HTML normalization or script removal is accepted.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import threading

import requests


_worker = threading.local()


def digest(value):
    return hashlib.sha256(value).hexdigest()


def compare(path, root, base):
    name = path.relative_to(root).as_posix()
    if not hasattr(_worker, 'session'):
        _worker.session = requests.Session()
    response = _worker.session.get(base.rstrip('/') + '/' + name, timeout=60)
    response.raise_for_status()
    received = response.content
    source = received
    injection = None
    if name.endswith('.html'):
        match = re.search(rb'<script>([\s\S]*?)</script>(?=</body>)', received)
        if match:
            raw = match.group(0)
            canonical = re.sub(rb"r:'[0-9a-f]+'", b"r:'RAY'", raw)
            canonical = re.sub(rb"t:'[A-Za-z0-9+/=]+'", b"t:'TIME'", canonical)
            canonical = re.sub(rb'\?ray=[0-9a-f]+', b'?ray=RAY', canonical)
            expected = '69dd8893936a4d122ab9539efcddaa035fe04cda961ccc480c7a2a75b6d07d64'
            if digest(canonical) != expected:
                raise ValueError(f'{name}: unexpected hosting script')
            source = received[:match.start()] + received[match.end():]
            injection = dict(kind='Cloudflare JS challenge', raw_sha256=digest(raw),
                             template_sha256=expected, bytes=len(raw))
    local = path.read_bytes()
    if source != local:
        raise ValueError(f'{name}: deployed bytes differ from checkout')
    return dict(path=name, bytes=len(local), sha256=digest(local),
                response_sha256=digest(received), http_status=response.status_code,
                hosting_injection=injection, matched=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='https://pathology-edge-lab.ykh13571.chatgpt.site')
    parser.add_argument('--dist', type=Path, default=Path('dist'))
    parser.add_argument('--output', type=Path, default=Path('work/deployment-parity.json'))
    args = parser.parse_args()
    subprocess.run(['git', 'diff', '--exit-code', 'HEAD', '--', str(args.dist)], check=True, stdout=subprocess.DEVNULL)
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    paths = sorted(path for path in args.dist.rglob('*') if path.is_file())
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(lambda path: compare(path, args.dist, args.base_url), paths))
    result = dict(verified_utc=datetime.now(timezone.utc).isoformat(), base_url=args.base_url,
                  github_ui_commit=commit, matched_files=len(rows), files=rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(f'{len(rows)} deployed files match {commit}')


if __name__ == '__main__':
    main()
