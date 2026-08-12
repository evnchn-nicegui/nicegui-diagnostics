from __future__ import annotations


def test_lifecycle_collect():
    from nicegui_diagnostics.probes.lifecycle import collect
    result = collect()
    assert "lifecycle" in result
    assert "connects_total" in result["lifecycle"]
    assert result["lifecycle"]["connects_total"] >= 0


def test_lifecycle_install_uninstall():
    from nicegui_diagnostics.probes.lifecycle import install, uninstall, collect
    install()
    uninstall()
    result = collect()
    assert result["lifecycle"]["connects_total"] == 0


def test_eio_collect():
    from nicegui_diagnostics.probes.eio import collect
    result = collect()
    assert "engineio" in result
    assert "nicegui_clients" in result["engineio"]
    assert result["engineio"]["nicegui_clients"] >= 0


def test_eio_graceful_degradation():
    """EIO probe should not crash even if core.sio.eio is unavailable."""
    from nicegui_diagnostics.probes.eio import collect
    result = collect()
    # eio_sessions may be None if not available, that's fine
    assert "engineio" in result
