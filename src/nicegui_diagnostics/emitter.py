"""Structlog interval emitter for diagnostics.

Emits structured log events at a configurable interval. The external
watchdog use case (e.g. PG's lag-watchdog.sh) needs structured logs on
a known interval even when the HTTP endpoint can't be reached.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from . import collect_snapshot

_task: asyncio.Task | None = None
_interval_s: float = 0
_logger: Any = None


def _get_logger() -> Any:
    """Get a structlog logger, falling back to stdlib logging."""
    global _logger
    if _logger is not None:
        return _logger
    try:
        import structlog
        _logger = structlog.get_logger("nicegui_diagnostics")
    except ImportError:
        _logger = logging.getLogger("nicegui_diagnostics")
    return _logger


async def _emit_loop() -> None:
    """Background loop that emits diagnostic snapshots at intervals."""
    while True:
        try:
            snapshot = collect_snapshot()
            logger = _get_logger()
            # Flatten snapshot for structlog (it handles nested dicts)
            if hasattr(logger, "info"):
                # structlog-style
                try:
                    logger.info("memory_diagnostic", **snapshot)
                except TypeError:
                    # stdlib logging doesn't support **kwargs the same way
                    logger.info(f"memory_diagnostic: {snapshot}")
        except Exception:
            logger = _get_logger()
            if hasattr(logger, "exception"):
                logger.exception("diagnostic_snapshot_failed")
        await asyncio.sleep(_interval_s)


def install(*, interval_s: float = 30.0, **kwargs: Any) -> None:
    """Start the emission loop. Called by main install().

    Args:
        interval_s: Seconds between emissions. 0 disables.
    """
    global _task, _interval_s
    if interval_s <= 0:
        return
    _interval_s = interval_s
    try:
        loop = asyncio.get_running_loop()
        _task = loop.create_task(_emit_loop(), name="nicegui-diagnostics-emitter")
    except RuntimeError:
        pass  # no running loop — will start on first collect


def uninstall() -> None:
    """Stop the emission loop."""
    global _task, _interval_s
    if _task is not None:
        _task.cancel()
        _task = None
    _interval_s = 0


def collect() -> dict[str, Any]:
    """Return emitter status."""
    return {
        "emitter_enabled": _task is not None,
        "emitter_interval_s": _interval_s,
    }
