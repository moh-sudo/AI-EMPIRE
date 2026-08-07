import os

_openai_client = None

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536


def _get_openai_client():
    global _openai_client
    if _openai_client is None:
        from openai import OpenAI

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key or api_key == "REPLACE_ME":
            raise RuntimeError("OPENAI_API_KEY not configured")
        _openai_client = OpenAI(api_key=api_key)
    return _openai_client


def generate_embedding(text: str) -> list[float]:
    client = _get_openai_client()
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=text)
    return response.data[0].embedding
