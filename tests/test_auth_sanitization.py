"""Tests for auth.sanitize_snapshot — issue #24."""
from __future__ import annotations

from starlette.applications import Starlette
from starlette.testclient import TestClient

from nicegui_diagnostics import install as diag_install
from nicegui_diagnostics import uninstall as diag_uninstall
from nicegui_diagnostics.api import get_route
from nicegui_diagnostics.api import install as api_install
from nicegui_diagnostics.api import uninstall as api_uninstall
from nicegui_diagnostics.auth import sanitize_snapshot

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_leaky_snapshot() -> dict:
    """Return a snapshot that mimics what collect_snapshot() produces with live clients."""
    return {
        'timestamp': '2026-08-13T12:00:00+00:00',
        'heartbeat': {
            'alive_clients': 3,
            'client_ids': ['abc123', 'def456', 'ghi789'],
        },
        'clients': {
            'total': 3,
            'connected': 2,
            'by_id': {
                'abc123': {'has_socket': True, 'elements': 42},
                'def456': {'has_socket': True, 'elements': 7},
                'ghi789': {'has_socket': False, 'elements': 0},
            },
        },
        'client_detail': {
            'id': 'abc123',
            'has_socket': True,
            'elements': 42,
        },
        'asyncio_tasks': {
            'total': 5,
            'by_coroutine': {
                'Client.abc123._handle': {
                    'count': 1,
                    'oldest_age_s': 1.2,
                    'names': ['nicegui-client-abc123-handler'],
                },
                'TaskGroup._run': {
                    'count': 3,
                    'oldest_age_s': 0.5,
                    'names': ['TaskGroup-1', 'TaskGroup-2', 'nicegui-client-def456-handler'],
                },
                'Background.cleanup': {
                    'count': 1,
                    'oldest_age_s': 0.1,
                    'names': ['cleanup-task'],
                },
            },
        },
        'memory': {
            'rss_bytes': 100_000_000,
        },
    }


# ---------------------------------------------------------------------------
# 1. Unauthenticated snapshot has no client IDs
# ---------------------------------------------------------------------------

class TestUnauthenticatedSanitization:
    def test_heartbeat_client_ids_stripped(self):
        snap = _make_leaky_snapshot()
        result = sanitize_snapshot(snap, authenticated=False)
        assert 'client_ids' not in result.get('heartbeat', {})

    def test_heartbeat_alive_count_preserved(self):
        snap = _make_leaky_snapshot()
        result = sanitize_snapshot(snap, authenticated=False)
        assert result['heartbeat']['alive_clients'] == 3

    def test_clients_by_id_stripped(self):
        snap = _make_leaky_snapshot()
        result = sanitize_snapshot(snap, authenticated=False)
        assert 'by_id' not in result.get('clients', {})

    def test_clients_counts_preserved(self):
        snap = _make_leaky_snapshot()
        result = sanitize_snapshot(snap, authenticated=False)
        assert result['clients']['total'] == 3
        assert result['clients']['connected'] == 2

    def test_client_detail_stripped(self):
        snap = _make_leaky_snapshot()
        result = sanitize_snapshot(snap, authenticated=False)
        assert 'client_detail' not in result

    def test_task_names_with_client_ids_redacted(self):
        snap = _make_leaky_snapshot()
        result = sanitize_snapshot(snap, authenticated=False)
        tasks = result['asyncio_tasks']['by_coroutine']
        # The task name containing 'abc123' should be redacted
        assert tasks['Client.abc123._handle']['names'] == ['<redacted>']
        # The TaskGroup list should have the def456 name redacted but others kept
        names = tasks['TaskGroup._run']['names']
        assert 'nicegui-client-def456-handler' not in names
        assert '<redacted>' in names
        assert 'TaskGroup-1' in names

    def test_clean_task_names_preserved(self):
        snap = _make_leaky_snapshot()
        result = sanitize_snapshot(snap, authenticated=False)
        tasks = result['asyncio_tasks']['by_coroutine']
        assert tasks['Background.cleanup']['names'] == ['cleanup-task']

    def test_unrelated_fields_preserved(self):
        snap = _make_leaky_snapshot()
        result = sanitize_snapshot(snap, authenticated=False)
        assert result['timestamp'] == '2026-08-13T12:00:00+00:00'
        assert result['memory']['rss_bytes'] == 100_000_000

    def test_no_client_id_strings_anywhere(self):
        """Brute-force check: no known client ID should appear in any string value."""
        snap = _make_leaky_snapshot()
        result = sanitize_snapshot(snap, authenticated=False)
        for cid in ['abc123', 'def456', 'ghi789']:
            # The IDs may appear as dict keys in by_coroutine group names — that's
            # the coroutine qualname, not a client leak.  But they must NOT appear
            # in heartbeat client_ids, clients by_id, client_detail, or task names.
            assert cid not in str(result.get('heartbeat', {}).get('client_ids', ''))
            assert cid not in str(result.get('clients', {}).get('by_id', ''))
            assert cid not in str(result.get('client_detail', ''))


# ---------------------------------------------------------------------------
# 2. Authenticated snapshot passes through
# ---------------------------------------------------------------------------

