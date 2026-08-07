"""Scoped connector to AI_EMPIRE's own database for Systems & Automation
Division agents -- Reliability & Monitoring's equivalent of
shared/fixera_connector.py.

Uses the same Supabase REST API transport as shared/db.py's
get_client() (supabase-py's create_client() -- the same mechanism
every agent in every division already uses successfully, never had a
connection issue), but signs its own narrowly-scoped JWT instead of
using SUPABASE_SERVICE_KEY. That JWT carries a custom 'app_role':
'systems_agent' claim, and RLS policies on circuit_breakers/audit_vault
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

import os
import time
from typing import Any

import jwt
from supabase import Client, create_client

_client: Client | None = None
_JWT_LIFETIME_SECONDS = 10 * 365 * 24 * 60 * 60  # 10 years -- a service credential, not a user session


def _mint_scoped_jwt() -> str:
    secret = os.environ["SUPABASE_JWT_SECRET"]
    now = int(time.time())
    payload = {
        "role": "authenticated",
        "app_role": "systems_agent",
        "iat": now,
        "exp": now + _JWT_LIFETIME_SECONDS,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def get_client() -> Client:
    """Two-token pattern, required by Supabase's gateway (Kong): the
    'apikey' header must be one of the project's real, known API keys
    (the public-safe anon key here) for the request to even reach
    PostgREST at all -- a custom-signed JWT there gets rejected outright
    with 'Invalid API key' before PostgREST ever evaluates it. The
    scoped JWT (carrying 'app_role': 'systems_agent') goes in a
    *separate* Authorization bearer, set via postgrest.auth() after
    client creation -- that's the one PostgREST actually decodes for
    RLS's auth.jwt() claims. Found live 2026-08-06 after the client
    initially used the same custom JWT for both headers and got
    rejected at the gateway layer."""
    global _client
    if _client is None:
        url = os.environ["SUPABASE_URL"]
        anon_key = os.environ["SUPABASE_ANON_KEY"]
        _client = create_client(url, anon_key)
        _client.postgrest.auth(_mint_scoped_jwt())
    return _client


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
