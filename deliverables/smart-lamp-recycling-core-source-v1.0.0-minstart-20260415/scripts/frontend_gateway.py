from __future__ import annotations

import http.client
import json
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

BASE_DIR = Path(__file__).resolve().parents[1]
STATIC_DIR = BASE_DIR / "frontend" / "dist"
HOST = os.getenv("FRONT_HOST", "127.0.0.1")
PORT = int(os.getenv("FRONT_PORT", "5173"))

PROXY_RULES = [
    ("/api", "127.0.0.1", 8080, False),
    ("/pay-api", "127.0.0.1", 8081, True),
    ("/song-api", "127.0.0.1", 8081, True),
    ("/vision-api", "127.0.0.1", 8000, True),
]


class FrontendGatewayHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def log_message(self, fmt: str, *args):
        return

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def do_GET(self):
        if self._try_proxy("GET"):
            return
        self._serve_spa()

    def do_HEAD(self):
        if self._try_proxy("HEAD"):
            return
        self._serve_spa(head_only=True)

    def do_POST(self):
        if self._try_proxy("POST"):
            return
        self._send_json_error(404, "not found")

    def do_PUT(self):
        if self._try_proxy("PUT"):
            return
        self._send_json_error(404, "not found")

    def do_PATCH(self):
        if self._try_proxy("PATCH"):
            return
        self._send_json_error(404, "not found")

    def do_DELETE(self):
        if self._try_proxy("DELETE"):
            return
        self._send_json_error(404, "not found")

    def do_OPTIONS(self):
        if self._try_proxy("OPTIONS"):
            return
        self.send_response(204)
        self.end_headers()

    def _serve_spa(self, head_only: bool = False):
        parsed = urlsplit(self.path)
        path = parsed.path or "/"
        target = (STATIC_DIR / path.lstrip("/")).resolve()
        try:
            target.relative_to(STATIC_DIR.resolve())
        except ValueError:
            self._send_json_error(403, "forbidden")
            return

        if path == "/":
            self.path = "/index.html"
        elif not target.is_file():
            self.path = "/index.html"

        if head_only:
            super().do_HEAD()
        else:
            super().do_GET()

    def _try_proxy(self, method: str) -> bool:
        parsed = urlsplit(self.path)
        in_path = parsed.path or "/"
        for prefix, host, port, rewrite in PROXY_RULES:
            if not in_path.startswith(prefix):
                continue

            out_path = in_path
            if rewrite:
                out_path = in_path[len(prefix):] or "/"
            if parsed.query:
                out_path = f"{out_path}?{parsed.query}"

            length = int(self.headers.get("Content-Length", "0") or "0")
            body = self.rfile.read(length) if length > 0 else None

            conn = http.client.HTTPConnection(host, port, timeout=30)
            try:
                headers = {
                    k: v
                    for k, v in self.headers.items()
                    if k.lower() not in {"host", "content-length", "connection"}
                }
                headers["Host"] = f"{host}:{port}"
                conn.request(method, out_path, body=body, headers=headers)
                response = conn.getresponse()
                raw = response.read()
            except OSError as exc:
                self._send_json_error(502, f"upstream error: {exc}")
                return True
            finally:
                conn.close()

            self.send_response(response.status)
            for key, value in response.getheaders():
                lower = key.lower()
                if lower in {"transfer-encoding", "connection", "keep-alive"}:
                    continue
                self.send_header(key, value)
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            if method != "HEAD":
                self.wfile.write(raw)
            return True
        return False

    def _send_json_error(self, status: int, message: str):
        payload = json.dumps({"error": message}, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def main():
    if not STATIC_DIR.is_dir():
        raise SystemExit(f"frontend dist not found: {STATIC_DIR}")

    server = ThreadingHTTPServer((HOST, PORT), FrontendGatewayHandler)
    print(f"Frontend gateway running at http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
