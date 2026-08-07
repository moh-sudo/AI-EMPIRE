from shared.db import get_client
from shared.memory.embeddings import generate_embedding


def add_experience(
    *,
    division: str,
    event_type: str,
    context: str,
    agent_id: str | None = None,
    outcome: str | None = None,
    metadata: dict | None = None,
    embedding: list[float] | None = None,
) -> dict:
    if embedding is None:
        embedding = generate_embedding(context)

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
                "embedding": embedding,
            }
        )
        .execute()
    )
    return result.data[0]


def search_experience(
    *,
    query: str,
    match_count: int = 5,
    division: str | None = None,
    query_embedding: list[float] | None = None,
) -> list[dict]:
    if query_embedding is None:
        query_embedding = generate_embedding(query)

    result = (
        get_client()
        .rpc(
            "match_memory_experience",
            {
                "query_embedding": query_embedding,
                "match_count": match_count,
                "filter_division": division,
            },
        )
        .execute()
    )
    return result.data
