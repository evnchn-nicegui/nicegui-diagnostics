"""Legacy diagnostics view — monolithic Log-element display.

Ported from upstream PR #5867. v0.1 ships this as the 'known-deficient
default'; composable sub-elements are the v0.2 carrot.
"""
from __future__ import annotations

from typing import Literal

from nicegui import ui
from nicegui.element import Element

from .. import collect_snapshot


class DiagnosticsView(Element):
    """Display a live diagnostics snapshot."""

    def __init__(
        self,
        *,
        scope: Literal["client", "global"] = "client",
        mode: Literal["append", "replace"] = "append",
        interval: float | None = None,
        max_lines: int = 200,
    ) -> None:
        """
        :param scope: 'client' for per-client detail, 'global' for server-wide
        :param mode: 'append' preserves history, 'replace' clears before refresh
        :param interval: auto-refresh interval in seconds; None disables
        :param max_lines: maximum log lines retained (prevents unbounded DOM growth)
        """
        super().__init__()
        self._scope = scope
        self._mode = mode

        with self:
            self._log = ui.log(max_lines=max_lines).classes("w-full")
            ui.button("Refresh", on_click=self.refresh)
            if interval is not None:
                ui.timer(interval, self.refresh)

    def _resolve_client_id(self) -> str | None:
        """Return the active client ID when scope is 'client', else None."""
        if self._scope == "global":
            return None
        try:
            return ui.context.client.id  # type: ignore[attr-defined]
        except (RuntimeError, AttributeError):
            return None

    def refresh(self) -> None:
        """Fetch and display a diagnostics snapshot."""
        snapshot = collect_snapshot(
            client_id=self._resolve_client_id(),
        )

        if self._mode == "replace":
            self._log.clear()

        self._log.push(f'--- {snapshot.get("timestamp", "?")} ---')

        tasks = snapshot.get("asyncio_tasks", {})
        if tasks:
            self._log.push(f'Tasks: {tasks.get("total", "?")}')

        clients = snapshot.get("clients", {})
        if clients:
            self._log.push(f'Clients: {clients.get("total", "?")} ({clients.get("connected", "?")} connected)')

        memory = snapshot.get("memory", {})
        if memory.get("current_rss_bytes") is not None:
            mb = memory["current_rss_bytes"] / (1024 * 1024)
            self._log.push(f"Memory: {mb:.1f} MB")
        elif memory.get("peak_rss_bytes") is not None:
            mb = memory["peak_rss_bytes"] / (1024 * 1024)
            self._log.push(f"Peak memory: {mb:.1f} MB")


def install() -> None:
    """No-op — the element is available on import."""


def uninstall() -> None:
    """No-op."""


def collect() -> dict:
    """Return element availability status."""
    return {"diagnostics_view_available": True}
