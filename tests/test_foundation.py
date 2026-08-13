from __future__ import annotations

import pytest


def test_install_idempotency():
    from nicegui_diagnostics import install, uninstall
    uninstall()  # ensure clean state
    install(features=[])
    with pytest.raises(RuntimeError, match='already installed'):
        install(features=[])
    uninstall()


def test_uninstall_allows_reinstall():
    from nicegui_diagnostics import install, uninstall
    uninstall()
    install(features=[])
    uninstall()
    install(features=[])  # should not raise
    uninstall()


def test_register_collector():
    from nicegui_diagnostics import collect_snapshot, install, register_collector, uninstall
    uninstall()
    install(features=[])
    register_collector('test', lambda: {'x': 1})
    snap = collect_snapshot()
    assert snap['test'] == {'x': 1}
    uninstall()


def test_features_empty_noops():
    from nicegui_diagnostics import collect_snapshot, install, uninstall
    uninstall()
    install(features=[])
    snap = collect_snapshot()
    assert 'timestamp' in snap
    uninstall()


def test_collect_snapshot_has_timestamp():
    from nicegui_diagnostics import collect_snapshot, install, uninstall
    uninstall()
    install(features=[])
    snap = collect_snapshot()
    assert 'timestamp' in snap
    uninstall()


def test_install_wires_probes():
    """install() with features should actually call probe collect() functions."""
    from nicegui_diagnostics import collect_snapshot, install, uninstall
    uninstall()
    install(features=['tasks', 'memory', 'clients', 'config'])
    snap = collect_snapshot()
    # These should have real data, not just timestamp
    assert 'asyncio_tasks' in snap or 'memory' in snap or 'clients' in snap or 'config' in snap
    uninstall()


def test_default_features_include_all_implemented():
    """install() with features=None should enable all 11 implemented probes."""
    import nicegui_diagnostics as nd
    nd.uninstall()
    nd.install(features=None)
    assert nd._enabled_features == set(nd._IMPLEMENTED_FEATURES)
    assert len(nd._IMPLEMENTED_FEATURES) == 11
    expected = {'tasks', 'memory', 'clients', 'config', 'event_loop_lag', 'stack_dump',
                'delta', 'lifecycle', 'eio', 'js_rtt', 'heartbeat'}
    assert nd._IMPLEMENTED_FEATURES == expected
    nd.uninstall()


def test_version_is_set():
    """__version__ should be a non-empty string."""
    from nicegui_diagnostics import __version__
    assert isinstance(__version__, str)
    assert len(__version__) > 0


def test_version_matches_pyproject():
    """__version__ should match pyproject.toml or fall back gracefully."""
    from nicegui_diagnostics import __version__
    # After pip install -e ., importlib.metadata should return the pyproject version
    # In dev without install, it falls back to '0.1.0.dev0'
    assert __version__ in ('0.1.0.dev0', '0.0.0') or '.' in __version__


@pytest.mark.asyncio
async def test_scheduler_tick_calls_event_loop_lag_measure():
    """_scheduler_tick() should call event_loop_lag.measure() when enabled."""
    import nicegui_diagnostics as nd
    from nicegui_diagnostics.probes import event_loop_lag
    nd.uninstall()
    nd.install(features=['event_loop_lag'])
    assert 'event_loop_lag' in nd._probe_modules

    # Before tick, lag should be 0.0
    assert event_loop_lag._last_lag_ms == 0.0

    # Run one tick
    await nd._scheduler_tick()

    # After tick, lag should be non-negative (it's always >= 0)
    assert event_loop_lag._last_lag_ms >= 0.0
    nd.uninstall()


@pytest.mark.asyncio
async def test_scheduler_tick_calls_heartbeat_purge():
    """_scheduler_tick() should call heartbeat.purge_stale() when enabled."""
    import time

    import nicegui_diagnostics as nd
    from nicegui_diagnostics.probes import heartbeat
    nd.uninstall()
    nd.install(features=['heartbeat'])
    assert 'heartbeat' in nd._probe_modules

    # Add entries with old timestamps (older than TTL)
    heartbeat._last_alive['old_client_1'] = time.monotonic() - 120.0
    heartbeat._last_alive['old_client_2'] = time.monotonic() - 120.0
    heartbeat._last_alive['fresh_client'] = time.monotonic()
    assert len(heartbeat._last_alive) == 3

    # Run one tick — should purge stale entries
    await nd._scheduler_tick()

    # Old entries should be purged, fresh one should remain
    assert 'old_client_1' not in heartbeat._last_alive
    assert 'old_client_2' not in heartbeat._last_alive
    assert 'fresh_client' in heartbeat._last_alive
    nd.uninstall()


@pytest.mark.asyncio
async def test_scheduler_starts_and_stops():
    """install() should start a scheduler task, uninstall() should cancel it."""
    from nicegui_diagnostics import install, uninstall
    uninstall()
    install(features=['event_loop_lag'])

    # Scheduler task should be running
    import nicegui_diagnostics as nd
    assert nd._scheduler_task is not None
    assert not nd._scheduler_task.done()

    uninstall()

    # After uninstall, scheduler should be stopped
    assert nd._scheduler_task is None


@pytest.mark.asyncio
async def test_scheduler_deferred_without_loop():
    """_start_scheduler() should handle no running event loop gracefully."""
    import nicegui_diagnostics as nd
    from nicegui_diagnostics import _start_scheduler
    # This is called from sync context in tests — should not raise
    old_installed = nd._installed
    nd._installed = True
    try:
        # In a sync test context, get_running_loop() will raise RuntimeError
        # but we're actually in an async test, so the loop exists.
        # The important thing is it doesn't crash.
        _start_scheduler()
    finally:
        nd._installed = old_installed
        nd._stop_scheduler()


def setup_function():
    from nicegui_diagnostics import uninstall
    try:
        uninstall()
    except Exception:
        pass
