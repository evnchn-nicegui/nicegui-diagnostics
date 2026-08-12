"""Clients probe — collects NiceGUI client counts."""
from __future__ import annotations

from typing import Any

_client_id: str | None = None
_verbose: bool = False


def configure(*, client_id: str | None = None, verbose: bool = False) -> None:
    """Set per-client detail options for the next ``collect()`` call."""
    global _client_id, _verbose
    _client_id = client_id
    _verbose = verbose


def install() -> None:
    """No-op — clients probe requires no setup."""


def uninstall() -> None:
    """No-op — clients probe has no state to clean up."""


def collect() -> dict[str, Any]:
    """Collect NiceGUI client totals and connected count."""
    from nicegui import Client  # noqa: PLC0415 — lazy import

    result: dict[str, Any] = {
        'clients': {
            'total': len(Client.instances),
            'connected': sum(1 for c in Client.instances.values() if c.has_socket_connection),
        },
    }
    if _verbose:
        result['clients']['by_id'] = {
            cid: {'has_socket': c.has_socket_connection, 'elements': len(c.elements)}
            for cid, c in Client.instances.items()
        }
    if _client_id and _client_id in Client.instances:
        c = Client.instances[_client_id]
        result['client_detail'] = {
            'id': _client_id,
            'has_socket': c.has_socket_connection,
            'elements': len(c.elements),
        }
    return result
