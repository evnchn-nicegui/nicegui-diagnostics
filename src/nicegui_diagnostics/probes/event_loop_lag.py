"""Event-loop lag probe — measures how long the event loop takes to schedule a callback."""
from __future__ import annotations

import asyncio
from typing import Any

_last_lag_ms: float = 0.0


def install() -> None:
    """No-op — lag probe requires no setup."""


def uninstall() -> None:
    """No-op — lag probe has no state to clean up."""


def collect() -> dict[str, Any]:
    """Return cached event-loop lag measurement.

    The synchronous ``collect()`` returns the most recent value measured
    by the async ``measure()`` call.  On first call (before any async
    measurement) this returns 0.0.
    """
    return {
        'event_loop_lag_ms': _last_lag_ms,
    }


async def measure() -> float:
    """Perform a fresh event-loop lag measurement and update the cache.

    Schedules a no-op callback via ``call_soon`` and measures how long
    the event loop takes to execute it.  On an idle loop this is <1 ms;
    under saturation it grows proportionally to queue depth.

    Returns the measured lag in milliseconds.
    """
    global _last_lag_ms  # noqa: PLW0603

    loop = asyncio.get_running_loop()
    future: asyncio.Future[float] = loop.create_future()
    t0 = loop.time()

    def _resolve() -> None:
        future.set_result((loop.time() - t0) * 1000.0)

    loop.call_soon(_resolve)
    _last_lag_ms = await future
    return _last_lag_ms
