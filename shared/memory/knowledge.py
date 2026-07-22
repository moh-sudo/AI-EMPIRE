from typing import Optional

from shared.db import get_client
from shared.memory.embeddings import generate_embedding


def add_knowledge(
    *,
    division: str,
    content: str,
    agent_id: Optional[str] = None,
    source: Optional[str] = None,
    metadata: Optional[dict] = None,
    embedding: Optional[list[float]] = None,
) -> dict:
    """embedding is optional so callers/tests can skip the OpenAI call and
    still exercise the DB round-trip; production callers should omit it
    and let this function generate one."""
    if embedding is None:
        embedding = generate_embedding(content)

    result = (
        get_client()
        .table("memory_knowledge")
        .insert({
            "division": division,
            "agent_id": agent_id,
            "content": content,
            "source": source,
            "metadata": metadata,
            "embedding": embedding,
        })
        .execute()
    )
    return result.data[0]


def search_knowledge(
    *,
    query: str,
    match_count: int = 5,
    division: Optional[str] = None,
    query_embedding: Optional[list[float]] = None,
) -> list[dict]:
    if query_embedding is None:
        query_embedding = generate_embedding(query)

    result = get_client().rpc(
        "match_memory_knowledge",
        {
            "query_embedding": query_embedding,
            "match_count": match_count,
            "filter_division": division,
        },
    ).execute()
    return result.data


def delete_knowledge(knowledge_id: str) -> None:
    get_client().table("memory_knowledge").delete().eq("id", knowledge_id).execute()
