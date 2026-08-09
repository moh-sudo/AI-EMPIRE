"""Flexible, multi-provider embeddings -- OpenAI and Ollama, configurable,
with automatic fallback. Mohamed's explicit request (2026-08-09): don't
hard-lock memory search to one provider.

Both providers write into the same 768-dimension vector column
(infrastructure/database/migrations/0011_flexible_embeddings_768.sql) --
OpenAI's text-embedding-3-small via its `dimensions=768` parameter (a
real, documented OpenAI feature, not truncation after the fact), Ollama's
via nomic-embed-text's native 768-dim output. Embeddings from different
providers are NOT semantically comparable to each other even though the
dimension matches -- EMBEDDING_PROVIDER picks the one *active* provider
for both writing and searching; switching providers later means old
embeddings should be regenerated, not mixed.
"""

import os

EMBEDDING_DIMENSIONS = 768
_OPENAI_MODEL = "text-embedding-3-small"
_OLLAMA_EMBED_MODEL = "nomic-embed-text"

_openai_client = None


def _get_openai_client():
    global _openai_client
    if _openai_client is None:
        from openai import OpenAI

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key or api_key == "REPLACE_ME":
            raise RuntimeError("OPENAI_API_KEY not configured")
        _openai_client = OpenAI(api_key=api_key)
    return _openai_client


def _generate_openai(text: str) -> list[float]:
    client = _get_openai_client()
    response = client.embeddings.create(model=_OPENAI_MODEL, input=text, dimensions=EMBEDDING_DIMENSIONS)
    return response.data[0].embedding


def _generate_ollama(text: str) -> list[float]:
    import requests

    base_url = os.environ.get("OLLAMA_BASE_URL")
    if not base_url:
        raise RuntimeError("OLLAMA_BASE_URL not configured")

    resp = requests.post(
        f"{base_url.rstrip('/')}/api/embed",
        json={"model": _OLLAMA_EMBED_MODEL, "input": text},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    embeddings = data.get("embeddings")
    if not embeddings:
        raise RuntimeError(f"Ollama returned no embedding: {data}")
    return embeddings[0]


_PROVIDERS = {"openai": _generate_openai, "ollama": _generate_ollama}
_FALLBACK_ORDER = ["openai", "ollama"]


def generate_embedding(text: str) -> list[float]:
    """EMBEDDING_PROVIDER in .env picks the provider to try first ("openai"
    or "ollama", defaults to "openai"); the other is tried as a fallback
    if the first fails. Raises RuntimeError only if every configured
    provider fails -- callers (safe_add_experience/safe_add_knowledge)
    already catch this and fall back to embedding=None, so a memory
    write is never blocked by an embedding failure."""
    preferred = os.environ.get("EMBEDDING_PROVIDER", "openai").lower()
    order = [preferred] + [p for p in _FALLBACK_ORDER if p != preferred]

    last_error = None
    for provider in order:
        generate_fn = _PROVIDERS.get(provider)
        if generate_fn is None:
            continue
        try:
            return generate_fn(text)
        except Exception as e:
            last_error = e
            continue

    raise RuntimeError(f"All embedding providers failed. Last error: {last_error}")
