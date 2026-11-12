"""Range-download the locked official BCData test entries; no full ZIP transfer.

Use only for non-commercial research after reviewing the official terms.
Original inputs must remain in an ignored, private work directory.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib

EVIDENCE = Path(__file__).resolve().parent


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--reuse-dir", type=Path)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    if args.manifest.exists():
        raise FileExistsError(args.manifest)
    protocol = json.loads((EVIDENCE / "protocol.json").read_text())
    manifest_bytes = (EVIDENCE / "archive-test-manifest.json").read_bytes()
    assert digest(manifest_bytes) == protocol["archive_test_manifest_sha256"]
    entries = json.loads(manifest_bytes)
    assert len(entries) == 1206
    assert sum(e["uncompressed_bytes"] for e in entries) <= protocol["download_budget"]["raw_limit_bytes"]
    page_url = "https://drive.usercontent.google.com/download?id=16W04QOR1E-G3ifc4061Be4eGpjRYDlkA&export=download"
    with urllib.request.urlopen(page_url, timeout=35) as response:
        html = response.read(200_000).decode()
    fields = dict(re.findall(r'<input[^>]+name="([^"]+)"[^>]+value="([^"]*)"', html))
    action = re.search(r'<form[^>]+action="([^"]+)"', html).group(1)
    assert action == "https://drive.usercontent.google.com/download"
    url = action + "?" + urllib.parse.urlencode(fields)

    def validate(data, entry):
        assert len(data) == entry["uncompressed_bytes"]
        assert zlib.crc32(data) == entry["crc32"]

    def fetch(entry):
        name = entry["name"]
        assert name.startswith("BCData/") and ".." not in Path(name).parts
        dest = args.data_dir / name
        source = args.reuse_dir / name if args.reuse_dir else None
        status, transferred = "existing-validated", 0
        if dest.exists():
            data = dest.read_bytes()
        elif source and source.exists():
            data = source.read_bytes()
            validate(data, entry)
            dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open("xb") as stream:
                stream.write(data)
            status = "prior-probe-input-reused"
        else:
            low = entry["offset"]
            high = low + entry["compressed_bytes"] + 1024
            request = urllib.request.Request(url, headers={"Range": f"bytes={low}-{high}"})
            for attempt in range(4):
                try:
                    with urllib.request.urlopen(request, timeout=45) as response:
                        assert response.status == 206, "Refuse a full ZIP response"
                        assert response.headers["Content-Range"] == f"bytes {low}-{high}/{protocol['archive_bytes']}"
                        raw = response.read(high - low + 2)
                    break
                except (TimeoutError, urllib.error.URLError):
                    if attempt == 3:
                        raise
                    time.sleep(2 ** attempt)
            assert len(raw) == high - low + 1
            header = struct.unpack_from("<4s5H3L2H", raw)
            assert header[0] == b"PK\x03\x04" and header[3] == entry["method"] == 8
            nlen, elen = header[-2:]
            assert raw[30:30+nlen].decode() == name
            start = 30 + nlen + elen
            assert start + entry["compressed_bytes"] <= len(raw)
            data = zlib.decompress(raw[start:start+entry["compressed_bytes"]], -15)
            validate(data, entry)
            dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open("xb") as stream:
                stream.write(data)
            status, transferred = "http206-range", len(raw)
        validate(data, entry)
        return dict(entry, sha256=digest(data), acquisition=status, range_bytes=transferred)

    start = time.perf_counter()
    records = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        for result in pool.map(fetch, entries):
            records.append(result)
            if len(records) % 100 == 0:
                print(json.dumps({"verified_files": len(records), "range_bytes": sum(x["range_bytes"] for x in records)}), flush=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    with args.manifest.open("x") as stream:
        json.dump(records, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"files": len(records), "range_bytes": sum(x["range_bytes"] for x in records),
                      "raw_bytes": sum(x["uncompressed_bytes"] for x in records),
                      "manifest_sha256": digest(args.manifest.read_bytes()),
                      "completed_utc": datetime.now(timezone.utc).isoformat(),
                      "wall_seconds": time.perf_counter()-start}), flush=True)


if __name__ == "__main__":
    main()
