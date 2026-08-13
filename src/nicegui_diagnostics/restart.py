"""Memory-threshold graceful restart module.

When RSS exceeds memory_restart_threshold_mb, triggers ordered shutdown:
1. Call on_before_restart hooks (consumer-registered flushers)
2. SystemExit(75) — systemd Restart=on-failure picks it up
"""
from __future__ import annotations

import os
import platform
import resource
from collections.abc import Callable

_threshold_mb: float | None = None
_hooks: list[Callable] = []
_check_interval_s: float = 10.0
_installed: bool = False


def install(
    *,
    threshold_mb: float | None = None,
    on_before_restart: list[Callable] | None = None,
    check_interval_s: float = 10.0,
) -> None:
    """Configure memory-threshold restart.

    Args:
        threshold_mb: RSS threshold in MB. None disables.
        on_before_restart: Hooks called before SystemExit(75).
        check_interval_s: How often to check memory (future: background task).
    """
    global _threshold_mb, _hooks, _check_interval_s, _installed
    _threshold_mb = threshold_mb
    _hooks = list(on_before_restart or [])
    _check_interval_s = check_interval_s
    _installed = threshold_mb is not None


def uninstall() -> None:
    global _threshold_mb, _hooks, _installed
    _threshold_mb = None
    _hooks = []
    _installed = False


def get_current_rss_mb() -> float:
    """Get current RSS in MB.

    Linux: reads /proc/self/statm (resident pages) — true current RSS.
    macOS: uses ru_maxrss which reports current (not peak) RSS on Darwin.
    """
    if platform.system() == "Linux":
        try:
            with open("/proc/self/statm") as f:
                fields = f.read().split()
            # Field 1 (0-indexed) = resident pages
            resident_pages = int(fields[1])
            rss_bytes = resident_pages * os.sysconf("SC_PAGE_SIZE")
            return rss_bytes / (1024 * 1024)
        except (OSError, ValueError, IndexError):
            pass  # fall through to ru_maxrss

    # macOS (and Linux fallback): ru_maxrss
    usage = resource.getrusage(resource.RUSAGE_SELF)
    rss_raw = usage.ru_maxrss
    if platform.system() == "Linux":
        # Linux: ru_maxrss is in KB (but this is peak, only used as fallback)
        rss_bytes = rss_raw * 1024
    else:
        # macOS: ru_maxrss is in bytes and reports current RSS
        rss_bytes = rss_raw
    return rss_bytes / (1024 * 1024)


def check_and_restart() -> bool:
    """Check if RSS exceeds threshold. If so, run hooks and exit.

    Returns True if restart was triggered, False otherwise.
    """
    if _threshold_mb is None:
        return False

    current_mb = get_current_rss_mb()
    if current_mb <= _threshold_mb:
        return False

    # Threshold exceeded — run hooks and exit
    for hook in _hooks:
        try:
            hook()
        except Exception:
            pass  # best-effort

    raise SystemExit(75)


def collect() -> dict:
    return {
        "restart": {
            "enabled": _installed,
            "threshold_mb": _threshold_mb,
            "current_rss_mb": round(get_current_rss_mb(), 1) if _installed else None,
            "hooks_registered": len(_hooks),
        }
    }
