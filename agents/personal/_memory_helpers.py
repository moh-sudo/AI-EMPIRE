"""Shared memory-write helpers for Personal Division agents.

Mirrors agents/fixera/_memory_helpers.py and agents/forex/_memory_helpers.py
exactly -- deliberately duplicated, not cross-imported, same
division-separation principle as _telegram.py.
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
# governance/policies/systems_automation_governance.md's Rule 1.


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
