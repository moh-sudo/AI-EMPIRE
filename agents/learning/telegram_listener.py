"""Telegram inbound listener -- Learning Division.

Own dedicated bot (TELEGRAM_LEARNING_BOT_TOKEN), matching every other
division's pattern.

Two jobs, both real:

1. Review sessions -- "REVIEW" starts/continues a session (shows the
   next due card's question), "SHOW" reveals its answer, "AGAIN"/
   "GOOD"/"EASY" rates it and automatically advances to the next due
   card. Session state (which card is currently shown, question-only
   vs answer-revealed) persists in a small local JSON file between
   polls, same pattern as every other stateful listener in this
   project.

2. Content ingestion, all 5 sources Mohamed asked for:
   - "PASTE <category>: <text>" -- raw text
   - "URL <category>: <url>" -- fetches and extracts article text
   - "VIDEO <category>: <url>" -- YouTube transcript
   - A Telegram document upload (PDF) with the category as the caption
   - A Telegram voice note with the category as the caption (still
     depends on shared/voice/speech_to_text.py, which IS stubbed --
     fails closed with an honest reason until that's connected)

Each ingested source goes through
agents.learning.content_transform.ingest_and_generate() (real Ollama
flashcard generation, per Mohamed's explicit choice 2026-08-02).
"""

import json
import os
import re
from pathlib import Path

import requests

STATE_FILE = Path(__file__).resolve().parent / ".telegram_offset.json"
SESSION_FILE = Path(__file__).resolve().parent / ".review_session.json"
DOWNLOADS_DIR = Path(__file__).resolve().parent / ".downloads"


def _read_last_update_id() -> int | None:
    if not STATE_FILE.exists():
        return None
    try:
        return json.loads(STATE_FILE.read_text()).get("last_update_id")
    except (json.JSONDecodeError, OSError):
        return None


def _save_last_update_id(update_id: int) -> None:
    STATE_FILE.write_text(json.dumps({"last_update_id": update_id}))


