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

from typing import Optional

from openai import APIError

from shared.db import get_client


def safe_add_experience(
    *,
    division: str,
    event_type: str,
    context: str,
    agent_id: Optional[str] = None,
    outcome: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> dict:
    from shared.memory.experience import add_experience

    try:
        return add_experience(
            division=division, event_type=event_type, context=context,
            agent_id=agent_id, outcome=outcome, metadata=metadata,
        )
    except (RuntimeError, APIError):
        result = (
            get_client()
            .table("memory_experience")
            .insert({
                "division": division, "agent_id": agent_id, "event_type": event_type,
                "context": context, "outcome": outcome, "metadata": metadata,
                "embedding": None,
            })
            .execute()
        )
        return result.data[0]


def safe_add_knowledge(
    *,
    division: str,
    content: str,
    agent_id: Optional[str] = None,
    source: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> dict:
    from shared.memory.knowledge import add_knowledge

    try:
        return add_knowledge(
            division=division, content=content, agent_id=agent_id,
            source=source, metadata=metadata,
        )
    except (RuntimeError, APIError):
        result = (
            get_client()
            .table("memory_knowledge")
            .insert({
                "division": division, "agent_id": agent_id, "content": content,
                "source": source, "metadata": metadata, "embedding": None,
            })
            .execute()
        )
        return result.data[0]
