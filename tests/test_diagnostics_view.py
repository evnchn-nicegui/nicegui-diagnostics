from __future__ import annotations

from unittest.mock import MagicMock, patch


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


def test_scope_global_passes_none_client_id():
    """scope='global' should always pass client_id=None to collect_snapshot."""
    from nicegui_diagnostics.elements.diagnostics_view import DiagnosticsView

    with patch("nicegui_diagnostics.elements.diagnostics_view.collect_snapshot") as mock_collect:
        mock_collect.return_value = {"timestamp": "now"}
        view = DiagnosticsView.__new__(DiagnosticsView)
        view._scope = "global"
        view._mode = "append"
        view._log = MagicMock()

        view.refresh()

        mock_collect.assert_called_once_with(client_id=None)


def test_scope_client_attempts_to_resolve_client_id():
    """scope='client' should attempt to get the active client ID.

    Without a real NiceGUI context, _resolve_client_id falls back to None,
    but the code path must go through the client-id resolution logic
    (not hardcode None like scope='global').
    """
    from nicegui_diagnostics.elements.diagnostics_view import DiagnosticsView

    with patch("nicegui_diagnostics.elements.diagnostics_view.collect_snapshot") as mock_collect:
        mock_collect.return_value = {"timestamp": "now"}
        view = DiagnosticsView.__new__(DiagnosticsView)
        view._scope = "client"
        view._mode = "append"
        view._log = MagicMock()

        # Patch _resolve_client_id to simulate a real client context
        with patch.object(view, "_resolve_client_id", return_value="test-client-123"):
            view.refresh()

        mock_collect.assert_called_once_with(client_id="test-client-123")


def test_scope_client_falls_back_to_none_without_context():
    """scope='client' without a NiceGUI context should fall back to client_id=None."""
    from nicegui_diagnostics.elements import diagnostics_view as dv

    with patch.object(dv, "collect_snapshot", return_value={"timestamp": "now"}) as mock_collect:
        view = dv.DiagnosticsView.__new__(dv.DiagnosticsView)
        view._scope = "client"
        view._mode = "append"
        view._log = MagicMock()

        # Mock ui.context to raise RuntimeError (simulating no NiceGUI context)
        mock_context = MagicMock()
        mock_context.client = property(lambda self: (_ for _ in ()).throw(RuntimeError("no context")))
        with patch.object(dv.ui, "context", new=mock_context):
            # Make accessing .client.id raise
            type(mock_context).client = property(lambda _: (_ for _ in ()).throw(RuntimeError("no client")))
            view.refresh()

        mock_collect.assert_called_once_with(client_id=None)


def test_max_lines_is_bounded():
    """ui.log should be created with a bounded max_lines to prevent unbounded DOM growth."""
    from nicegui_diagnostics.elements import diagnostics_view as dv

    with patch.object(dv, "ui") as mock_ui:
        mock_log = MagicMock()
        mock_ui.log.return_value = mock_log
        mock_log.classes.return_value = mock_log
        mock_ui.button.return_value = MagicMock()
        mock_ui.timer.return_value = MagicMock()

        # Mock Element.__init__ and __enter__/__exit__ to avoid needing a real slot
        with (
            patch("nicegui.element.Element.__init__", return_value=None),
            patch("nicegui.element.Element.__enter__", return_value=MagicMock()),
            patch("nicegui.element.Element.__exit__", return_value=False),
        ):
            dv.DiagnosticsView()

        # Verify ui.log was called with max_lines parameter
        mock_ui.log.assert_called_once()
        call_kwargs = mock_ui.log.call_args
        max_lines = call_kwargs.kwargs.get("max_lines")
        assert max_lines is not None
        assert isinstance(max_lines, int)
        assert max_lines > 0


def test_max_lines_custom_value():
    """Custom max_lines kwarg should be forwarded to ui.log."""
    from nicegui_diagnostics.elements import diagnostics_view as dv

    with patch.object(dv, "ui") as mock_ui:
        mock_log = MagicMock()
        mock_ui.log.return_value = mock_log
        mock_log.classes.return_value = mock_log
        mock_ui.button.return_value = MagicMock()
        mock_ui.timer.return_value = MagicMock()

        with (
            patch("nicegui.element.Element.__init__", return_value=None),
            patch("nicegui.element.Element.__enter__", return_value=MagicMock()),
            patch("nicegui.element.Element.__exit__", return_value=False),
        ):
            dv.DiagnosticsView(max_lines=500)

        call_kwargs = mock_ui.log.call_args
        assert call_kwargs.kwargs.get("max_lines") == 500
