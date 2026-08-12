"""Delta mode — current-vs-previous snapshot diffs (gap 4)."""
from __future__ import annotations

import time
from typing import Any

_previous_snapshot: dict[str, Any] | None = None
_previous_query_time: float | None = None


def install() -> None:
    pass

def uninstall() -> None:
    reset()

def reset() -> None:
    global _previous_snapshot, _previous_query_time
    _previous_snapshot = None
    _previous_query_time = None

def collect() -> dict[str, Any]:
    return {"delta_available": _previous_snapshot is not None}

def compute_delta(current: dict[str, Any]) -> dict[str, Any]:
    global _previous_snapshot, _previous_query_time
    now = time.monotonic()
    result: dict[str, Any] = {"current": current}
    if _previous_snapshot is not None and _previous_query_time is not None:
        result["delta"] = _diff_snapshots(_previous_snapshot, current)
        result["since_last_query_s"] = round(now - _previous_query_time, 2)
    _previous_snapshot = current
    _previous_query_time = now
    return result

def _diff_snapshots(prev: dict[str, Any], curr: dict[str, Any]) -> dict[str, str]:
    delta: dict[str, str] = {}
    for key in set(list(prev.keys()) + list(curr.keys())):
        pv = prev.get(key)
        cv = curr.get(key)
        if isinstance(pv, (int, float)) and isinstance(cv, (int, float)):
            diff = cv - pv
            if isinstance(diff, float):
                delta[key] = f"{diff:+.1f}"
            else:
                delta[key] = f"{diff:+d}" if diff != 0 else "0"
        elif isinstance(pv, dict) and isinstance(cv, dict):
            for nk, nv in _diff_snapshots(pv, cv).items():
                delta[f"{key}.{nk}"] = nv
    return delta
