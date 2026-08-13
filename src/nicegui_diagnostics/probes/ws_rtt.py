"""WebSocket round-trip latency probe.

Measures the time for a JavaScript round-trip through the WebSocket.
This captures network RTT + browser RAF + JSON serialization that
server-side event_loop_lag misses.
"""
from __future__ import annotations

import time

_last_rtt_ms: float = 0.0


async def measure() -> float:
    """Measure WS round-trip by running a trivial JS expression.

    Returns RTT in milliseconds, or -1 if no client connected.
    """
    global _last_rtt_ms
    try:
        from nicegui import ui
        t0 = time.monotonic()
        await ui.run_javascript("1+1", timeout=5.0)
        t1 = time.monotonic()
        _last_rtt_ms = (t1 - t0) * 1000.0
        return _last_rtt_ms
    except Exception:
        return -1.0


def install() -> None:
    pass


def uninstall() -> None:
    global _last_rtt_ms
    _last_rtt_ms = 0.0


def collect() -> dict:
    return {
        "ws_rtt_ms": _last_rtt_ms,
    }
