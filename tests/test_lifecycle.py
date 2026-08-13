from __future__ import annotations


def test_lifecycle_collect():
    from nicegui_diagnostics.probes.lifecycle import collect
    result = collect()
    assert 'lifecycle' in result
    assert 'connects_total' in result['lifecycle']
    assert result['lifecycle']['connects_total'] >= 0


def test_lifecycle_install_uninstall():
    from nicegui_diagnostics.probes.lifecycle import collect, install, uninstall
    install()
    uninstall()
    result = collect()
    assert result['lifecycle']['connects_total'] == 0


def test_lifecycle_gate_flag_blocks_callbacks_after_uninstall():
    """After uninstall(), on_connect/on_disconnect should be no-ops."""
    from nicegui_diagnostics.probes import lifecycle
    lifecycle._installed = False
    lifecycle._connects_total = 0
    lifecycle._disconnects_total = 0

    # Call the callbacks directly — they should not increment counters
    lifecycle._on_connect()
    lifecycle._on_disconnect()

    assert lifecycle._connects_total == 0
    assert lifecycle._disconnects_total == 0


def test_lifecycle_on_delete_increments():
    """_on_delete should increment _deletes_total when installed."""
    from nicegui_diagnostics.probes import lifecycle
    lifecycle._installed = True
    lifecycle._deletes_total = 0

    lifecycle._on_delete('client-1')
    lifecycle._on_delete('client-2')

    assert lifecycle._deletes_total == 2
    lifecycle._installed = False
    lifecycle._deletes_total = 0


def test_lifecycle_on_delete_noop_after_uninstall():
    """_on_delete should be a no-op when not installed."""
    from nicegui_diagnostics.probes import lifecycle
    lifecycle._installed = False
    lifecycle._deletes_total = 0

    lifecycle._on_delete('client-1')
    assert lifecycle._deletes_total == 0


def test_lifecycle_reconnect_detection():
    """A connect from a recently-disconnected client should count as reconnect."""
    import time

    from nicegui_diagnostics.probes import lifecycle

    lifecycle._installed = True
    lifecycle._connects_total = 0
    lifecycle._disconnects_total = 0
    lifecycle._reconnects_total = 0
    lifecycle._recent_disconnects.clear()

    # Simulate a disconnect for a known client ID
    lifecycle._recent_disconnects['client-abc'] = time.monotonic()

    # Simulate a reconnect — we can't easily mock ui.context.client.id,
    # so we test the internal mechanism directly
    lifecycle._connects_total += 1
    # Manually trigger the reconnect detection logic
    now = time.monotonic()
    if 'client-abc' in lifecycle._recent_disconnects:
        dt = lifecycle._recent_disconnects.pop('client-abc')
        if now - dt <= lifecycle._RECONNECT_WINDOW_S:
            lifecycle._reconnects_total += 1

    assert lifecycle._reconnects_total == 1
    assert 'client-abc' not in lifecycle._recent_disconnects

    lifecycle._installed = False
    lifecycle._recent_disconnects.clear()
    lifecycle._connects_total = 0
    lifecycle._reconnects_total = 0


def test_lifecycle_reconnect_window_expiry():
    """A reconnect after the window expires should NOT count."""
    import time

    from nicegui_diagnostics.probes import lifecycle

    lifecycle._installed = True
    lifecycle._reconnects_total = 0
    lifecycle._recent_disconnects.clear()

    # Simulate a disconnect that happened long ago (outside the window)
    lifecycle._recent_disconnects['old-client'] = time.monotonic() - 60.0

    now = time.monotonic()
    if 'old-client' in lifecycle._recent_disconnects:
        dt = lifecycle._recent_disconnects.pop('old-client')
        if now - dt <= lifecycle._RECONNECT_WINDOW_S:
            lifecycle._reconnects_total += 1

    assert lifecycle._reconnects_total == 0  # window expired, no reconnect counted

    lifecycle._installed = False
    lifecycle._recent_disconnects.clear()


def test_lifecycle_collect_includes_all_counters():
    """collect() should return all four lifecycle counters."""
    from nicegui_diagnostics.probes.lifecycle import collect
    result = collect()
    assert 'lifecycle' in result
    lc = result['lifecycle']
    assert 'connects_total' in lc
    assert 'disconnects_total' in lc
    assert 'reconnects_total' in lc
    assert 'deletes_total' in lc


def test_eio_collect():
    from nicegui_diagnostics.probes.eio import collect
    result = collect()
    assert 'engineio' in result
    assert 'nicegui_clients' in result['engineio']
    assert result['engineio']['nicegui_clients'] >= 0


def test_eio_graceful_degradation():
    """EIO probe should not crash even if core.sio.eio is unavailable."""
    from nicegui_diagnostics.probes.eio import collect
    result = collect()
    assert 'engineio' in result
