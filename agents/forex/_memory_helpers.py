"""Shared memory-write helpers for Forex Division agents.

Wraps shared.memory.experience/knowledge's add_experience/add_knowledge
with a graceful fallback for when embedding generation isn't available
-- the record is still written with a NULL embedding rather than
failing outright, so real data starts accumulating immediately.
Semantic search (match_memory_experience / match_memory_knowledge)
simply won't surface NULL-embedding rows until a real, working key is
in place and existing rows are backfilled.

2026-07-26 fix: originally only caught RuntimeError, which is what
shared.memory.embeddings.generate_embedding() raises when
OPENAI_API_KEY is still a placeholder. Once a real key was added, a
quota/billing failure surfaces as openai.APIError (RateLimitError is a
subclass) instead -- a completely different exception type the
original except clause didn't catch, so every memory write silently
crashed instead of falling back. Caught live: a real Telegram briefing
request (2026-07-26 morning) hit this exact path and never got a
reply. Now catches both -- "real embeddings aren't available right
now, for any reason" was always the intent, this just makes it
actually true for a real-but-rate-limited key, not just a placeholder.
"""

from openai import APIError

from shared.scoped_db import get_scoped_client


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

    client = get_scoped_client("forex_agent")
    try:
        return add_experience(
            division=division,
            event_type=event_type,
            context=context,
            agent_id=agent_id,
            outcome=outcome,
            metadata=metadata,
            client=client,
        )
    except (RuntimeError, APIError):
        result = (
            client.table("memory_experience")
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

    client = get_scoped_client("forex_agent")
    try:
        return add_knowledge(
            division=division,
            content=content,
            agent_id=agent_id,
            source=source,
            metadata=metadata,
            client=client,
        )
    except (RuntimeError, APIError):
        result = (
            client.table("memory_knowledge")
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
