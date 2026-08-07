from shared.db import get_client


def register_model(
    *,
    model_identifier: str,
    provider: str,
    model_class: str,
    context_window: int | None = None,
    cost_per_1k_input_usd: float = 0,
    cost_per_1k_output_usd: float = 0,
    metadata: dict | None = None,
) -> dict:
    result = (
        get_client()
        .table("model_registry")
        .upsert(
            {
                "model_identifier": model_identifier,
                "provider": provider,
                "model_class": model_class,
                "context_window": context_window,
                "cost_per_1k_input_usd": cost_per_1k_input_usd,
                "cost_per_1k_output_usd": cost_per_1k_output_usd,
                "metadata": metadata,
            },
            on_conflict="model_identifier",
        )
        .execute()
    )
    return result.data[0]


def get_model(model_identifier: str) -> dict | None:
    result = (
        get_client().table("model_registry").select("*").eq("model_identifier", model_identifier).limit(1).execute()
    )
    return result.data[0] if result.data else None


def list_active_models(provider: str | None = None) -> list[dict]:
    query = get_client().table("model_registry").select("*").eq("status", "active")
    if provider:
        query = query.eq("provider", provider)
    return query.execute().data
