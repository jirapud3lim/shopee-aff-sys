from __future__ import annotations

import html
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qsl, urlparse

from .flow import OAuthFlow


def make_handler(flow: OAuthFlow):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):  # never log request lines (contain code/state)
            pass

        def _send(self, status: int, body: str, ctype: str = "text/html; charset=utf-8", loc: str | None = None):
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            if loc:
                self.send_header("Location", loc)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body.encode())

        def do_GET(self):
            u = urlparse(self.path)
            if u.path == "/":
                self._send(302, "", loc=flow.start_url())
            elif u.path == flow.cfg.callback_path:
                status, data = flow.handle_callback(dict(parse_qsl(u.query)))
                text = json.dumps(data, indent=2, ensure_ascii=False)
                print(f"[callback] http={status}\n{text}", flush=True)
                self._send(status, f"<pre>{html.escape(text)}</pre>")
            else:
                self._send(404, "not found")

    return Handler


def serve(flow: OAuthFlow, host: str = "127.0.0.1", port: int = 8000) -> None:
    httpd = HTTPServer((host, port), make_handler(flow))
    print(f"listening on http://{host}:{port}/  (open / in a browser to start login)", flush=True)
    httpd.serve_forever()
