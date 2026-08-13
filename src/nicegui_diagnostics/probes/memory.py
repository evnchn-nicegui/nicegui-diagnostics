"""Memory probe — collects peak and current RSS metrics."""
from __future__ import annotations

import contextlib
import sys
from typing import Any

# resource module is POSIX-only; gracefully degrade on other platforms
try:
    import resource
except ImportError:
    resource = None  # type: ignore[assignment]


def install() -> None:
    """No-op — memory probe requires no setup."""


def uninstall() -> None:
    """No-op — memory probe has no state to clean up."""


def collect() -> dict[str, Any]:
    """Collect memory usage metrics with source labels.

    Peak RSS via ``resource.getrusage`` (POSIX).
    Current RSS via ``/proc/self/status`` VmRSS (Linux only).
    """
    if resource is not None:
        peak_rss_raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        # On Linux ru_maxrss is in KB; on macOS it is in bytes
        peak_rss_bytes: int | None = peak_rss_raw * 1024 if sys.platform == 'linux' else peak_rss_raw
        peak_rss_source = 'resource.getrusage(RUSAGE_SELF).ru_maxrss'
    else:
        peak_rss_bytes = None
        peak_rss_source = 'resource module not available (non-POSIX platform)'

    current_rss_bytes: int | None = None
    current_rss_source = '/proc/self/status not available (non-Linux platform)'
    with contextlib.suppress(OSError), open('/proc/self/status', encoding='utf-8') as f:
        for line in f:
            if line.startswith('VmRSS:'):
                current_rss_bytes = int(line.split()[1]) * 1024
                current_rss_source = '/proc/self/status VmRSS'
                break

    return {
        'memory': {
            'peak_rss_bytes': peak_rss_bytes,
            'peak_rss_source': peak_rss_source,
            'current_rss_bytes': current_rss_bytes,
            'current_rss_source': current_rss_source,
        },
    }
