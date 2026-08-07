"""Ollama chat client -- generic shared infra, not division-specific.

Talks to a locally-hosted Ollama server (currently Mohamed's M1
MacBook, reachable over LAN at OLLAMA_BASE_URL) via its native
/api/chat endpoint. Existing for text generation only -- no vision,
no embeddings (both need separate handling; see the 2026-07-30 session
notes on why 8GB unified memory makes vision impractical here).

Fail-safe like every other external call in this project
(send_telegram, the Fixera connector, etc.): never raises, always
returns a dict with "ok".

Known limitation, not hidden: OLLAMA_BASE_URL is a LAN IP the Mac gets
from DHCP -- it can change if the Mac reconnects to Wi-Fi. Update the
.env value if chat calls start failing with a connection error.
"""

import os

import requests

DEFAULT_TIMEOUT = 60  # local 3B model on 8GB M1 -- generous but not unbounded


def chat(prompt: str, system: str | None = None, model: str | None = None) -> dict:
    base_url = os.environ.get("OLLAMA_BASE_URL")
    if not base_url:
        return {"ok": False, "reason": "OLLAMA_BASE_URL not configured in .env yet."}

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    try:
        resp = requests.post(
            f"{base_url.rstrip('/')}/api/chat",
            json={
                "model": model or os.environ.get("OLLAMA_MODEL", "llama3.2:3b"),
                "messages": messages,
                "stream": False,
            },
            timeout=DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        reply = data.get("message", {}).get("content", "")
        if not reply:
            return {"ok": False, "reason": f"Ollama returned no content: {data}"}
        return {"ok": True, "reply": reply}
    except requests.RequestException as e:
        return {"ok": False, "reason": str(e)}
