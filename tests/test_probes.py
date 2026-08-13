from __future__ import annotations


def test_tasks_collect():
    from nicegui_diagnostics.probes.tasks import collect
    result = collect()
    assert "asyncio_tasks" in result
    assert "total" in result["asyncio_tasks"]
    assert result["asyncio_tasks"]["total"] >= 0


def test_memory_collect():
    from nicegui_diagnostics.probes.memory import collect
    result = collect()
    assert "memory" in result
    assert result["memory"]["peak_rss_bytes"] is not None  # macOS has resource module


def test_clients_collect():
    from nicegui_diagnostics.probes.clients import collect
    result = collect()
    assert "clients" in result
    assert result["clients"]["total"] >= 0


def test_config_collect():
    from nicegui_diagnostics.probes.config import collect
    result = collect()
    assert "config" in result


def test_lag_collect():
    from nicegui_diagnostics.probes.event_loop_lag import collect
    result = collect()
    assert "event_loop_lag_ms" in result
    assert isinstance(result["event_loop_lag_ms"], (int, float))


def test_tasks_install_uninstall():
    """Task probe install/uninstall should not crash."""
    from nicegui_diagnostics.probes.tasks import collect, install, uninstall
    install()
    result = collect()
    assert "asyncio_tasks" in result
    uninstall()


def test_clients_verbose():
    """Clients probe with verbose should return by_id detail."""
    from nicegui_diagnostics.probes.clients import collect, configure
    configure(verbose=True)
    result = collect()
    assert "clients" in result
    configure(verbose=False)  # reset


def test_stack_dump_clean_uninstall():
    """Stack dump uninstall should fully clean up."""
    from nicegui_diagnostics.probes.stack_dump import collect, install, uninstall
    install(port=0)
    assert collect()["stack_dump_enabled"] is True
    uninstall()
    assert collect()["stack_dump_enabled"] is False
    # Reinstall should work (port reuse)
    install(port=0)
    assert collect()["stack_dump_enabled"] is True
    uninstall()
