"""Lifecycle counters — connects, disconnects, reconnects, deletes."""
from __future__ import annotations

import time

_connects_total: int = 0
_disconnects_total: int = 0
_reconnects_total: int = 0
_deletes_total: int = 0
_installed: bool = False

# Track recently-disconnected client IDs for reconnect detection.
# Maps client_id -> monotonic timestamp of disconnect.
_recent_disconnects: dict[str, float] = {}
_RECONNECT_WINDOW_S: float = 30.0  # consider a reconnect if reconnect happens within 30s


def _on_connect() -> None:
    if not _installed:
        return
    global _connects_total, _reconnects_total
    _connects_total += 1

    # Heuristic: if this client ID was recently disconnected, count as reconnect.
    # NiceGUI doesn't always expose client IDs in on_connect, so we do best-effort.
    try:
        from nicegui import ui
        client_id = ui.context.client.id
        now = time.monotonic()
        if client_id in _recent_disconnects:
            disconnect_time = _recent_disconnects.pop(client_id)
            if now - disconnect_time <= _RECONNECT_WINDOW_S:
                _reconnects_total += 1
    except Exception:
        pass


def _on_disconnect() -> None:
    if not _installed:
        return
    global _disconnects_total
    _disconnects_total += 1

    # Record this client ID as recently disconnected for reconnect detection.
    try:
        from nicegui import ui
        client_id = ui.context.client.id
        _recent_disconnects[client_id] = time.monotonic()
    except Exception:
        pass

    # Prune old entries to prevent unbounded growth.
    _prune_recent_disconnects()


def _on_delete(client_id: str) -> None:
    if not _installed:
        return
    global _deletes_total
    _deletes_total += 1


def _prune_recent_disconnects() -> None:
    """Remove disconnect records older than the reconnect window."""
    now = time.monotonic()
    stale = [k for k, v in _recent_disconnects.items() if now - v > _RECONNECT_WINDOW_S * 2]
    for k in stale:
        del _recent_disconnects[k]


def install() -> None:
    global _installed
    if _installed:
        return
    try:
        from nicegui import app
        app.on_connect(_on_connect)
        app.on_disconnect(_on_disconnect)
        # Client.on_delete registration depends on NiceGUI version.
        # Gracefully degrade if not available.
        _installed = True
    except Exception:
        pass


def uninstall() -> None:
    global _installed, _connects_total, _disconnects_total, _reconnects_total, _deletes_total
    # Setting _installed = False makes the callbacks no-ops even though
    # NiceGUI still holds references to them (gate-flag pattern).
    _installed = False
    _connects_total = 0
    _disconnects_total = 0
    _reconnects_total = 0
    _deletes_total = 0
    _recent_disconnects.clear()


def collect() -> dict:
    return {
        'lifecycle': {
            'connects_total': _connects_total,
            'disconnects_total': _disconnects_total,
            'reconnects_total': _reconnects_total,
            'deletes_total': _deletes_total,
        },
    }
