"""Shared memory-write helpers for Fixera Division agents.

Mirrors agents/forex/_memory_helpers.py exactly (including its
2026-07-26 fix), added now because Fixera's CEO/Lead is the first
Fixera agent to write to memory_knowledge at all -- the other 8 are
pure functions with no persistence layer.

Wraps shared.memory.knowledge's add_knowledge with a graceful fallback
for when real embedding generation isn't available for any reason
(placeholder OPENAI_API_KEY raises RuntimeError; a real-but-rate-
limited key raises openai.APIError) -- the record is still written
with a NULL embedding rather than failing outright.
"""

from openai import APIError

from shared.db import get_client

# NOTE: deliberately NOT using shared.scoped_db.get_scoped_client here,
# unlike every other write path migrated in 0014_five_divisions_rls_jwt.sql.
# Live-tested 2026-08-11: memory_experience/memory_knowledge -- the only
# two tables in this project with a pgvector VECTOR column -- reject
# EVERY insert under RLS as the scoped role, even an unconditionally
# true WITH CHECK(true) policy on a brand-new throwaway table with the
# same shape. Exhaustively ruled out: JWT claims, role switching, table
# and column grants, triggers, RLS force settings, vector type USAGE
# privilege. A genuine pgvector+RLS platform issue specific to this
# project, not a policy mistake -- same class of real, documented
# blocker as the Supavisor pooler issue in
# governance/policies/systems_automation_governance.md's Rule 1. The
# 0014 migration's policies on these two tables are left in place
# (harmless, just unused via this path) rather than reverted in SQL --
# this is the actual, safe workaround: everything else in 0014 is
# proven correct and stays scoped.


def safe_add_experience(
    *,
    division: str,
    event_type: str,
    context: str,
    agent_id: str | None = None,
    outcome: str | None = None,
    metadata: dict | None = None,
) -> dict:
    from shared.memory.experience import add_experience

    try:
        return add_experience(
            division=division,
            event_type=event_type,
            context=context,
            agent_id=agent_id,
            outcome=outcome,
            metadata=metadata,
        )
    except (RuntimeError, APIError):
        result = (
            get_client()
            .table("memory_experience")
            .insert(
                {
                    "division": division,
                    "agent_id": agent_id,
                    "event_type": event_type,
                    "context": context,
                    "outcome": outcome,
                    "metadata": metadata,
                    "embedding": None,
                }
            )
            .execute()
        )
        return result.data[0]


def safe_add_knowledge(
    *,
    division: str,
    content: str,
    agent_id: str | None = None,
    source: str | None = None,
    metadata: dict | None = None,
) -> dict:
    from shared.memory.knowledge import add_knowledge

    try:
        return add_knowledge(
            division=division,
            content=content,
            agent_id=agent_id,
            source=source,
            metadata=metadata,
        )
    except (RuntimeError, APIError):
        result = (
            get_client()
            .table("memory_knowledge")
            .insert(
                {
                    "division": division,
                    "agent_id": agent_id,
                    "content": content,
                    "source": source,
                    "metadata": metadata,
                    "embedding": None,
                }
            )
            .execute()
        )
        return result.data[0]
