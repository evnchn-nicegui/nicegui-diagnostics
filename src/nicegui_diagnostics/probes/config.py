"""Config probe — collects NiceGUI server configuration relevant to diagnostics."""
from __future__ import annotations

from typing import Any


def install() -> None:
    """No-op — config probe requires no setup."""


def uninstall() -> None:
    """No-op — config probe has no state to clean up."""


def collect() -> dict[str, Any]:
    """Collect server configuration for event handling and debugging.

    Uses ``getattr`` with ``None`` default for every field because
    ``reconnect_timeout`` and ``binding_refresh_interval`` don't exist
    on NiceGUI 3.15.  Access ``core.sio.eio`` for transports and
    ``core.sio`` for async_handlers.
    """
    from nicegui import core

    eio = getattr(core.sio, 'eio', None)

    return {
        'config': {
            'async_handlers': getattr(core.sio, 'async_handlers', None),
            'transports': getattr(eio, 'transports', []) if eio is not None else [],
            'reconnect_timeout': getattr(core.app.config, 'reconnect_timeout', None),
            'binding_refresh_interval': getattr(core.app.config, 'binding_refresh_interval', None),
        },
    }
