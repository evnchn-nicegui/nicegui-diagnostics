from __future__ import annotations


def test_ws_rtt_collect():
    from nicegui_diagnostics.probes.ws_rtt import collect
    result = collect()
    assert "ws_rtt_ms" in result
    assert isinstance(result["ws_rtt_ms"], (int, float))


def test_ws_rtt_uninstall():
    from nicegui_diagnostics.probes.ws_rtt import collect, uninstall
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
    from nicegui_diagnostics.probes.heartbeat import collect, install, uninstall
    install()
    uninstall()
    result = collect()
    assert result["heartbeat"]["alive_clients"] == 0


def test_heartbeat_purge():
    import time

    from nicegui_diagnostics.probes.heartbeat import _last_alive, install, purge_stale, uninstall
    install(ttl_s=0.001)  # very short TTL
    _last_alive["test-client"] = time.monotonic() - 1.0  # 1 second ago
    purged = purge_stale()
    assert purged == 1
    assert "test-client" not in _last_alive
    uninstall()


def test_heartbeat_gate_flag_blocks_callbacks_after_uninstall():
    """After uninstall(), heartbeat callbacks should be no-ops."""
    from nicegui_diagnostics.probes import heartbeat
    heartbeat._installed = False
    heartbeat._last_alive.clear()

    # Call the callbacks directly — they should not add entries
    heartbeat._on_connect()
    heartbeat._on_disconnect()

    assert len(heartbeat._last_alive) == 0
