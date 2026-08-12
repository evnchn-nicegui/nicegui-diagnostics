from __future__ import annotations

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


def test_disabled_by_default():
    result = collect()
    assert result["restart"]["enabled"] is False
    assert result["restart"]["threshold_mb"] is None


def test_install_with_threshold():
    install(threshold_mb=1000.0)
    result = collect()
    assert result["restart"]["enabled"] is True
    assert result["restart"]["threshold_mb"] == 1000.0


def test_check_below_threshold():
    install(threshold_mb=99999.0)  # very high threshold
    triggered = check_and_restart()
    assert triggered is False


def test_check_triggers_exit():
    install(threshold_mb=0.001)  # very low threshold — will exceed
    hooks_called = []
    install(threshold_mb=0.001, on_before_restart=[lambda: hooks_called.append(1)])
    with pytest.raises(SystemExit) as exc_info:
        check_and_restart()
    assert exc_info.value.code == 75
    assert hooks_called == [1]


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


def test_uninstall_disables():
    install(threshold_mb=1000.0)
    uninstall()
    result = collect()
    assert result["restart"]["enabled"] is False
    triggered = check_and_restart()
    assert triggered is False


def test_get_current_rss():
    rss = get_current_rss_mb()
    assert rss > 0  # we're using some memory
