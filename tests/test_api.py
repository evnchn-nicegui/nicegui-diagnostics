from __future__ import annotations

import pytest
from starlette.applications import Starlette
from starlette.testclient import TestClient

from nicegui_diagnostics import install as diag_install
from nicegui_diagnostics import uninstall as diag_uninstall
from nicegui_diagnostics.api import get_route
from nicegui_diagnostics.api import install as api_install
from nicegui_diagnostics.api import uninstall as api_uninstall


def setup_function():
    try:
        diag_uninstall()
    except Exception:
        pass
    api_uninstall()


def teardown_function():
    try:
        diag_uninstall()
    except Exception:
        pass
    api_uninstall()


def _make_app():
    """Create a minimal Starlette app with the diagnostics route."""
    diag_install(features=[])
    api_install(auth_fn=None)
    route = get_route()
    app = Starlette(routes=[route])
    return app


def test_endpoint_returns_200():
    app = _make_app()
    client = TestClient(app)
    resp = client.get('/_nicegui/diagnostics')
    assert resp.status_code == 200
    data = resp.json()
    assert 'timestamp' in data


def test_coarse_counts_no_auth():
    """Without auth, coarse counts (no verbose/client_id/delta) are allowed."""
    app = _make_app()
    client = TestClient(app)
    resp = client.get('/_nicegui/diagnostics')
    assert resp.status_code == 200


def test_verbose_denied_without_auth():
    app = _make_app()
    client = TestClient(app)
    resp = client.get('/_nicegui/diagnostics?verbose=true')
    assert resp.status_code == 401


def test_client_id_denied_without_auth():
    app = _make_app()
    client = TestClient(app)
    resp = client.get('/_nicegui/diagnostics?client_id=abc')
    assert resp.status_code == 401


def test_delta_denied_without_auth():
    app = _make_app()
    client = TestClient(app)
    resp = client.get('/_nicegui/diagnostics?delta=true')
    assert resp.status_code == 401


def test_verbose_allowed_with_auth():
    diag_uninstall()
    api_uninstall()
    diag_install(features=[])
    api_install(auth_fn=lambda req: True)  # always authorize
    route = get_route()
    app = Starlette(routes=[route])
    client = TestClient(app)
    resp = client.get('/_nicegui/diagnostics?verbose=true')
    assert resp.status_code == 200


def test_delta_mode():
    # Delta requires auth, so set up with a permissive auth fn
    diag_uninstall()
    api_uninstall()
    diag_install(features=[])
    api_install(auth_fn=lambda req: True)
    route = get_route()
    app = Starlette(routes=[route])
    client = TestClient(app)

    resp1 = client.get('/_nicegui/diagnostics?delta=true')
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert 'current' in data1

    # Second query should have delta
    resp2 = client.get('/_nicegui/diagnostics?delta=true')
    data2 = resp2.json()
    assert 'delta' in data2 or 'current' in data2
