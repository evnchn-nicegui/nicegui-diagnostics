"""Engine.io session probe (gap 5)."""
from __future__ import annotations


def install() -> None:
    pass


def uninstall() -> None:
    pass


def collect() -> dict:
    eio_sessions = None
    try:
        from nicegui import core
        if hasattr(core, 'sio') and hasattr(core.sio, 'eio'):
            eio = core.sio.eio
            if hasattr(eio, 'sockets'):
                eio_sessions = len(eio.sockets)
    except Exception:
        pass

    # Get NiceGUI client count for discrepancy calculation
    nicegui_clients = 0
    try:
        from nicegui import Client
        nicegui_clients = len(Client.instances)
    except Exception:
        pass

    orphan_estimate = None
    if eio_sessions is not None:
        orphan_estimate = max(0, eio_sessions - nicegui_clients)

    return {
        "engineio": {
            "eio_sessions": eio_sessions,
            "nicegui_clients": nicegui_clients,
            "orphan_sockets_estimate": orphan_estimate,
        }
    }
