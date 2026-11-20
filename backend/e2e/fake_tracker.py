"""Minimal HTTP BitTorrent tracker used by the end-to-end smoke test.

Logs every announce (one JSON object per line) and answers with a valid
bencoded response.  Torrents whose info_hash is listed in REJECT_HASHES get a
BEP 3 'failure reason' instead.

Usage: python fake_tracker.py <port> <log_file> [reject_info_hash_hex,...]
"""
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

PORT = int(sys.argv[1])
LOG = sys.argv[2]
REJECT = {bytes.fromhex(h) for h in (sys.argv[3].split(",") if len(sys.argv) > 3 and sys.argv[3] else [])}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = parse_qs(urlparse(self.path).query, encoding="latin-1")
        info_hash = query.get("info_hash", [""])[0].encode("latin-1")
        entry = {k: query.get(k, [""])[0] for k in ("event", "uploaded", "downloaded", "left", "port")}
        entry["info_hash"] = info_hash.hex()
        entry["user_agent"] = self.headers.get("User-Agent")
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

        if info_hash in REJECT:
            body = b"d14:failure reason20:Unregistered torrente"
        else:
            body = b"d8:completei3e10:incompletei2e8:intervali60e12:min intervali60e5:peers0:e"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
