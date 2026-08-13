"""Auth gating for the diagnostics endpoint."""
from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

# Default policy: coarse counts allowed without auth, verbose/client/delta require auth
# This matches the 02-api-surface.md spec:
# "non-verbose, no client_id, no delta → returns coarse counts"
# "ANY of verbose=, client_id=, delta= → 401"

AuthFn = Callable[[Any], bool]  # Callable[[Request], bool]

# Pattern that matches NiceGUI client IDs embedded in asyncio task names.
# NiceGUI stamps client IDs (hex strings) onto task names, e.g.
# "nicegui-client-abc123-handler" or "Client.abc123.some_coro".
_CLIENT_ID_IN_TASK_RE = re.compile(
    r'(?:nicegui[-_]?client[-_]|client[-_])[\w-]+',
    re.IGNORECASE,
)


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


def _collect_known_client_ids(snapshot: dict[str, Any]) -> set[str]:
    """Extract all client IDs visible in a raw snapshot (pre-sanitization)."""
    ids: set[str] = set()
    # From heartbeat probe
    heartbeat = snapshot.get('heartbeat')
    if isinstance(heartbeat, dict):
        for cid in heartbeat.get('client_ids', []):
            if isinstance(cid, str):
                ids.add(cid)
    # From clients probe
    clients = snapshot.get('clients')
    if isinstance(clients, dict):
        by_id = clients.get('by_id')
        if isinstance(by_id, dict):
            ids.update(by_id.keys())
    # From client_detail
    detail = snapshot.get('client_detail')
    if isinstance(detail, dict):
        cid = detail.get('id')
        if isinstance(cid, str):
            ids.add(cid)
    return ids


def _redact_task_name(name: str, known_ids: set[str]) -> str:
    """Redact a task name if it contains a known client ID or matches client patterns."""
    # Direct match against known client IDs
    for cid in known_ids:
        if cid and cid in name:
            return '<redacted>'
    # Heuristic: if the name matches the client-in-task pattern, redact it
    if _CLIENT_ID_IN_TASK_RE.search(name):
        return '<redacted>'
    return name


def sanitize_snapshot(
    snapshot: dict[str, Any],
    *,
    authenticated: bool,
    verbose: bool = False,
    client_id: str | None = None,
) -> dict[str, Any]:
    """Remove client-identifying data from a snapshot when the caller is not authenticated.

    When *authenticated* is True the snapshot is returned as-is (shallow copy).
    When False the following fields are stripped or redacted:

    * ``heartbeat.client_ids`` — list of live client IDs
    * ``clients.by_id`` — per-client detail dict
    * ``client_detail`` — single-client detail block
    * ``asyncio_tasks.by_coroutine[*].names`` — task names containing client IDs
    """
    if authenticated:
        return dict(snapshot)

    # Collect known IDs *before* we mutate, so we can use them to redact task names
    known_ids = _collect_known_client_ids(snapshot)

    sanitized: dict[str, Any] = {}
    for key, value in snapshot.items():
        if key == 'heartbeat' and isinstance(value, dict):
            # Keep alive_clients count, drop client_ids list
            sanitized[key] = {k: v for k, v in value.items() if k != 'client_ids'}
        elif key == 'clients' and isinstance(value, dict):
            # Keep total/connected counts, drop by_id
            sanitized[key] = {k: v for k, v in value.items() if k != 'by_id'}
        elif key == 'client_detail':
            # Drop entirely — it exposes a specific client's detail
            continue
        elif key == 'asyncio_tasks' and isinstance(value, dict):
            sanitized[key] = _sanitize_asyncio_tasks(value, known_ids)
        else:
            sanitized[key] = value

    return sanitized


def _sanitize_asyncio_tasks(
    tasks_data: dict[str, Any],
    known_ids: set[str],
) -> dict[str, Any]:
    """Redact task names that may contain client identifiers."""
    by_coroutine = tasks_data.get('by_coroutine')
    if not isinstance(by_coroutine, dict):
        return dict(tasks_data)

    new_by_coroutine: dict[str, Any] = {}
    for group_key, group_data in by_coroutine.items():
        if not isinstance(group_data, dict):
            new_by_coroutine[group_key] = group_data
            continue
        new_group = dict(group_data)
        names = new_group.get('names')
        if isinstance(names, list):
            new_group['names'] = [_redact_task_name(n, known_ids) for n in names]
        new_by_coroutine[group_key] = new_group

    return {**tasks_data, 'by_coroutine': new_by_coroutine}
