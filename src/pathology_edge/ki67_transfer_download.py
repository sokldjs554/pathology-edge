"""One bounded range per public ZIP member, with respectful rate-limit backoff."""
from datetime import datetime,timezone
from email.utils import parsedate_to_datetime
import hashlib
import struct
import time
import threading
import urllib.error
import zlib
from .ki67_deepliif import read_range

_last_request_start=-float('inf')
_request_lock=threading.Lock()


def fetch_entry_once(url,entry,total):
    low=entry['offset'];compressed=entry['compressed_bytes'];size=entry['uncompressed_bytes']
    if entry['method']!=8 or not 0<size<=8_000_000 or not 0<compressed<=7_800_000:raise ValueError('Unsupported bounded ZIP entry')
    # ZIP extra field length is uint16; include its maximum in the single read.
    high=min(total-1,low+30+len(entry['name'].encode('utf-8'))+65535+compressed-1)
    raw=read_range(url,low,high,total)
    if len(raw)<30:raise ValueError('Truncated local header')
    fields=struct.unpack('<4s5H3L2H',raw[:30]);nlen,elen=fields[-2:];start=30+nlen+elen
    if fields[0]!=b'PK\x03\x04' or fields[2]&1 or fields[3]!=8 or raw[30:30+nlen].decode('utf-8')!=entry['name']:raise ValueError('ZIP header/name differs')
    payload=raw[start:start+compressed]
    if len(payload)!=compressed:raise ValueError('Truncated ZIP payload')
    d=zlib.decompressobj(-15);data=d.decompress(payload,size+1)
    if not d.eof or d.unused_data or d.unconsumed_tail or len(data)!=size or zlib.crc32(data)!=entry['crc32']:raise ValueError('ZIP size/CRC differs')
    return data,{**entry,'sha256':hashlib.sha256(data).hexdigest(),'range_bytes':len(raw)}


def wait_seconds(seconds):
    while seconds>0:
        chunk=min(30,seconds);time.sleep(chunk);seconds-=chunk


def download(url,entry,total):
    global _last_request_start
    for attempt in range(8):
        try:
            with _request_lock:
                wait_seconds(max(0,2-(time.monotonic()-_last_request_start)))
                _last_request_start=time.monotonic()
            return fetch_entry_once(url,entry,total)
        except urllib.error.HTTPError as exc:
            if exc.code not in (429,500,502,503,504) or attempt==7:raise
            header=exc.headers.get('Retry-After','') if exc.headers else ''
            try:seconds=float(header)
            except ValueError:
                try:seconds=(parsedate_to_datetime(header)-datetime.now(timezone.utc)).total_seconds()
                except (TypeError,ValueError):seconds=60*min(attempt+1,5)
            seconds=max(1,seconds)
            print(f'PUBLIC_DATA_BACKOFF status={exc.code} seconds={seconds}',flush=True);wait_seconds(seconds)
        except (TimeoutError,urllib.error.URLError):
            if attempt==7:raise
            wait_seconds(10*min(attempt+1,5))
