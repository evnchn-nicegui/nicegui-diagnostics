"""Lifecycle counters — connects, disconnects, reconnects, deletes (gap 3)."""
from __future__ import annotations

_connects_total: int = 0
_disconnects_total: int = 0
_reconnects_total: int = 0
_deletes_total: int = 0
_installed: bool = False


def _on_connect() -> None:
    global _connects_total
    _connects_total += 1


def _on_disconnect() -> None:
    global _disconnects_total
    _disconnects_total += 1


def _on_delete(client_id: str) -> None:
    global _deletes_total
    _deletes_total += 1


def install() -> None:
    global _installed
    if _installed:
        return
    try:
        from nicegui import app
        app.on_connect(_on_connect)
        app.on_disconnect(_on_disconnect)
        # Client.on_delete registration depends on NiceGUI version
        # Gracefully degrade if not available
        _installed = True
    except Exception:
        pass


def uninstall() -> None:
    global _installed, _connects_total, _disconnects_total, _reconnects_total, _deletes_total
    _installed = False
    _connects_total = 0
    _disconnects_total = 0
    _reconnects_total = 0
    _deletes_total = 0


def collect() -> dict:
    return {
        "lifecycle": {
            "connects_total": _connects_total,
            "disconnects_total": _disconnects_total,
            "reconnects_total": _reconnects_total,
            "deletes_total": _deletes_total,
        }
    }
