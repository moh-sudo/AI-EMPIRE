"""Content Transformation pipeline -- Learning Division.

Real ingestion from 5 real sources -- text paste, URL fetch, document
upload, YouTube transcript, voice note -- each normalizes its input
into plain text, fully deterministic, no model needed for any of
them. The final step (text -> flashcards) uses Ollama, per Mohamed's
explicit choice (2026-08-02) to connect it now rather than stub it,
since it's already proven working for the Fixera/Forex chat -- an
intentional exception to the general architecture-first default for
this specific division.

Voice note ingestion depends on shared/voice/speech_to_text.py, which
was stubbed when this file was first written but has run real
faster-whisper transcription in-process since 2026-08-10 (see
ARCHITECTURE.md) -- corrected here 2026-08-20 after confirming
extract_text_from_voice() below already calls the real transcribe(),
the docstring just hadn't caught up.
"""

import ipaddress
import re
import socket
from urllib.parse import urlparse


def _is_safe_url(url: str) -> bool:
    """SSRF guard -- rejects anything but http(s), and any URL whose
    hostname resolves to a private/loopback/link-local/reserved/
    multicast address. Added 2026-08-20 after a Red Team exercise
    confirmed extract_text_from_url() had zero validation and could
    reach internal-only endpoints (e.g. 127.0.0.1:8007/openapi.json)
    via this division's own Telegram URL: ingest command."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return False
    try:
        resolved = socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror:
        return False
    for _family, _type, _proto, _canonname, sockaddr in resolved:
        ip = ipaddress.ip_address(sockaddr[0])
        if ip.is_private or ip.is_reserved or ip.is_multicast:
            return False
    return True


def extract_text_from_url(url: str) -> dict:
    import trafilatura

    if not _is_safe_url(url):
        return {
            "ok": False,
            "reason": f"Refused to fetch {url}: unsupported scheme or resolves to a private/internal address.",
        }

    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return {"ok": False, "reason": f"Could not fetch {url}"}
        text = trafilatura.extract(downloaded)
        if not text:
            return {"ok": False, "reason": f"Could not extract readable article text from {url}"}
        return {"ok": True, "text": text}
    except Exception as e:
        return {"ok": False, "reason": str(e)}


def extract_text_from_pdf(file_path: str) -> dict:
    from pypdf import PdfReader

    try:
        reader = PdfReader(file_path)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        if not text.strip():
            return {"ok": False, "reason": "No extractable text found (PDF may be scanned/image-based)."}
        return {"ok": True, "text": text}
    except Exception as e:
        return {"ok": False, "reason": str(e)}


_YOUTUBE_ID_PATTERN = re.compile(r"(?:v=|youtu\.be/|embed/)([A-Za-z0-9_-]{11})")


def extract_text_from_youtube(url: str) -> dict:
    from youtube_transcript_api import YouTubeTranscriptApi

    match = _YOUTUBE_ID_PATTERN.search(url)
    if not match:
        return {"ok": False, "reason": f"Could not find a YouTube video ID in '{url}'"}
    video_id = match.group(1)
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        text = " ".join(entry["text"] for entry in transcript)
        return {"ok": True, "text": text}
    except Exception as e:
        return {"ok": False, "reason": str(e)}


def extract_text_from_voice(audio_path: str) -> dict:
    from shared.voice.speech_to_text import transcribe

    result = transcribe(audio_path)
    if not result.get("ok"):
        return {"ok": False, "reason": result["reason"]}
    return {"ok": True, "text": result["text"]}


FLASHCARD_GENERATION_PROMPT = (
    "You are a study-flashcard generator. Given the text below, extract the "
    "most important facts/concepts and turn each into a question-and-answer "
    "flashcard pair. Respond with each card in exactly this format, nothing "
    "else:\nQ: <question>\nA: <answer>\n(repeat for each card, one blank "
    "line between cards). Generate between 3 and 10 cards depending on how "
    "much real content is in the text -- never pad with trivial or "
    "repetitive cards just to hit a number."
)


def _parse_flashcard_response(reply: str) -> list[dict]:
    cards = []
    current_q = None
    for line in reply.splitlines():
        line = line.strip()
        if line[:2].upper() == "Q:":
            current_q = line[2:].strip()
        elif line[:2].upper() == "A:" and current_q:
            cards.append({"front": current_q, "back": line[2:].strip()})
            current_q = None
    return cards


def generate_flashcards_from_text(text: str, max_chars: int = 6000) -> dict:
    from shared.models.ollama_client import chat as ollama_chat

    result = ollama_chat(text[:max_chars], system=FLASHCARD_GENERATION_PROMPT)
    if not result.get("ok"):
        return {"ok": False, "reason": result["reason"]}

    cards = _parse_flashcard_response(result["reply"])
    if not cards:
        return {
            "ok": False,
            "reason": "Model responded but no valid Q/A pairs could be parsed.",
            "raw_reply": result["reply"],
        }
    return {"ok": True, "cards": cards}


def ingest_and_generate(text: str, category: str, source_type: str, source_reference: str | None = None) -> dict:
    """Full pipeline: text -> Ollama flashcard generation -> real cards
    saved via the active learning engine (agents.learning.engine)."""
    generation = generate_flashcards_from_text(text)
    if not generation.get("ok"):
        return {"ok": False, "stage": "generation", "reason": generation["reason"]}

    from agents.learning.engine import get_learning_engine

    engine = get_learning_engine()
    created = [
        engine.add_card(category, c["front"], c["back"], source_type=source_type, source_reference=source_reference)
        for c in generation["cards"]
    ]
    return {"ok": True, "cards_created": len(created), "cards": created}
