"""Shared memory-write helpers for Learning Division agents.

Mirrors every other division's _memory_helpers.py exactly --
deliberately duplicated, not cross-imported.
"""

from openai import APIError

from shared.scoped_db import get_scoped_client

# Re-migrated to the scoped client 2026-08-18 -- the "pgvector + RLS"
# platform bug this was reverted for (2026-08-11) turned out to be a
# misdiagnosis. Real root cause, confirmed live: memory_experience/
# memory_knowledge had no SELECT policy for most divisions, and
# PostgREST's default insert behavior tries to SELECT the just-inserted
# row back to return it -- that implicit read is itself subject to RLS,
# so with no SELECT grant it always failed, surfacing as the same
# generic "violates row-level security policy" error a real WITH CHECK
# failure would. Nothing to do with vector columns at all -- fixed by
# 0015_memory_knowledge_select_fix.sql (adds each division's own-row
# SELECT policy), not by working around the write path. See
# governance/policies/systems_automation_governance.md's Rule 1/pgvector
# entries for the full history.


def _client():
    return get_scoped_client("learning_agent")


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
            client=_client(),
        )
    except (RuntimeError, APIError):
        result = (
            _client()
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
            client=_client(),
        )
    except (RuntimeError, APIError):
        result = (
            _client()
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
