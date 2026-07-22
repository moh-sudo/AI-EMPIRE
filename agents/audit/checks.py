"""The 4 anomaly checks from CONTEXT.md / Implementation Roadmap 3.1,
mapped onto the actual schema (routing_logs has no explicit error/status
column — blocked routing attempts are logged to audit_vault instead, so
"error rate in routing_logs" is defined as blocked-attempts / total-attempts).
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from shared.db import get_client

SEVERITY_CRITICAL = "Critical"
SEVERITY_HIGH = "High"
SEVERITY_MEDIUM = "Medium"

CLOUD_RISK_CLASSIFICATIONS = ("CONFIDENTIAL", "RESTRICTED", "SECRET")


@dataclass
class Finding:
    check: str
    severity: str
    count: int
    details: list[dict[str, Any]] = field(default_factory=list)

    @property
    def triggered(self) -> bool:
        return self.count > 0


def _since_24h_iso() -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()


def check_error_rate() -> Finding:
    """>20% error rate in routing_logs (last 24h). 'Error' = a blocked
    routing attempt (logged to audit_vault, action='route_request',
    outcome='blocked') as a share of all attempts (blocked + successful)."""
    since = _since_24h_iso()
    client = get_client()

    success_count = (
        client.table("routing_logs")
        .select("id", count="exact")
        .gte("created_at", since)
        .execute()
        .count
        or 0
    )
    blocked_result = (
        client.table("audit_vault")
        .select("id,agent_id,division,metadata,created_at", count="exact")
        .eq("action", "route_request")
        .eq("outcome", "blocked")
        .gte("created_at", since)
        .execute()
    )
    blocked_count = blocked_result.count or 0
    total = success_count + blocked_count
    rate = (blocked_count / total) if total else 0.0

    triggered = total > 0 and rate > 0.20
    return Finding(
        check="error_rate_24h",
        severity=SEVERITY_HIGH,
        count=(1 if triggered else 0),
        details=[{
            "blocked_count": blocked_count,
            "success_count": success_count,
            "error_rate": round(rate, 4),
            "threshold": 0.20,
            "sample_blocked": blocked_result.data[:5],
        }] if triggered else [],
    )


def check_unsanitized_cloud_routing() -> Finding:
    """Any routing_destination='cloud' where sanitization_status='none'
    AND data_classification is CONFIDENTIAL or higher. This is a direct
    Law 6 / Presidio-failure violation — Critical."""
    result = (
        get_client()
        .table("routing_logs")
        .select("*")
        .eq("routing_destination", "cloud")
        .eq("sanitization_status", "none")
        .in_("data_classification", list(CLOUD_RISK_CLASSIFICATIONS))
        .execute()
    )
    rows = result.data
    return Finding(
        check="unsanitized_cloud_routing",
        severity=SEVERITY_CRITICAL,
        count=len(rows),
        details=rows,
    )


def check_stale_agent_reviews() -> Finding:
    """Any active agent_registry record with next_review in the past."""
    now = datetime.now(timezone.utc).isoformat()
    result = (
        get_client()
        .table("agent_registry")
        .select("agent_id,agent_name,division,next_review,status")
        .eq("status", "active")
        .lt("next_review", now)
        .execute()
    )
    rows = result.data
    return Finding(
        check="stale_agent_reviews",
        severity=SEVERITY_MEDIUM,
        count=len(rows),
        details=rows,
    )


def check_missing_audit_fields() -> Finding:
    """Any routing_logs record (last 24h) missing capability_matched or
    cost_usd (budget_impact) — the two nullable fields among the 6
    required routing_logs fields."""
    since = _since_24h_iso()
    result = (
        get_client()
        .table("routing_logs")
        .select("*")
        .gte("created_at", since)
        .or_("capability_matched.is.null,cost_usd.is.null")
        .execute()
    )
    rows = result.data
    return Finding(
        check="missing_audit_fields",
        severity=SEVERITY_MEDIUM,
        count=len(rows),
        details=rows,
    )


def run_all_checks() -> list[Finding]:
    return [
        check_error_rate(),
        check_unsanitized_cloud_routing(),
        check_stale_agent_reviews(),
        check_missing_audit_fields(),
    ]
