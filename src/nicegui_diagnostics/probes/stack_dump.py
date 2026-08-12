"""Separate-thread HTTP stack dump server (gap 1).

Works when the event loop is blocked — the async diagnostics handler hangs
in exactly the case you most need diagnostics for.
"""
from __future__ import annotations

import http.server
import sys
import threading
import traceback

_server: http.server.HTTPServer | None = None
_thread: threading.Thread | None = None


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path != "/stacks":
            self.send_error(404)
            return
        frames = sys._current_frames()
        body = "\n\n".join(
            f"=== thread {tid} ===\n{''.join(traceback.format_stack(frame))}"
            for tid, frame in frames.items()
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args) -> None:
        pass


def install(*, port: int = 9999) -> None:
    global _server, _thread
    if _server is not None:
        return
    srv = http.server.HTTPServer(("127.0.0.1", port), _Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True, name="nicegui-diagnostics-stack-dump")
    t.start()
    _server = srv
    _thread = t


def uninstall() -> None:
    global _server, _thread
    if _server is not None:
        _server.shutdown()
        _server.server_close()
        if _thread is not None:
            _thread.join(timeout=2.0)
        _server = None
        _thread = None


def collect() -> dict:
    return {
        "stack_dump_enabled": _server is not None,
        "stack_dump_port": _server.server_address[1] if _server else None,
    }
