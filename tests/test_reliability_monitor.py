"""Real unit tests for the Systems & Automation circuit-breaker state
machine (agents/systems/reliability_monitor.py) -- the piece that was
hardened live on 2026-08-06 after a real gap was found (a DB hiccup on
one service could silently abort the whole sweep). These tests exercise
the pure state-transition logic with the database and health checks
mocked out -- no real Supabase, no real network calls, safe to run
anywhere including CI.
"""

from unittest.mock import patch

import pytest

from agents.systems import reliability_monitor as rm


class FakeStore:
    """In-memory stand-in for shared/systems_db_connector.py -- lets
    tests drive check_and_update() through real state transitions
    without touching Supabase."""

    def __init__(self, initial_state: str = "healthy", failure_count: int = 0, auto_restart_permitted: bool = True):
        self.row = {
            "state": initial_state,
            "failure_count": failure_count,
            "auto_restart_permitted": auto_restart_permitted,
            "metadata": {},
        }
        self.write_calls: list[dict] = []
        self.audit_calls: list[tuple] = []

    def get_or_create(self, service_name, auto_restart_permitted):
        return dict(self.row)

    def write(self, service_name, updates):
        self.write_calls.append(updates)
        self.row.update(updates)

    def log_state_change(self, service_name, old_state, new_state):
        self.audit_calls.append((old_state, new_state))


def _run(store: FakeStore, ok: bool, auto_restart_permitted: bool = True, restart_fn=None):
    fake_registry = {
        "test_service": (lambda: ok, auto_restart_permitted, restart_fn),
    }
    with (
        patch.object(rm, "_service_registry", return_value=fake_registry),
        patch.object(rm, "_get_or_create_row", side_effect=store.get_or_create),
        patch.object(rm, "_write_row", side_effect=store.write),
        patch.object(rm, "_log_state_change", side_effect=store.log_state_change),
    ):
        return rm.check_and_update("test_service")


def test_healthy_check_stays_healthy_no_alert():
    store = FakeStore(initial_state="healthy", failure_count=0)
    result = _run(store, ok=True)
    assert result["new_state"] == "healthy"
    assert result["alert"] is False


def test_first_failure_moves_to_warning_and_alerts():
    store = FakeStore(initial_state="healthy", failure_count=0)
    result = _run(store, ok=False)
    assert result["new_state"] == "warning"
    assert result["alert"] is True


def test_second_consecutive_failure_opens_circuit():
    store = FakeStore(initial_state="warning", failure_count=1)
    result = _run(store, ok=False)
    assert result["new_state"] == "open_circuit"
    assert result["alert"] is True


def test_open_circuit_attempts_exactly_one_restart_when_permitted():
    restart_calls = []
    store = FakeStore(initial_state="open_circuit", failure_count=2, auto_restart_permitted=True)
    result = _run(store, ok=False, auto_restart_permitted=True, restart_fn=lambda: restart_calls.append(1))
    assert result["new_state"] == "recovery_test"
    assert len(restart_calls) == 1


def test_recovery_test_success_returns_to_healthy():
    store = FakeStore(initial_state="recovery_test", failure_count=3)
    result = _run(store, ok=True)
    assert result["new_state"] == "healthy"
    assert result["alert"] is True


def test_recovery_test_failure_moves_to_fallback_not_another_restart():
    """The core anti-thrash guarantee: a still-failing service after
    its one restart attempt must NOT trigger a second restart -- it
    gives up and waits, per governance Rule 4 (one remediation
    attempt per incident)."""
    restart_calls = []
    store = FakeStore(initial_state="recovery_test", failure_count=3, auto_restart_permitted=True)
    result = _run(store, ok=False, auto_restart_permitted=True, restart_fn=lambda: restart_calls.append(1))
    assert result["new_state"] == "fallback"
    assert len(restart_calls) == 0


def test_non_restartable_service_goes_straight_from_open_circuit_to_fallback():
    """Ollama/Supabase-style services (auto_restart_permitted=False)
    must never have a restart attempted -- confirms governance Rules
    2/3 hold at the state-machine level, not just by convention."""
    store = FakeStore(initial_state="open_circuit", failure_count=2, auto_restart_permitted=False)
    result = _run(store, ok=False, auto_restart_permitted=False, restart_fn=None)
    assert result["new_state"] == "fallback"


def test_fallback_does_not_re_alert_every_check():
    """Once in fallback, repeated failures must not spam an alert on
    every single check -- only the transition into fallback alerts."""
    store = FakeStore(initial_state="fallback", failure_count=5, auto_restart_permitted=False)
    result = _run(store, ok=False, auto_restart_permitted=False, restart_fn=None)
    assert result["new_state"] == "fallback"
    assert result["alert"] is False


def test_db_read_failure_does_not_raise_and_is_reported():
    """The exact gap found and fixed live 2026-08-06: a DB-layer
    failure on one service must never raise out of check_and_update
    (which would abort the whole sweep) -- it must be reported back
    in the result instead."""
    fake_registry = {"test_service": (lambda: True, True, None)}
    with (
        patch.object(rm, "_service_registry", return_value=fake_registry),
        patch.object(rm, "_get_or_create_row", side_effect=RuntimeError("simulated Supabase outage")),
    ):
        result = rm.check_and_update("test_service")
    assert "error" in result


def test_unknown_service_returns_error_not_exception():
    fake_registry = {}
    with patch.object(rm, "_service_registry", return_value=fake_registry):
        result = rm.check_and_update("nonexistent_service")
    assert result["error"] == "unknown service"


@pytest.mark.parametrize(
    "division,expected_port",
    [
        ("audit", 8001),
        ("forex", 8002),
        ("fixera", 8003),
        ("personal", 8004),
        ("learning", 8005),
        ("rii", 8006),
    ],
)
def test_division_port_map_matches_live_deployment(division, expected_port):
    """Guards against a silent typo in DIVISION_PORTS ever causing the
    monitor to health-check (or restart!) the wrong service."""
    assert rm.DIVISION_PORTS[division] == expected_port
