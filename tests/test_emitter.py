from __future__ import annotations

import asyncio

from nicegui_diagnostics.emitter import collect, install, uninstall


def setup_function():
    uninstall()


def teardown_function():
    uninstall()


def test_install_disabled_by_default():
    install(interval_s=0)
    result = collect()
    assert result["emitter_enabled"] is False


def test_install_with_interval():
    """Emitter starts when interval > 0 and a loop is running."""
    async def _test():
        install(interval_s=1.0)
        result = collect()
        assert result["emitter_enabled"] is True
        assert result["emitter_interval_s"] == 1.0
        uninstall()
        result = collect()
        assert result["emitter_enabled"] is False
    asyncio.run(_test())


def test_uninstall_cancels_task():
    async def _test():
        install(interval_s=1.0)
        assert collect()["emitter_enabled"] is True
        uninstall()
        assert collect()["emitter_enabled"] is False
    asyncio.run(_test())


def test_collect_returns_status():
    result = collect()
    assert "emitter_enabled" in result
    assert "emitter_interval_s" in result
    assert result["emitter_enabled"] is False
    assert result["emitter_interval_s"] == 0
