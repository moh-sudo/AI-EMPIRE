"""Flexible, multi-provider chat/completion -- Ollama, OpenAI, or
Claude/Anthropic, selectable via a `provider` parameter or the
CHAT_PROVIDER env var (defaults to "ollama", Mohamed's primary
backend most of the time as of 2026-08-09). Generic shared infra,
not division-specific -- same fail-safe pattern as every other
external call in this project (send_telegram, the Fixera connector,
ollama_client.chat): never raises, always returns a dict with "ok".

Unlike shared/memory/embeddings.py's generate_embedding(), this does
NOT auto-fall-back across providers on failure -- different providers'
chat responses have real quality/behavior differences a caller should
control explicitly, not silently swap without knowing. If a provider
isn't configured or fails, that's reported back, not hidden behind a
different provider's answer.

ANTHROPIC_API_KEY is a placeholder (REPLACE_ME) in .env as of
2026-08-09 -- the "anthropic" option is real and ready, but reports
itself unconfigured until a real key is added.
"""

import os

_DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
_DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-5"


def _chat_ollama(prompt: str, system: str | None, model: str | None) -> dict:
    from shared.models.ollama_client import chat as ollama_chat

    return ollama_chat(prompt, system=system, model=model)


def _chat_openai(prompt: str, system: str | None, model: str | None) -> dict:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key or api_key == "REPLACE_ME":
        return {"ok": False, "reason": "OPENAI_API_KEY not configured in .env yet."}

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = client.chat.completions.create(model=model or _DEFAULT_OPENAI_MODEL, messages=messages)
        reply = response.choices[0].message.content
        if not reply:
            return {"ok": False, "reason": "OpenAI returned no content."}
        return {"ok": True, "reply": reply}
    except Exception as e:
        return {"ok": False, "reason": str(e)}


def _chat_anthropic(prompt: str, system: str | None, model: str | None) -> dict:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key or api_key == "REPLACE_ME":
        return {"ok": False, "reason": "ANTHROPIC_API_KEY not configured in .env yet."}

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=model or _DEFAULT_ANTHROPIC_MODEL,
            max_tokens=2048,
            system=system or anthropic.NOT_GIVEN,
            messages=[{"role": "user", "content": prompt}],
        )
        reply = response.content[0].text if response.content else ""
        if not reply:
            return {"ok": False, "reason": "Claude returned no content."}
        return {"ok": True, "reply": reply}
    except Exception as e:
        return {"ok": False, "reason": str(e)}


_PROVIDERS = {"ollama": _chat_ollama, "openai": _chat_openai, "anthropic": _chat_anthropic}


def chat(prompt: str, system: str | None = None, provider: str | None = None, model: str | None = None) -> dict:
    """provider: "ollama" | "openai" | "anthropic". Defaults to
    CHAT_PROVIDER env var, then "ollama" if that's unset too."""
    provider = (provider or os.environ.get("CHAT_PROVIDER", "ollama")).lower()
    chat_fn = _PROVIDERS.get(provider)
    if chat_fn is None:
        return {"ok": False, "reason": f"Unknown provider '{provider}'. Choose from: {sorted(_PROVIDERS)}"}
    return chat_fn(prompt, system, model)
