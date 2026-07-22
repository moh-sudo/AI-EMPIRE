from typing import Optional

from shared.db import get_client


def log_incident(
    *,
    agent_id: Optional[str],
    division: Optional[str],
    action: str,
    outcome: str,
    severity: int,
    reason: str,
    data_classification: str = "INTERNAL",
) -> None:
    get_client().table("audit_vault").insert({
        "agent_id": agent_id or "system",
        "division": division or "systems",
        "action": action,
        "outcome": outcome,
        "data_classification": data_classification,
        "law_reference": "Law 9" if severity >= 2 else None,
        "metadata": {"severity": severity, "reason": reason},
    }).execute()
