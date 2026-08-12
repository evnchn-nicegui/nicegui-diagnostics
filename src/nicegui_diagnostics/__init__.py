"""nicegui-diagnostics — runtime introspection for NiceGUI applications."""
from __future__ import annotations

import importlib
import logging
from datetime import datetime, timezone
from types import ModuleType
from typing import Any, Callable

from nicegui_diagnostics import _bus

__version__ = '0.1.0.dev0'

_log = logging.getLogger(__name__)

_installed: bool = False
_collectors: dict[str, Callable[[], dict[str, Any]]] = {}
_enabled_features: set[str] = set()
_probe_modules: dict[str, ModuleType] = {}

_FEATURE_PROBES: dict[str, str] = {
    'tasks': 'nicegui_diagnostics.probes.tasks',
    'memory': 'nicegui_diagnostics.probes.memory',
    'clients': 'nicegui_diagnostics.probes.clients',
    'config': 'nicegui_diagnostics.probes.config',
    'event_loop_lag': 'nicegui_diagnostics.probes.event_loop_lag',
    'stack_dump': 'nicegui_diagnostics.probes.stack_dump',
    'delta': 'nicegui_diagnostics.probes.delta',
    'lifecycle': 'nicegui_diagnostics.probes.lifecycle',
    'eio': 'nicegui_diagnostics.probes.eio',
    'js_rtt': 'nicegui_diagnostics.probes.ws_rtt',
    'heartbeat': 'nicegui_diagnostics.probes.heartbeat',
}

# Features whose probe modules actually exist — used as the default when
# install() is called with features=None so we don't try to import stubs.
_IMPLEMENTED_FEATURES: frozenset[str] = frozenset({
    'tasks', 'memory', 'clients', 'config', 'event_loop_lag', 'stack_dump', 'delta',
})

# Stored kwargs for use by probes / dashboard
_structlog_interval_s: float = 0
_memory_restart_threshold_mb: float | None = None
_auth: Any = None
_stack_dump_port: int = 9999
_on_before_restart: Callable[[], None] | None = None


def install(
    features: list[str] | None = None,
    *,
    structlog_interval_s: float = 0,
    memory_restart_threshold_mb: float | None = None,
    auth: Any = None,
    extra_collectors: dict[str, Callable[[], dict[str, Any]]] | None = None,
    stack_dump_port: int = 9999,
    on_before_restart: Callable[[], None] | None = None,
) -> None:
    """Install the diagnostics framework.

    Args:
        features: List of feature names to enable. ``None`` enables all known features.
        structlog_interval_s: Interval in seconds for structlog-based logging (0 = disabled).
        memory_restart_threshold_mb: Restart the process when RSS exceeds this threshold.
        auth: Authentication configuration for the diagnostics endpoint.
        extra_collectors: Additional named collector callables to register.
        stack_dump_port: Port for the stack dump debug server.
        on_before_restart: Callback invoked before a memory-threshold restart.
    """
    global _installed, _structlog_interval_s, _memory_restart_threshold_mb
    global _auth, _stack_dump_port, _on_before_restart

    if _installed:
        raise RuntimeError('nicegui_diagnostics is already installed')

    _installed = True

    # Store configuration for later use
    _structlog_interval_s = structlog_interval_s
    _memory_restart_threshold_mb = memory_restart_threshold_mb
    _auth = auth
    _stack_dump_port = stack_dump_port
    _on_before_restart = on_before_restart

    # --- Install the API endpoint (always, not feature-gated) ---
    try:
        from nicegui_diagnostics import api as _api_module

        _api_module.install(auth_fn=auth)

        # Register the diagnostics route on NiceGUI's Starlette app so it
        # actually serves HTTP requests (HIGH #1 fix).
        from nicegui import app as nicegui_app

        route = _api_module.get_route()
        if route is not None:
            nicegui_app.routes.append(route)
    except Exception:
        _log.warning('API endpoint install() failed', exc_info=True)

    # --- Register ui.diagnostics_view() on NiceGUI's ui namespace ---
    try:
        from nicegui import ui as nicegui_ui
        from nicegui_diagnostics.elements.diagnostics_view import DiagnosticsView

        nicegui_ui.diagnostics_view = DiagnosticsView
    except Exception:
        _log.warning('UI element registration failed', exc_info=True)

    # --- Install the structlog emitter (only when interval > 0) ---
    if structlog_interval_s > 0:
        try:
            from nicegui_diagnostics import emitter as _emitter_module

            _emitter_module.install(interval_s=structlog_interval_s)
        except Exception:
            _log.warning('Emitter install() failed', exc_info=True)

    # Resolve features — default to only implemented probes to avoid import
    # warnings for stub modules (lifecycle, eio, ws_rtt, heartbeat).
    if features is None:
        features = sorted(_IMPLEMENTED_FEATURES)

    for feature in features:
        module_path = _FEATURE_PROBES.get(feature)
        if module_path is None:
            _log.warning('Unknown feature: %s', feature)
            continue
        try:
            mod = importlib.import_module(module_path)
        except Exception:
            _log.warning('Could not import probe module %s for feature %r', module_path, feature)
            continue
        _enabled_features.add(feature)
        _probe_modules[feature] = mod
        if hasattr(mod, 'install'):
            try:
                # stack_dump needs the configured port
                if feature == 'stack_dump':
                    mod.install(port=stack_dump_port)
                else:
                    mod.install()
            except Exception:
                _log.warning('Probe %s install() failed', feature, exc_info=True)

    # Register extra collectors
    if extra_collectors:
        for name, fn in extra_collectors.items():
            _collectors[name] = fn


