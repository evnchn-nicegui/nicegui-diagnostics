"""Auth gating for the diagnostics endpoint."""
from __future__ import annotations

from typing import Any, Callable

# Default policy: coarse counts allowed without auth, verbose/client/delta require auth
# This matches the 02-api-surface.md spec:
# "non-verbose, no client_id, no delta → returns coarse counts"
# "ANY of verbose=, client_id=, delta= → 401"

AuthFn = Callable[[Any], bool]  # Callable[[Request], bool]


def check_auth(
    auth_fn: AuthFn | None,
    request: Any,
    *,
    verbose: bool = False,
    client_id: str | None = None,
    delta: bool = False,
) -> bool:
    """Return True if the request is authorized.

    Default behavior (auth_fn is None):
    - Coarse counts (no verbose, no client_id, no delta) → allowed
    - Any of verbose/client_id/delta → denied
    """
    needs_auth = verbose or client_id is not None or delta
    if not needs_auth:
        return True
    if auth_fn is None:
        return False
    return auth_fn(request)
