import os
from typing import Optional

from supabase import Client, create_client

_client: Optional[Client] = None


def get_client() -> Client:
    global _client
    if _client is None:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_KEY")
        if not url or not key:
            raise RuntimeError("SUPABASE_URL / SUPABASE_SERVICE_KEY not configured")
        _client = create_client(url, key)
    return _client


def log_routing_decision(
    *,
    prompt_hash: str,
    data_classification: str,
    routing_destination: str,
    sanitization_status: str,
    model_identifier: str,
    capability_matched: Optional[str],
    budget_impact: float,
    division: Optional[str],
    agent_id: Optional[str],
    latency_ms: int,
) -> None:
    # budget_impact maps to the routing_logs.cost_usd column — CONTEXT.md's
    # required-fields list names it "budget_impact" but the migration's
    # column is cost_usd; this is the single mapping point for that.
    get_client().table("routing_logs").insert({
        "prompt_hash": prompt_hash,
        "data_classification": data_classification,
        "routing_destination": routing_destination,
        "sanitization_status": sanitization_status,
        "model_identifier": model_identifier,
        "capability_matched": capability_matched,
        "cost_usd": budget_impact,
        "division": division,
        "agent_id": agent_id,
        "latency_ms": latency_ms,
    }).execute()


def log_audit_incident(
    *,
    agent_id: Optional[str],
    division: Optional[str],
    action: str,
    outcome: str,
    data_classification: str,
    severity: int,
    reason: str,
) -> None:
    get_client().table("audit_vault").insert({
        "agent_id": agent_id or "api_gateway",
        "division": division or "systems",
        "action": action,
        "outcome": outcome,
        "data_classification": data_classification,
        "law_reference": "Law 9" if severity >= 2 else None,
        "metadata": {"severity": severity, "reason": reason},
    }).execute()
