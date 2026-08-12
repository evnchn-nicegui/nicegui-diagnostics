from __future__ import annotations


def test_import():
    """The module imports without error."""
    from nicegui_diagnostics.elements import diagnostics_view
    assert hasattr(diagnostics_view, "DiagnosticsView")


def test_install_uninstall():
    from nicegui_diagnostics.elements.diagnostics_view import install, uninstall
    install()  # no-op, should not raise
    uninstall()  # no-op, should not raise


def test_collect():
    from nicegui_diagnostics.elements.diagnostics_view import collect
    result = collect()
    assert result["diagnostics_view_available"] is True


def test_class_exists():
    from nicegui_diagnostics.elements.diagnostics_view import DiagnosticsView
    assert DiagnosticsView is not None
    # Check it has the expected methods
    assert hasattr(DiagnosticsView, "refresh")
