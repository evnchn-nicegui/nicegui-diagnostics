"""HTTP endpoint for diagnostics — /_nicegui/diagnostics."""
from __future__ import annotations

from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from . import auth as auth_module
from . import collect_snapshot
from .probes.delta import compute_delta

_auth_fn = None
_route: Route | None = None


def _make_handler() -> Any:
    async def handler(request: Request) -> JSONResponse:
        verbose = request.query_params.get('verbose', '').lower() in ('true', '1', 'yes')
        client_id = request.query_params.get('client_id')
        delta_mode = request.query_params.get('delta', '').lower() in ('true', '1', 'yes')
        delta_key = request.query_params.get('delta_key')

        if not auth_module.check_auth(
            _auth_fn,
            request,
            verbose=verbose,
            client_id=client_id,
            delta=delta_mode,
        ):
            return JSONResponse({'error': 'unauthorized'}, status_code=401)

        # Determine whether this caller is authenticated.  The same logic as
        # the check_auth call above: coarse-only requests are always allowed,
        # anything else needs auth_fn to return True.
        needs_auth = verbose or client_id is not None or delta_mode
        authenticated = (not needs_auth) or (_auth_fn is not None and _auth_fn(request))

        # Defence-in-depth: tell the clients probe whether the caller is
        # authenticated so it can suppress by_id at the source.  The
        # authenticated flag uses a tri-state (None = don't touch) so that
        # collect_snapshot's own configure() call does not reset it.
        from .probes import clients as _clients_probe

        _clients_probe.configure(authenticated=authenticated)

        snapshot = collect_snapshot(client_id=client_id, verbose=verbose)

        snapshot = auth_module.sanitize_snapshot(
            snapshot,
            authenticated=authenticated,
            verbose=verbose,
            client_id=client_id,
        )

        if delta_mode:
            result = compute_delta(snapshot, delta_key=delta_key)
        else:
            result = snapshot

        return JSONResponse(result)

    return handler


def install(*, auth_fn: Any = None, **kwargs: Any) -> None:
    """Register the diagnostics route. Called by main install()."""
    global _auth_fn, _route
    _auth_fn = auth_fn
    _route = Route('/_nicegui/diagnostics', _make_handler(), methods=['GET'])


def uninstall() -> None:
    """Tear down the diagnostics route and auth state."""
    global _auth_fn, _route
    _auth_fn = None
    _route = None


def get_route() -> Route | None:
    """Return the route object for registration with the app."""
    return _route


def collect() -> dict[str, Any]:
    """Return endpoint status."""
    return {
        'endpoint_enabled': _route is not None,
        'endpoint_path': '/_nicegui/diagnostics',
    }
