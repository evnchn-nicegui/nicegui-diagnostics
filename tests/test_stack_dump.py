from __future__ import annotations
import urllib.request
import urllib.error
import pytest

from nicegui_diagnostics.probes import stack_dump


def setup_function():
    stack_dump.uninstall()


def teardown_function():
    stack_dump.uninstall()


def test_install_and_collect():
    stack_dump.install(port=0)
    result = stack_dump.collect()
    assert result["stack_dump_enabled"] is True
    assert isinstance(result["stack_dump_port"], int)


def test_stacks_endpoint():
    stack_dump.install(port=0)
    port = stack_dump._server.server_address[1]
    url = f"http://127.0.0.1:{port}/stacks"
    with urllib.request.urlopen(url) as resp:
        body = resp.read().decode()
    assert resp.status == 200
    assert "=== thread" in body


def test_404_on_other_paths():
    stack_dump.install(port=0)
    port = stack_dump._server.server_address[1]
    url = f"http://127.0.0.1:{port}/other"
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(url)
    assert exc_info.value.code == 404


def test_uninstall():
    stack_dump.install(port=0)
    stack_dump.uninstall()
    result = stack_dump.collect()
    assert result["stack_dump_enabled"] is False
    assert result["stack_dump_port"] is None


def test_localhost_only():
    stack_dump.install(port=0)
    addr = stack_dump._server.server_address
    assert addr[0] == "127.0.0.1"
