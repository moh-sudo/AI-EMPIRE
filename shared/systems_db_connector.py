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

from typing import Any

from supabase import Client

from shared.scoped_db import get_scoped_client


def get_client() -> Client:
    return get_scoped_client("systems_agent")


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
