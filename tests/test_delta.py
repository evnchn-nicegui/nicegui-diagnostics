"""Tests for per-caller delta baseline storage."""
from __future__ import annotations

from unittest.mock import patch

from nicegui_diagnostics.probes.delta import (
    _MAX_KEYS,
    _TTL_SECONDS,
    _baselines,
    collect,
    compute_delta,
    reset,
    uninstall,
)


def setup_function():
    reset()


# ── Backward compatibility ────────────────────────────────────────────────────


def test_first_query_no_delta():
    result = compute_delta({'tasks': 10, 'clients': 5})
    assert 'delta' not in result
    assert result['current'] == {'tasks': 10, 'clients': 5}


def test_second_query_has_delta():
    compute_delta({'tasks': 10, 'clients': 5})
    result = compute_delta({'tasks': 15, 'clients': 5})
    assert result['delta']['tasks'] == '+5'
    assert result['delta']['clients'] == '0'
    assert 'since_last_query_s' in result


def test_negative_delta():
    compute_delta({'tasks': 20})
    result = compute_delta({'tasks': 15})
    assert result['delta']['tasks'] == '-5'


def test_nested_dict_delta():
    compute_delta({'server': {'tasks': 10, 'memory': 100}})
    result = compute_delta({'server': {'tasks': 12, 'memory': 95}})
    assert result['delta']['server.tasks'] == '+2'
    assert result['delta']['server.memory'] == '-5'


def test_non_numeric_omitted():
    compute_delta({'name': 'test', 'count': 5})
    result = compute_delta({'name': 'test', 'count': 10})
    assert 'name' not in result['delta']


def test_reset():
    compute_delta({'tasks': 10})
    reset()
    result = compute_delta({'tasks': 15})
    assert 'delta' not in result


def test_uninstall_resets():
    compute_delta({'tasks': 10})
    uninstall()
    assert collect()['delta_available'] is False


def test_float_delta():
    compute_delta({'lag_ms': 1.5})
    result = compute_delta({'lag_ms': 3.2})
    assert result['delta']['lag_ms'] == '+1.7'


# ── Per-caller isolation (issue #29) ──────────────────────────────────────────


def test_interleaved_callers_isolated():
    """A, B, A — A's second response diffs against A's first, NOT B's."""
    # Caller A: first snapshot
    compute_delta({'tasks': 10}, delta_key='A')
    # Caller B: first snapshot (different value)
    compute_delta({'tasks': 100}, delta_key='B')
    # Caller A: second snapshot — should diff against A's first (10), not B's (100)
    result = compute_delta({'tasks': 15}, delta_key='A')
    assert result['delta']['tasks'] == '+5', 'A should diff against A own previous snapshot'
    assert result['delta_key'] == 'A'


def test_interleaved_three_callers():
    """Three callers interleaved — each sees only its own baseline."""
    compute_delta({'v': 1}, delta_key='x')
    compute_delta({'v': 100}, delta_key='y')
    compute_delta({'v': 1000}, delta_key='z')
    # x's second call: should diff against x's first (1), not z's (1000)
    result = compute_delta({'v': 3}, delta_key='x')
    assert result['delta']['v'] == '+2'
    # y's second call: should diff against y's first (100)
    result = compute_delta({'v': 150}, delta_key='y')
    assert result['delta']['v'] == '+50'


# ── Response metadata ─────────────────────────────────────────────────────────


def test_response_metadata_delta_key():
    result = compute_delta({'tasks': 10}, delta_key='engineer-1')
    assert result['delta_key'] == 'engineer-1'


def test_response_metadata_delta_since_present_after_baseline():
    compute_delta({'tasks': 10}, delta_key='k')
    result = compute_delta({'tasks': 15}, delta_key='k')
    assert 'delta_since' in result
    assert isinstance(result['delta_since'], float)


def test_response_metadata_delta_since_absent_on_first_call():
    result = compute_delta({'tasks': 10}, delta_key='k')
    assert 'delta_since' not in result


# ── Backward compatibility: default key ───────────────────────────────────────


def test_default_key_when_no_delta_key():
    """No delta_key → uses __default__, behaves like the old global baseline."""
    r1 = compute_delta({'tasks': 10})
    assert r1['delta_key'] == '__default__'
    r2 = compute_delta({'tasks': 15})
    assert r2['delta_key'] == '__default__'
    assert r2['delta']['tasks'] == '+5'


def test_default_key_and_explicit_key_are_independent():
    compute_delta({'tasks': 10})  # default key
    compute_delta({'tasks': 100}, delta_key='explicit')
    result = compute_delta({'tasks': 12})  # default key again
    assert result['delta']['tasks'] == '+2', 'default key should not see explicit key baseline'


# ── Bounded storage ───────────────────────────────────────────────────────────


def test_bounded_store_evicts_oldest():
    """Creating more keys than _MAX_KEYS evicts the oldest-accessed."""
    # Fill to capacity
    for i in range(_MAX_KEYS):
        compute_delta({'v': i}, delta_key=f'key-{i}')
    assert len(_baselines) == _MAX_KEYS

    # One more → should evict key-0 (oldest access)
    compute_delta({'v': 999}, delta_key='overflow')
    assert len(_baselines) == _MAX_KEYS
    assert 'key-0' not in _baselines
    assert 'overflow' in _baselines


def test_bounded_store_preserves_recently_accessed():
    """Accessing a key refreshes its last_access, protecting it from eviction."""
    for i in range(_MAX_KEYS):
        compute_delta({'v': i}, delta_key=f'key-{i}')

    # Re-access key-0 to refresh its last_access
    compute_delta({'v': 0}, delta_key='key-0')

    # Add one more → should evict key-1 (now the oldest), NOT key-0
    compute_delta({'v': 999}, delta_key='overflow')
    assert 'key-0' in _baselines
    assert 'key-1' not in _baselines


# ── TTL eviction ──────────────────────────────────────────────────────────────


def test_ttl_eviction():
    """Entries older than TTL are evicted on next compute_delta call."""
    fake_time = 1000.0

    with patch('nicegui_diagnostics.probes.delta.time') as mock_time:
        mock_time.monotonic.return_value = fake_time
        compute_delta({'tasks': 10}, delta_key='stale')
        assert 'stale' in _baselines

        # Advance time past TTL
        mock_time.monotonic.return_value = fake_time + _TTL_SECONDS + 1
        # Next call triggers eviction of stale entry
        compute_delta({'tasks': 20}, delta_key='fresh')

    assert 'stale' not in _baselines
    assert 'fresh' in _baselines


def test_ttl_not_evicted_within_window():
    """Entries within TTL are preserved."""
    fake_time = 1000.0

    with patch('nicegui_diagnostics.probes.delta.time') as mock_time:
        mock_time.monotonic.return_value = fake_time
        compute_delta({'tasks': 10}, delta_key='active')

        # Advance time but stay within TTL
        mock_time.monotonic.return_value = fake_time + _TTL_SECONDS - 1
        compute_delta({'tasks': 20}, delta_key='other')

    assert 'active' in _baselines
    assert 'other' in _baselines
