from __future__ import annotations

import gc
import platform

import pytest

from nicegui_diagnostics.restart import (
    check_and_restart,
    collect,
    get_current_rss_mb,
    install,
    uninstall,
)


def setup_function():
    uninstall()


def teardown_function():
    uninstall()


# --- install / uninstall / collect ---


def test_disabled_by_default():
    result = collect()
    assert result["restart"]["enabled"] is False
    assert result["restart"]["threshold_mb"] is None


def test_install_with_threshold():
    install(threshold_mb=1000.0)
    result = collect()
    assert result["restart"]["enabled"] is True
    assert result["restart"]["threshold_mb"] == 1000.0


def test_uninstall_disables():
    install(threshold_mb=1000.0)
    uninstall()
    result = collect()
    assert result["restart"]["enabled"] is False
    triggered = check_and_restart()
    assert triggered is False


# --- get_current_rss_mb ---


def test_get_current_rss_mb_sane_value():
    """RSS should be a positive float within a reasonable range (1 MB – 10 GB)."""
    rss = get_current_rss_mb()
    assert isinstance(rss, float)
    assert rss > 1.0, f"RSS too low: {rss} MB"
    assert rss < 10 * 1024, f"RSS suspiciously high: {rss} MB"


@pytest.mark.skipif(
    platform.system() != "Linux",
    reason="macOS ru_maxrss behaves differently; alloc-free pattern only reliable on Linux /proc",
)
def test_not_peak_rss_on_linux():
    """After allocating and freeing a large block, current RSS should drop — not stay at peak."""
    # Baseline
    gc.collect()
    rss_before = get_current_rss_mb()

    # Allocate ~100 MB
    big = bytearray(100 * 1024 * 1024)
    # Touch pages so they're actually mapped
    big[0] = 1
    big[-1] = 1
    rss_during = get_current_rss_mb()
    assert rss_during > rss_before, "RSS should increase after large allocation"

    # Free and force GC
    del big
    gc.collect()

    rss_after = get_current_rss_mb()
    # Current RSS should have dropped significantly from the peak during allocation.
    # Allow some slack — the allocator may not return all pages to the OS immediately.
    assert rss_after < rss_during, (
        f"Current RSS ({rss_after:.1f} MB) should be less than during-allocation RSS ({rss_during:.1f} MB). "
        "get_current_rss_mb() may be reporting peak instead of current."
    )


# --- check_and_restart ---


def test_check_triggers_exit_at_low_threshold():
    """A threshold below current RSS should trigger SystemExit(75)."""
    hooks_called = []
    install(threshold_mb=0.001, on_before_restart=[lambda: hooks_called.append(1)])
    with pytest.raises(SystemExit) as exc_info:
        check_and_restart()
    assert exc_info.value.code == 75
    assert hooks_called == [1]


def test_check_no_trigger_with_high_threshold():
    """A threshold of 100 GB should never trigger in a test process."""
    install(threshold_mb=100 * 1024)  # 100 GB
    triggered = check_and_restart()
    assert triggered is False


def test_hooks_called_in_order():
    order = []
    install(
        threshold_mb=0.001,
        on_before_restart=[
            lambda: order.append("first"),
            lambda: order.append("second"),
        ],
    )
    with pytest.raises(SystemExit):
        check_and_restart()
    assert order == ["first", "second"]
