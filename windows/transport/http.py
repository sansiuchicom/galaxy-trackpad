"""Local HTTP server that serves the tablet HTML assets."""
from __future__ import annotations

import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from windows.paths import HTTP_PORT, STATIC_DIR


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def start_http_server(directory=None) -> ThreadingHTTPServer:
    root = str(directory or STATIC_DIR)
    httpd = ThreadingHTTPServer(
        ("127.0.0.1", HTTP_PORT),
        partial(QuietHandler, directory=root),
    )
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd
