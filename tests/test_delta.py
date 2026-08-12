from __future__ import annotations
from nicegui_diagnostics.probes.delta import compute_delta, reset, collect, install, uninstall

def setup_function():
    reset()

def test_first_query_no_delta():
    result = compute_delta({"tasks": 10, "clients": 5})
    assert "delta" not in result
    assert result["current"] == {"tasks": 10, "clients": 5}

def test_second_query_has_delta():
    compute_delta({"tasks": 10, "clients": 5})
    result = compute_delta({"tasks": 15, "clients": 5})
    assert result["delta"]["tasks"] == "+5"
    assert result["delta"]["clients"] == "0"
    assert "since_last_query_s" in result

def test_negative_delta():
    compute_delta({"tasks": 20})
    result = compute_delta({"tasks": 15})
    assert result["delta"]["tasks"] == "-5"

def test_nested_dict_delta():
    compute_delta({"server": {"tasks": 10, "memory": 100}})
    result = compute_delta({"server": {"tasks": 12, "memory": 95}})
    assert result["delta"]["server.tasks"] == "+2"
    assert result["delta"]["server.memory"] == "-5"

def test_non_numeric_omitted():
    compute_delta({"name": "test", "count": 5})
    result = compute_delta({"name": "test", "count": 10})
    assert "name" not in result["delta"]

def test_reset():
    compute_delta({"tasks": 10})
    reset()
    result = compute_delta({"tasks": 15})
    assert "delta" not in result

def test_uninstall_resets():
    compute_delta({"tasks": 10})
    uninstall()
    assert collect()["delta_available"] is False

def test_float_delta():
    compute_delta({"lag_ms": 1.5})
    result = compute_delta({"lag_ms": 3.2})
    assert result["delta"]["lag_ms"] == "+1.7"
