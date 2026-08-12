"""Client-count heartbeat with TTL purge.

Registers on_connect/on_disconnect to maintain a last_alive dict.
Catches tab-killed / network-cut clients that on_disconnect misses.

KEY INVARIANT: The heartbeat must be reported from each page's own
context (ui.context.client.id), not from a background task.
"""
from __future__ import annotations

import time

_last_alive: dict[str, float] = {}
_ttl_s: float = 60.0
_installed: bool = False


def _on_connect() -> None:
    try:
        from nicegui import ui
        client_id = ui.context.client.id
        _last_alive[client_id] = time.monotonic()
    except Exception:
        pass


def _on_disconnect() -> None:
    try:
        from nicegui import ui
        client_id = ui.context.client.id
        _last_alive.pop(client_id, None)
    except Exception:
        pass


def install(*, ttl_s: float = 60.0) -> None:
    global _installed, _ttl_s
    if _installed:
        return
    _ttl_s = ttl_s
    try:
        from nicegui import app
        app.on_connect(_on_connect)
        app.on_disconnect(_on_disconnect)
        _installed = True
    except Exception:
        pass


def uninstall() -> None:
    global _installed, _last_alive
    _installed = False
    _last_alive.clear()


def purge_stale() -> int:
    """Remove entries older than TTL. Returns count purged."""
    now = time.monotonic()
    stale = [k for k, v in _last_alive.items() if now - v > _ttl_s]
    for k in stale:
        del _last_alive[k]
    return len(stale)


def collect() -> dict:
    return {
        "heartbeat": {
            "alive_clients": len(_last_alive),
            "client_ids": list(_last_alive.keys()),
        }
    }
