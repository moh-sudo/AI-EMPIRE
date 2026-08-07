from shared.db import get_client


def set_identity(*, agent_id: str, division: str, key: str, value: dict) -> dict:
    result = (
        get_client()
        .table("memory_identity")
        .upsert(
            {"agent_id": agent_id, "division": division, "key": key, "value": value},
            on_conflict="agent_id,key",
        )
        .execute()
    )
    return result.data[0]


def get_identity(*, agent_id: str, key: str) -> dict | None:
    result = (
        get_client().table("memory_identity").select("*").eq("agent_id", agent_id).eq("key", key).limit(1).execute()
    )
    return result.data[0] if result.data else None


def get_all_identity(agent_id: str) -> list[dict]:
    result = get_client().table("memory_identity").select("*").eq("agent_id", agent_id).execute()
    return result.data
