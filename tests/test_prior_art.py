from __future__ import annotations


def test_ws_rtt_collect():
    from nicegui_diagnostics.probes.ws_rtt import collect
    result = collect()
    assert "ws_rtt_ms" in result
    assert isinstance(result["ws_rtt_ms"], (int, float))


def test_ws_rtt_uninstall():
    from nicegui_diagnostics.probes.ws_rtt import uninstall, collect
    uninstall()
    result = collect()
    assert result["ws_rtt_ms"] == 0.0


def test_heartbeat_collect():
    from nicegui_diagnostics.probes.heartbeat import collect
    result = collect()
    assert "heartbeat" in result
    assert "alive_clients" in result["heartbeat"]
    assert result["heartbeat"]["alive_clients"] >= 0


def test_heartbeat_install_uninstall():
    from nicegui_diagnostics.probes.heartbeat import install, uninstall, collect
    install()
    uninstall()
    result = collect()
    assert result["heartbeat"]["alive_clients"] == 0


def test_heartbeat_purge():
    from nicegui_diagnostics.probes.heartbeat import _last_alive, purge_stale, install, uninstall
    import time
    install(ttl_s=0.001)  # very short TTL
    _last_alive["test-client"] = time.monotonic() - 1.0  # 1 second ago
    purged = purge_stale()
    assert purged == 1
    assert "test-client" not in _last_alive
    uninstall()
