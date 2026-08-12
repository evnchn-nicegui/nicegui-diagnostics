"""Internal ObservableDict metric bus singleton."""
from __future__ import annotations

from nicegui.observables import ObservableDict

_bus: ObservableDict | None = None


def get_bus() -> ObservableDict:
    global _bus
    if _bus is None:
        _bus = ObservableDict()
    return _bus


def make_metric_bus() -> ObservableDict:
    """Create a fresh metric bus for consumer use."""
    return ObservableDict()


def reset() -> None:
    """Reset the singleton bus. Call from uninstall()."""
    global _bus
    _bus = None
