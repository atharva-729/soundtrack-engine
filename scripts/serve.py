"""Local preview of the site with HTTP range support (so audio seeking works, like on GitHub Pages).
Usage: python scripts/serve.py [port]
"""
import http.server
import os
import re
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parents[1] / "site"


class RangeHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(SITE), **k)

    def send_head(self):
        rng = self.headers.get("Range")
        path = self.translate_path(self.path)
        if not rng or not os.path.isfile(path):
            return super().send_head()
        m = re.match(r"bytes=(\d*)-(\d*)", rng)
        size = os.path.getsize(path)
        start = int(m.group(1)) if m and m.group(1) else 0
        end = int(m.group(2)) if m and m.group(2) else size - 1
        end = min(end, size - 1)
        if start > end:
            self.send_error(416)
            return None
        f = open(path, "rb")
        f.seek(start)
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(end - start + 1))
        self.send_header("Accept-Ranges", "bytes")
        self.end_headers()
        self._remaining = end - start + 1
        return f

    def copyfile(self, source, outputfile):
        n = getattr(self, "_remaining", None)
        if n is None:
            return super().copyfile(source, outputfile)
        while n > 0:
            buf = source.read(min(64 * 1024, n))
            if not buf:
                break
            outputfile.write(buf)
            n -= len(buf)
        self._remaining = None

    def end_headers(self):
        if not self.headers.get("Range"):
            self.send_header("Accept-Ranges", "bytes")
        super().end_headers()

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    print(f"Serving {SITE} at http://localhost:{port}  (Ctrl+C to stop)", flush=True)
    http.server.ThreadingHTTPServer(("127.0.0.1", port), RangeHandler).serve_forever()
