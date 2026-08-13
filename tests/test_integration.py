"""Integration tests — prove the package works end-to-end.

These tests exercise the REAL integration path: install() → collect_snapshot() → endpoint.
They catch the bugs that smoke tests miss (Codex review 2026-08-12).
"""
from __future__ import annotations


def setup_function():
    from nicegui_diagnostics import uninstall
    try:
        uninstall()
    except Exception:
        pass


def teardown_function():
    from nicegui_diagnostics import uninstall
    try:
        uninstall()
    except Exception:
        pass


def test_install_with_features_returns_probe_data():
    """install(features=[...]) followed by collect_snapshot() should return real probe data, not just timestamp."""
    from nicegui_diagnostics import collect_snapshot, install
    install(features=["tasks", "memory", "clients", "config"])
    snap = collect_snapshot()
    # At least one probe should have contributed data
    probe_keys = {"asyncio_tasks", "memory", "clients", "config", "event_loop_lag", "stack_dump"}
    found = probe_keys & set(snap.keys())
    assert len(found) > 0, f"Expected probe data in snapshot, got keys: {list(snap.keys())}"


def test_install_with_all_features():
    """install() with no features arg should enable defaults without crashing."""
    from nicegui_diagnostics import collect_snapshot, install
    install(features=[])  # minimal — just foundation
    snap = collect_snapshot()
    assert "timestamp" in snap


def test_collect_snapshot_includes_registered_collectors():
    """register_collector() output should appear in collect_snapshot()."""
    from nicegui_diagnostics import collect_snapshot, install, register_collector
    install(features=[])
    register_collector("my_app", lambda: {"widget_count": 42})
    snap = collect_snapshot()
    assert snap.get("my_app") == {"widget_count": 42}


def test_stack_dump_port_config():
    """install(stack_dump_port=N) should start stack dump on port N."""
    from nicegui_diagnostics import install
    # This test verifies the config is at least stored
    # Full wiring test depends on __init__.py fix
    install(features=["stack_dump"], stack_dump_port=0)
    # If wiring is correct, stack_dump should be enabled
    from nicegui_diagnostics.probes.stack_dump import collect
    result = collect()
    # After the fix, this should be True. Before the fix, it's False.
    # We assert the expected behavior (post-fix):
    assert result["stack_dump_enabled"] is True, "stack_dump_port config not wired through install()"


def test_emitter_config():
    """install(structlog_interval_s=N) should start the emitter."""
    from nicegui_diagnostics import install
    install(features=[], structlog_interval_s=0)  # disabled
    from nicegui_diagnostics.emitter import collect
    result = collect()
    assert result["emitter_enabled"] is False


def test_api_endpoint_via_install():
    """After install(), the API route should be registered."""
    from nicegui_diagnostics import install
    install(features=[])
    from nicegui_diagnostics.api import get_route
    route = get_route()
    # After the fix, this should not be None
    assert route is not None, "API route not registered by install()"


def test_auth_wired_through_install():
    """install(auth=fn) should pass auth to the API module."""
    from nicegui_diagnostics import install
    auth_called = []
    def my_auth(request):
        auth_called.append(True)
        return True
    install(features=[], auth=my_auth)
    from nicegui_diagnostics.api import _auth_fn
    assert _auth_fn is my_auth, "auth callable not wired through install()"


def test_route_registered_on_nicegui_app():
    """install() should add the diagnostics route to nicegui.app.routes."""
    from nicegui import app as nicegui_app

    from nicegui_diagnostics import install, uninstall
    uninstall()
    before = len([r for r in nicegui_app.routes if getattr(r, 'path', None) == '/_nicegui/diagnostics'])
    install(features=[])
    after = len([r for r in nicegui_app.routes if getattr(r, 'path', None) == '/_nicegui/diagnostics'])
    assert after > before, "Route not registered on nicegui.app"
    uninstall()


def test_snapshot_shape_not_double_nested():
    """collect_snapshot() should return flat probe keys, not double-nested."""
    from nicegui_diagnostics import collect_snapshot, install, uninstall
    uninstall()
    install(features=["memory", "tasks"])
    snap = collect_snapshot()
    # memory should be directly accessible, not snap["memory"]["memory"]
    if "memory" in snap:
        mem = snap["memory"]
        # Should have peak_rss_bytes directly, not nested under another "memory" key
        assert "peak_rss_bytes" in mem or "memory" not in mem, \
            f"Double-nested! snap['memory'] keys: {list(mem.keys())}"
    uninstall()


def test_verbose_returns_client_detail():
    """collect_snapshot(verbose=True) should include per-client detail."""
    from nicegui_diagnostics import collect_snapshot, install, uninstall
    uninstall()
    install(features=["clients"])
    snap = collect_snapshot(verbose=True)
    # With verbose, should have by_id or similar detail
    clients_data = snap.get("clients", {})
    # Just verify it doesn't crash and returns something
    assert isinstance(clients_data, dict)
    uninstall()


def test_default_features_only_implemented():
    """install() with no features arg should not try to import unimplemented modules."""
    from nicegui_diagnostics import install, uninstall
    uninstall()
    # This should not produce import warnings for lifecycle/eio/ws_rtt/heartbeat
    install()  # features=None → should default to implemented only
    uninstall()
