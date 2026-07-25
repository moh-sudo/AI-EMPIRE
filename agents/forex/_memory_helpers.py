"""Shared memory-write helpers for Forex Division agents.

Wraps shared.memory.experience/knowledge's add_experience/add_knowledge
with a graceful fallback for when OPENAI_API_KEY is still a placeholder
(true as of this writing) -- in that case the record is still written
with a NULL embedding rather than failing outright, so real data starts
accumulating immediately. Semantic search (match_memory_experience /
match_memory_knowledge) simply won't surface NULL-embedding rows until
a real key is added and existing rows are backfilled; nothing about
this helper needs to change once that happens -- callers just start
getting real embeddings automatically.
"""

from typing import Optional

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
    except RuntimeError:
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
    except RuntimeError:
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