def _read_session() -> dict:
    if not SESSION_FILE.exists():
        return {}
    try:
        return json.loads(SESSION_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _save_session(session: dict) -> None:
    SESSION_FILE.write_text(json.dumps(session))


def _download_telegram_file(token: str, file_id: str, suffix: str) -> str | None:
    """Real download -- Telegram's getFile + file-content endpoints.
    Returns a local path, or None on failure."""
    try:
        resp = requests.get(f"https://api.telegram.org/bot{token}/getFile", params={"file_id": file_id}, timeout=15)
        resp.raise_for_status()
        file_path = resp.json()["result"]["file_path"]

        DOWNLOADS_DIR.mkdir(exist_ok=True)
        local_path = DOWNLOADS_DIR / f"{file_id}{suffix}"
        file_resp = requests.get(f"https://api.telegram.org/file/bot{token}/{file_path}", timeout=30)
        file_resp.raise_for_status()
        local_path.write_bytes(file_resp.content)
        return str(local_path)
    except (requests.RequestException, KeyError):
        return None


def _start_or_continue_review() -> str:
    from agents.learning.engine import get_learning_engine

    due = get_learning_engine().get_due_cards(limit=1)
    if not due:
        _save_session({})
        return "No cards due for review right now. Nice work staying on top of it."

    card = due[0]
    _save_session({"card_id": card["id"], "front": card["front"], "back": card["back"], "answer_shown": False})
    return f'[{card["category"]}]\nQ: {card["front"]}\n\nReply "SHOW" to see the answer.'


def _handle_show() -> str:
    session = _read_session()
    if not session or "card_id" not in session:
        return 'No card currently in review. Reply "REVIEW" to start.'
    session["answer_shown"] = True
    _save_session(session)
    return f"A: {session['back']}\n\nReply AGAIN / GOOD / EASY."


def _handle_rating(rating: str) -> str:
    from agents.learning.engine import get_learning_engine

    session = _read_session()
    if not session or "card_id" not in session:
        return 'No card currently in review. Reply "REVIEW" to start.'
    if not session.get("answer_shown"):
        return 'Reply "SHOW" first to see the answer before rating.'

    result = get_learning_engine().rate_card(session["card_id"], rating)
    if not result.get("ok"):
        return f"Couldn't rate that card: {result.get('reason')}"

    next_prompt = _start_or_continue_review()
    return f"Recorded. Next up:\n\n{next_prompt}"


_INGEST_PATTERN = re.compile(r"^(PASTE|URL|VIDEO)\s+([^:]+):\s*(.+)$", re.IGNORECASE | re.DOTALL)


def _handle_ingest_text_command(text: str) -> str | None:
    match = _INGEST_PATTERN.match(text.strip())
    if not match:
        return None

    kind, category, payload = match.group(1).upper(), match.group(2).strip(), match.group(3).strip()
    from agents.learning.content_transform import (
        extract_text_from_url,
        extract_text_from_youtube,
    )

    if kind == "PASTE":
        return _run_ingest(payload, category, "paste", None)
    if kind == "URL":
        extraction = extract_text_from_url(payload)
        if not extraction.get("ok"):
            return f"Couldn't fetch that URL: {extraction['reason']}"
        return _run_ingest(extraction["text"], category, "url", payload)
    if kind == "VIDEO":
        extraction = extract_text_from_youtube(payload)
        if not extraction.get("ok"):
            return f"Couldn't get that video's transcript: {extraction['reason']}"
        return _run_ingest(extraction["text"], category, "video", payload)
    return None


def _run_ingest(text: str, category: str, source_type: str, source_reference: str | None) -> str:
    from agents.learning.content_transform import ingest_and_generate

    result = ingest_and_generate(text, category, source_type, source_reference)
    if not result.get("ok"):
        return f"Couldn't generate flashcards: {result.get('reason')}"
    return f'Created {result["cards_created"]} flashcard(s) in category "{category}".'


def _handle_document(msg: dict, token: str) -> str | None:
    doc = msg.get("document")
    if not doc:
        return None
    category = (msg.get("caption") or "uncategorized").strip()
    local_path = _download_telegram_file(token, doc["file_id"], ".pdf")
    if not local_path:
        return "Couldn't download that document."

    from agents.learning.content_transform import extract_text_from_pdf

    extraction = extract_text_from_pdf(local_path)
    if not extraction.get("ok"):
        return f"Couldn't extract text from that document: {extraction['reason']}"
    return _run_ingest(extraction["text"], category, "document", doc.get("file_name"))


def _handle_voice(msg: dict, token: str) -> str | None:
    voice = msg.get("voice")
    if not voice:
        return None
    category = (msg.get("caption") or "uncategorized").strip()
    local_path = _download_telegram_file(token, voice["file_id"], ".ogg")
    if not local_path:
        return "Couldn't download that voice note."

    from agents.learning.content_transform import extract_text_from_voice

    extraction = extract_text_from_voice(local_path)
    if not extraction.get("ok"):
        return f"Couldn't process that voice note: {extraction['reason']}"
    return _run_ingest(extraction["text"], category, "voice", None)


def _handle_curriculum_status() -> str:
    from agents.learning.curriculum import start_current_subject

    result = start_current_subject()
    if not result.get("ok"):
        return result.get("reason", "Curriculum not available.")
    phase, subject = result["phase"], result["subject"]
    return (
        f"Phase {phase['phase_number']}: {phase['name']}\n"
        f"Goal: {phase['goal']}\n\n"
        f"Current subject: {subject['name']} ({subject['status']})\n\n"
        f'Paste real lesson material with "PASTE {subject["name"]}: <text>" (or URL/VIDEO) to build '
        f'flashcards for it. Reply "COMPLETE" when you\'ve mastered this subject to move to the next.'
    )


def _handle_complete_subject() -> str:
    from agents.learning.curriculum import mark_current_subject_complete

    result = mark_current_subject_complete()
    if not result.get("ok"):
        return result.get("reason", "Nothing to complete.")

    next_info = result.get("next", {})
    if not next_info.get("found"):
        return f'Completed "{result["completed_subject"]}" -- that was the last subject. Curriculum complete!'

    next_subject = next_info["subject"]
    return f'Completed "{result["completed_subject"]}". Next up: {next_subject["name"]}.'


def _handle_progress() -> str:
    from agents.learning.curriculum import get_progress_summary

    p = get_progress_summary()
    return (
        f"{p['completed_subjects']}/{p['total_subjects']} subjects complete ({p['percent_complete']}%)\n"
        f"Current phase: {p['current_phase'] or 'N/A'}\n"
        f"Current subject: {p['current_subject'] or 'N/A'}"
    )


def _handle_text(text: str) -> str:
    text_upper = text.strip().upper()
    if text_upper == "REVIEW":
        return _start_or_continue_review()
    if text_upper == "SHOW":
        return _handle_show()
    if text_upper in ("AGAIN", "GOOD", "EASY"):
        return _handle_rating(text_upper)
    if text_upper == "DUE":
        from agents.learning.engine import get_learning_engine

        return f"{get_learning_engine().get_due_count()} card(s) due for review."
    if text_upper == "CATEGORIES":
        from agents.learning.engine import get_learning_engine

        categories = get_learning_engine().list_categories()
        if not categories:
            return "No categories yet -- add some content first."
        lines = [f"  - {c['category']}: {c['total']} card(s), {c['due']} due" for c in categories]
        return "Categories:\n" + "\n".join(lines)
    if text_upper == "CURRICULUM":
        return _handle_curriculum_status()
    if text_upper == "COMPLETE":
        return _handle_complete_subject()
    if text_upper == "PROGRESS":
        return _handle_progress()

    ingest_reply = _handle_ingest_text_command(text)
    if ingest_reply is not None:
        return ingest_reply

    return (
        'Reply "REVIEW" to study due cards, "DUE" to check how many are due, "CATEGORIES" to see your '
        'topics, "CURRICULUM" for your current AI Empire University subject, "COMPLETE" to finish it and '
        'advance, "PROGRESS" for overall completion, or add content with "PASTE <category>: <text>", '
        '"URL <category>: <link>", "VIDEO <category>: <youtube link>", or upload a PDF/voice note with '
        "the category as the caption."
    )


def check_for_learning_requests() -> dict:
    """Polls Telegram's getUpdates once, advances the offset past every
    update seen. Never raises -- same fail-safe pattern as every other
    listener in this project."""
    token = os.environ.get("TELEGRAM_LEARNING_BOT_TOKEN")
    expected_chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not expected_chat_id:
        return {"checked": False, "reason": "TELEGRAM_LEARNING_BOT_TOKEN/TELEGRAM_CHAT_ID not configured."}

    last_update_id = _read_last_update_id()
    params = {"timeout": 0}
    if last_update_id is not None:
        params["offset"] = last_update_id + 1

    try:
        resp = requests.get(f"https://api.telegram.org/bot{token}/getUpdates", params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        return {"checked": False, "reason": str(e)}

    if not data.get("ok"):
        return {"checked": False, "reason": data.get("description", "unknown Telegram API error")}

    updates = data.get("result", [])
    if not updates:
        return {"checked": True, "new_messages": 0, "triggered": False}

    from agents.learning._telegram import send_telegram

    highest_update_id = last_update_id or 0
    action_results = []

    for update in updates:
        highest_update_id = max(highest_update_id, update["update_id"])
        msg = update.get("message")
        if not msg:
            continue
        chat_id = str(msg.get("chat", {}).get("id", ""))
        if chat_id != str(expected_chat_id):
            continue

        reply = None
        if msg.get("document"):
            reply = _handle_document(msg, token)
        elif msg.get("voice"):
            reply = _handle_voice(msg, token)
        else:
            text = (msg.get("text") or "").strip()
            if text:
                reply = _handle_text(text)

        if reply is not None:
            send_telegram(reply, token_env="TELEGRAM_LEARNING_BOT_TOKEN")
            action_results.append({"reply": reply})

    _save_last_update_id(highest_update_id)

    result = {"checked": True, "new_messages": len(updates), "triggered": bool(action_results)}
    if action_results:
        result["action_results"] = action_results
    return result
