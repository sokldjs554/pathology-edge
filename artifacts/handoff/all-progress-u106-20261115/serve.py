from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit
import mimetypes
import zipfile

ROOT=Path(__file__).resolve().parents[2]
ARCHIVE=ROOT/'artifacts/handoff/PathologyEdge-All-Progress-U106-20261115.zip'
Z=zipfile.ZipFile(ARCHIVE)
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        p=unquote(urlsplit(self.path).path).lstrip('/') or 'START_HERE.html'
        if p not in Z.namelist(): self.send_error(404);return
        b=Z.read(p)
        self.send_response(200)
        self.send_header('Content-Type',mimetypes.guess_type(p)[0] or 'application/octet-stream')
        self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
    def log_message(self,*args): pass
ThreadingHTTPServer(('127.0.0.1',8145),Handler).serve_forever()
