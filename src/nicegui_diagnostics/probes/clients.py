"""Clients probe — collects NiceGUI client counts."""
from __future__ import annotations

from typing import Any

_client_id: str | None = None
_verbose: bool = False
_authenticated: bool = False


def configure(
    *,
    client_id: str | None = None,
    verbose: bool = False,
    authenticated: bool | None = None,
) -> None:
    """Set per-client detail options for the next ``collect()`` call.

    *authenticated* is only updated when explicitly passed (not ``None``) so
    that callers like ``collect_snapshot()`` that forward only *client_id* and
    *verbose* do not accidentally clear the auth flag.
    """
    global _client_id, _verbose, _authenticated
    _client_id = client_id
    _verbose = verbose
    if authenticated is not None:
        _authenticated = authenticated


def install() -> None:
    """No-op — clients probe requires no setup."""


def uninstall() -> None:
    """No-op — clients probe has no state to clean up."""
    global _authenticated
    _authenticated = False


def collect() -> dict[str, Any]:
    """Collect NiceGUI client totals and connected count.

    ``by_id`` is only included when both *_verbose* and *_authenticated* are
    True.  This is a defence-in-depth check — the canonical gate is
    ``auth.sanitize_snapshot()``, but we avoid emitting per-client data at all
    when the caller has not been authenticated.
    """
    from nicegui import Client

    result: dict[str, Any] = {
        'clients': {
            'total': len(Client.instances),
            'connected': sum(1 for c in Client.instances.values() if c.has_socket_connection),
        },
    }
    if _verbose and _authenticated:
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
