"""Delta mode — current-vs-previous snapshot diffs (gap 4).

Per-caller baseline storage with bounded LRU + TTL eviction so concurrent
``?delta=true`` callers do not clobber each other's previous snapshot.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

_DEFAULT_KEY = '__default__'
_MAX_KEYS = 64
_TTL_SECONDS = 300  # 5 minutes of inactivity → evicted


@dataclass
class _Baseline:
    snapshot: dict[str, Any]
    query_time: float
    last_access: float = field(default_factory=time.monotonic)


# Per-caller baseline store: key → _Baseline
_baselines: dict[str, _Baseline] = {}


def install() -> None:
    pass


def uninstall() -> None:
    reset()


def reset() -> None:
    _baselines.clear()


def collect() -> dict[str, Any]:
    return {'delta_available': len(_baselines) > 0}


def _evict_expired(now: float) -> None:
    """Remove entries whose last_access is older than TTL."""
    expired = [k for k, b in _baselines.items() if now - b.last_access > _TTL_SECONDS]
    for k in expired:
        del _baselines[k]


def _evict_lru(needed: int = 1) -> None:
    """If adding *needed* new entries would exceed the cap, drop oldest-accessed."""
    while len(_baselines) + needed > _MAX_KEYS:
        if not _baselines:
            break
        oldest_key = min(_baselines, key=lambda k: _baselines[k].last_access)
        del _baselines[oldest_key]


def compute_delta(
    current: dict[str, Any],
    delta_key: str | None = None,
) -> dict[str, Any]:
    """Compute delta for a caller identified by *delta_key*.

    When *delta_key* is ``None``, falls back to ``__default__`` so that a
    single-caller workflow remains backward-compatible.
    """
    key = delta_key if delta_key is not None else _DEFAULT_KEY
    now = time.monotonic()

    # Evict stale / over-capacity entries before inserting
    _evict_expired(now)
    _evict_lru(needed=0 if key in _baselines else 1)

    baseline = _baselines.get(key)

    result: dict[str, Any] = {
        'current': current,
        'delta_key': key,
    }

    if baseline is not None:
        result['delta'] = _diff_snapshots(baseline.snapshot, current)
        result['since_last_query_s'] = round(now - baseline.query_time, 2)
        result['delta_since'] = baseline.query_time

    # Upsert baseline (refreshes last_access on hit too)
    _baselines[key] = _Baseline(snapshot=current, query_time=now, last_access=now)

    return result


def _diff_snapshots(prev: dict[str, Any], curr: dict[str, Any]) -> dict[str, str]:
    delta: dict[str, str] = {}
    for key in set(list(prev.keys()) + list(curr.keys())):
        pv = prev.get(key)
        cv = curr.get(key)
        if isinstance(pv, (int, float)) and isinstance(cv, (int, float)):
            diff = cv - pv
            if isinstance(diff, float):
                delta[key] = f'{diff:+.1f}'
            else:
                delta[key] = f'{diff:+d}' if diff != 0 else '0'
        elif isinstance(pv, dict) and isinstance(cv, dict):
            for nk, nv in _diff_snapshots(pv, cv).items():
                delta[f'{key}.{nk}'] = nv
    return delta
