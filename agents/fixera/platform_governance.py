"""Platform Governance Agent v0.1 — Fixera Division.

System behavior integrity per the Execution Truth Principle: "the
authoritative behavior of the platform is defined by the executing
code path and runtime -- not merely by configuration, schema, or
documentation. Verify before relying." This agent's job is drift
detection between what's documented/configured and what's actually
running.

Findings are reported, never auto-fixed -- per the "Fixera
Relationship" model, fixes to Fixera's own schema/code happen in
C:\\fixera directly, never applied by an AI_EMPIRE agent.
"""

from dataclasses import dataclass


@dataclass
class DriftFinding:
    kind: str  # "missing_column" | "missing_trigger" | "missing_table" | "missing_view"
    target: str
    documented_in: str
    detail: str


def check_column_drift(
    table_name: str,
    documented_columns: dict[str, str],
    actual_columns: set[str],
    documented_in: str,
) -> list[DriftFinding]:
    """documented_columns maps column_name -> where it's documented (a
    file/migration reference), so findings point back to the source of
    the stale claim."""
    findings = []
    for column, source in documented_columns.items():
        if column not in actual_columns:
            findings.append(DriftFinding(
                "missing_column", f"{table_name}.{column}", source,
                f"documented in {source} but not present in {table_name}",
            ))
    return findings


def check_trigger_drift(
    table_name: str,
    documented_triggers: dict[str, str],
    actual_triggers: set[str],
) -> list[DriftFinding]:
    findings = []
    for trigger, source in documented_triggers.items():
        if trigger not in actual_triggers:
            findings.append(DriftFinding(
                "missing_trigger", f"{table_name}.{trigger}", source,
                f"documented in {source} but no such trigger exists on {table_name}",
            ))
    return findings


def check_view_drift(documented_views: dict[str, str], actual_views: set[str]) -> list[DriftFinding]:
    findings = []
    for view, source in documented_views.items():
        if view not in actual_views:
            findings.append(DriftFinding(
                "missing_view", view, source,
                f"documented in {source} but view does not exist",
            ))
    return findings