def uninstall() -> None:
    """Uninstall the diagnostics framework and clean up all state."""
    global _installed, _collectors, _enabled_features, _probe_modules
    global _structlog_interval_s, _memory_restart_threshold_mb
    global _auth, _stack_dump_port, _on_before_restart

    # Tear down probe modules
    for feature, mod in _probe_modules.items():
        if hasattr(mod, 'uninstall'):
            try:
                mod.uninstall()
            except Exception:
                _log.warning('Probe %s uninstall() failed', feature, exc_info=True)

    # Tear down API endpoint
    try:
        from nicegui_diagnostics import api as _api_module

        # Remove the diagnostics route from NiceGUI's Starlette app (HIGH #1 fix).
        from nicegui import app as nicegui_app

        route = _api_module.get_route()
        if route is not None and route in nicegui_app.routes:
            nicegui_app.routes.remove(route)

        _api_module.uninstall()
    except Exception:
        _log.warning('API endpoint uninstall() failed', exc_info=True)

    # Remove ui.diagnostics_view
    try:
        from nicegui import ui as nicegui_ui

        if hasattr(nicegui_ui, 'diagnostics_view'):
            delattr(nicegui_ui, 'diagnostics_view')
    except Exception:
        pass

    # Tear down emitter
    try:
        from nicegui_diagnostics import emitter as _emitter_module

        _emitter_module.uninstall()
    except Exception:
        _log.warning('Emitter uninstall() failed', exc_info=True)

    _installed = False
    _collectors = {}
    _enabled_features = set()
    _probe_modules = {}
    _structlog_interval_s = 0
    _memory_restart_threshold_mb = None
    _auth = None
    _stack_dump_port = 9999
    _on_before_restart = None
    _bus.reset()


def collect_snapshot(*, client_id: str | None = None, verbose: bool = False) -> dict[str, Any]:
    """Collect a diagnostic snapshot from all enabled probes and registered collectors.

    Args:
        client_id: Optional client identifier to scope the snapshot.
        verbose: If True, include additional detail in the snapshot.

    Returns:
        A dictionary containing the merged snapshot data.
    """
    # Forward client_id/verbose to the clients probe so it can scope its
    # output (HIGH #3 fix).
    if 'clients' in _probe_modules:
        from .probes import clients as _clients_probe

        _clients_probe.configure(client_id=client_id, verbose=verbose)

    result: dict[str, Any] = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
    }

    for feature, mod in _probe_modules.items():
        if hasattr(mod, 'collect'):
            try:
                data = mod.collect()
                if isinstance(data, dict):
                    # Merge probe keys directly into the snapshot instead of
                    # nesting under the feature name (HIGH #2 fix).  Probes
                    # already return their own top-level key, e.g.
                    # {"memory": {"peak_rss_bytes": ...}}.
                    result.update(data)
            except Exception:
                _log.warning('Probe %s collect() failed', feature, exc_info=True)

    for name, fn in _collectors.items():
        try:
            data = fn()
            if isinstance(data, dict):
                result[name] = data
        except Exception:
            _log.warning('Collector %r failed', name, exc_info=True)

    return result


def register_collector(name: str, callable: Callable[[], dict[str, Any]]) -> None:
    """Register a named collector callable that will be invoked during snapshot collection."""
    _collectors[name] = callable


__all__ = ['install', 'uninstall', 'collect_snapshot', 'register_collector', '__version__']
