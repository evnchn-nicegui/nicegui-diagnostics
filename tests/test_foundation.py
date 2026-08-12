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
    from nicegui_diagnostics import install, uninstall, register_collector, collect_snapshot
    uninstall()
    install(features=[])
    register_collector('test', lambda: {'x': 1})
    snap = collect_snapshot()
    assert snap['test'] == {'x': 1}
    uninstall()


def test_features_empty_noops():
    from nicegui_diagnostics import install, uninstall, collect_snapshot
    uninstall()
    install(features=[])
    snap = collect_snapshot()
    assert 'timestamp' in snap
    uninstall()


def test_collect_snapshot_has_timestamp():
    from nicegui_diagnostics import install, uninstall, collect_snapshot
    uninstall()
    install(features=[])
    snap = collect_snapshot()
    assert 'timestamp' in snap
    uninstall()


def test_install_wires_probes():
    """install() with features should actually call probe collect() functions."""
    from nicegui_diagnostics import install, uninstall, collect_snapshot
    uninstall()
    install(features=['tasks', 'memory', 'clients', 'config'])
    snap = collect_snapshot()
    # These should have real data, not just timestamp
    assert 'asyncio_tasks' in snap or 'memory' in snap or 'clients' in snap or 'config' in snap
    uninstall()


def setup_function():
    from nicegui_diagnostics import uninstall
    try:
        uninstall()
    except Exception:
        pass