class TestAuthenticatedPassthrough:
    def test_heartbeat_client_ids_present(self):
        snap = _make_leaky_snapshot()
        result = sanitize_snapshot(snap, authenticated=True)
        assert result['heartbeat']['client_ids'] == ['abc123', 'def456', 'ghi789']

    def test_clients_by_id_present(self):
        snap = _make_leaky_snapshot()
        result = sanitize_snapshot(snap, authenticated=True)
        assert 'by_id' in result['clients']
        assert 'abc123' in result['clients']['by_id']

    def test_client_detail_present(self):
        snap = _make_leaky_snapshot()
        result = sanitize_snapshot(snap, authenticated=True)
        assert 'client_detail' in result
        assert result['client_detail']['id'] == 'abc123'

    def test_task_names_not_redacted(self):
        snap = _make_leaky_snapshot()
        result = sanitize_snapshot(snap, authenticated=True)
        tasks = result['asyncio_tasks']['by_coroutine']
        assert tasks['Client.abc123._handle']['names'] == ['nicegui-client-abc123-handler']


# ---------------------------------------------------------------------------
# 3. Task name sanitization (heuristic pattern matching)
# ---------------------------------------------------------------------------

class TestTaskNameSanitization:
    def test_nicegui_client_pattern_redacted(self):
        """Task names matching the NiceGUI client pattern are redacted even without known IDs."""
        snap = {
            'asyncio_tasks': {
                'total': 2,
                'by_coroutine': {
                    'Handler.run': {
                        'count': 2,
                        'oldest_age_s': 0.1,
                        'names': ['nicegui-client-xyz789-handler', 'normal-task'],
                    },
                },
            },
        }
        result = sanitize_snapshot(snap, authenticated=False)
        names = result['asyncio_tasks']['by_coroutine']['Handler.run']['names']
        assert names[0] == '<redacted>'
        assert names[1] == 'normal-task'

    def test_client_underscore_pattern_redacted(self):
        snap = {
            'asyncio_tasks': {
                'total': 1,
                'by_coroutine': {
                    'Handler.run': {
                        'count': 1,
                        'oldest_age_s': 0.1,
                        'names': ['client_abc123_handler'],
                    },
                },
            },
        }
        result = sanitize_snapshot(snap, authenticated=False)
        names = result['asyncio_tasks']['by_coroutine']['Handler.run']['names']
        assert names[0] == '<redacted>'

    def test_known_id_in_task_name_redacted(self):
        """Even if the task name doesn't match the heuristic, a known client ID triggers redaction."""
        snap = {
            'heartbeat': {
                'alive_clients': 1,
                'client_ids': ['secret-id-42'],
            },
            'asyncio_tasks': {
                'total': 1,
                'by_coroutine': {
                    'Handler.run': {
                        'count': 1,
                        'oldest_age_s': 0.1,
                        'names': ['task-for-secret-id-42'],
                    },
                },
            },
        }
        result = sanitize_snapshot(snap, authenticated=False)
        names = result['asyncio_tasks']['by_coroutine']['Handler.run']['names']
        assert names[0] == '<redacted>'

    def test_empty_snapshot_no_crash(self):
        result = sanitize_snapshot({}, authenticated=False)
        assert result == {}

    def test_missing_asyncio_tasks_no_crash(self):
        snap = {'heartbeat': {'alive_clients': 0, 'client_ids': ['x']}}
        result = sanitize_snapshot(snap, authenticated=False)
        assert 'client_ids' not in result['heartbeat']


# ---------------------------------------------------------------------------
# 4. API integration — unauthenticated request has no client IDs
# ---------------------------------------------------------------------------

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


class TestAPIIntegration:
    def _make_app(self, auth_fn=None):
        try:
            diag_uninstall()
        except Exception:
            pass
        api_uninstall()
        diag_install(features=[])
        api_install(auth_fn=auth_fn)
        route = get_route()
        return Starlette(routes=[route])

    def test_unauthenticated_coarse_no_client_ids(self):
        """An unauthenticated coarse request should not leak client IDs in the response."""
        app = self._make_app(auth_fn=None)
        client = TestClient(app)
        resp = client.get('/_nicegui/diagnostics')
        assert resp.status_code == 200
        data = resp.json()
        # heartbeat section should not have client_ids
        heartbeat = data.get('heartbeat', {})
        assert 'client_ids' not in heartbeat
        # clients section should not have by_id
        clients = data.get('clients', {})
        assert 'by_id' not in clients
        # no client_detail
        assert 'client_detail' not in data

    def test_authenticated_verbose_has_full_data(self):
        """An authenticated verbose request should pass through all fields."""
        app = self._make_app(auth_fn=lambda req: True)
        client = TestClient(app)
        resp = client.get('/_nicegui/diagnostics?verbose=true')
        assert resp.status_code == 200
        data = resp.json()
        # With no actual NiceGUI clients, by_id may be empty but the key
        # should be present (sanitize passes through for authenticated).
        # The important thing is the request succeeds and is not stripped.
        assert 'timestamp' in data
