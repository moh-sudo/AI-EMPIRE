"""Scoped connector to AI_EMPIRE's own database for Systems & Automation
Division agents -- Reliability & Monitoring's equivalent of
shared/fixera_connector.py.

The JWT-minting/client mechanism now lives in shared/scoped_db.py
(extracted 2026-08-10 -- it had zero Systems-specific logic, the same
two-step dance regardless of which division's claim is being minted).
This module keeps its own table-specific helper functions
(get_circuit_breaker(), write_audit_vault(), etc.), which ARE real
Systems-specific logic and stay here.

That JWT carries a custom 'app_role': 'systems_agent' claim, and RLS
policies on circuit_breakers/audit_vault
(infrastructure/database/migrations/0010_systems_agent_rls_jwt.sql)
only allow SELECT/INSERT/UPDATE on circuit_breakers and SELECT/INSERT
on audit_vault to requests carrying that exact claim -- nothing else,
enforced by Postgres's own RLS engine, not application code.

Deliberately not shared/db.py's get_client(), which authenticates with
the all-powerful service_role key every other agent in the project
uses today and which bypasses Row-Level Security entirely.

This replaces the Postgres-role approach in
infrastructure/database/migrations/0009_systems_agent_scoped_role.sql,
which is real and correctly scoped but blocked by a Supabase Supavisor
pooler issue that rejects that role's connections before they reach
Postgres at all (see governance/policies/systems_automation_governance.md,
Rule 1, for the full diagnostic trail). This connector sidesteps that
entirely by never touching Supavisor/raw Postgres connections -- it's
pure REST, same as everything else in this codebase.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from supabase import Client

from shared.scoped_db import get_scoped_client


def get_client() -> Client:
    return get_scoped_client("systems_agent")


# service_name values as actually written to circuit_breakers by
# reliability_monitor.py's DIVISION_PORTS + its n8n/ollama/supabase/
# fastapi_router checks -- confirmed live 2026-08-22 by querying the
# real table rather than assumed from the code.
_DIVISION_SERVICE_MAP = {
    "rii": "rii_server",
    "learning": "learning_server",
    "fixera": "fixera_server",
    "forex": "forex_server",
    "audit": "audit_server",
    # the Orchestrator totem has no monitored process of its own -- it
    # IS the routing layer, so fastapi_router is its real proxy rather
    # than a fabricated status.
    "orchestrator": "fastapi_router",
}


def get_empire_status() -> dict[str, Any]:
    """Real, live snapshot for the Empire Brain display -- every field
    here is a genuine read against circuit_breakers/audit_vault via the
    systems_agent scoped connector, never a placeholder. 'Systems' has
    no row of its own in circuit_breakers (it doesn't monitor itself),
    but a request reaching this function at all proves it's running, so
    it's reported healthy unconditionally rather than queried.

    Deliberately does not touch agent_registry -- systems_agent has no
    grant on it today (see infrastructure/database/migrations/
    0010_systems_agent_rls_jwt.sql, scoped to circuit_breakers/
    audit_vault only). circuit_breakers already carries a real liveness
    signal for every division server, which is what this display
    actually needs, so no new migration/grant was required for this
    first real slice."""
    client = get_client()

    breakers = client.table("circuit_breakers").select("service_name,state,failure_count").execute().data
    by_service = {row["service_name"]: row for row in breakers}

    divisions = {}
    for division, service_name in _DIVISION_SERVICE_MAP.items():
        row = by_service.get(service_name)
        divisions[division] = row["state"] if row else "unknown"
    divisions["systems"] = "healthy"

    monitored_services = list(_DIVISION_SERVICE_MAP.values()) + ["n8n", "ollama", "supabase"]
    services_online = sum(1 for name in monitored_services if by_service.get(name, {}).get("state") == "healthy")
    alerts = sum(1 for name in monitored_services if by_service.get(name, {}).get("state", "healthy") != "healthy")

    since = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    recent = client.table("audit_vault").select("id", count="exact").gte("created_at", since).execute()

    return {
        "divisions": divisions,
        "services_online": services_online,
        "services_total": len(monitored_services) + 1,  # +1 for systems itself
        "alerts": alerts,
        "recent_activity_1h": recent.count or 0,
    }


_ALLOWED_CIRCUIT_BREAKER_FIELDS = {
    "state",
    "failure_count",
    "last_failure_at",
    "last_success_at",
    "opened_at",
    "metadata",
}


def get_circuit_breaker(service_name: str) -> dict[str, Any] | None:
    result = get_client().table("circuit_breakers").select("*").eq("service_name", service_name).execute()
    return result.data[0] if result.data else None


def create_circuit_breaker(service_name: str, auto_restart_permitted: bool) -> dict[str, Any]:
    result = (
        get_client()
        .table("circuit_breakers")
        .insert(
            {
                "service_name": service_name,
                "state": "healthy",
                "failure_count": 0,
                "auto_restart_permitted": auto_restart_permitted,
                "metadata": {},
            }
        )
        .execute()
    )
    return result.data[0]


def update_circuit_breaker(service_name: str, updates: dict[str, Any]) -> None:
    """updates keys must be a subset of _ALLOWED_CIRCUIT_BREAKER_FIELDS --
    deliberately not a raw passthrough, so a caller can't accidentally
    write to service_name or auto_restart_permitted after creation."""
    unknown = set(updates) - _ALLOWED_CIRCUIT_BREAKER_FIELDS
    if unknown:
        raise ValueError(f"Unknown circuit_breakers field(s): {sorted(unknown)}")
    if not updates:
        return

    get_client().table("circuit_breakers").update(updates).eq("service_name", service_name).execute()


def write_audit_vault(
    *,
    agent_id: str,
    division: str,
    action: str,
    outcome: str,
    data_classification: str,
    law_reference: str | None = None,
    metadata: dict | None = None,
) -> None:
    get_client().table("audit_vault").insert(
        {
            "agent_id": agent_id,
            "division": division,
            "action": action,
            "outcome": outcome,
            "data_classification": data_classification,
            "law_reference": law_reference,
            "metadata": metadata or {},
        }
    ).execute()
