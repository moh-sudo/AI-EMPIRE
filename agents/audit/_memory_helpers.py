"""Shared memory-write helpers for Audit & Verification Division agents.

Mirrors every other division's _memory_helpers.py exactly --
deliberately duplicated, not cross-imported.
"""

from openai import APIError

from shared.db import get_client


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
