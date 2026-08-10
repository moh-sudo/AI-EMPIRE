"""Obsidian write-integration -- the general knowledge/notes layer.

Obsidian itself is just a markdown-file viewer/editor over a folder --
"the vault" is nothing more than that folder. Writing a note here
requires no Obsidian installation, no API, no running process; it's
real the moment the file exists on disk, and Obsidian picks it up
next time it's opened. This module is the single, clearly-marked
place that writes into the vault, mirroring speech_to_text.py's and
text_to_speech.py's role as the single connection points for their
own concerns.

Vault location is configurable via OBSIDIAN_VAULT_PATH (.env) rather
than hardcoded -- Mohamed didn't have a vault yet, so one was created
at a sensible default location, but the path is his to change.
"""

import os
import re
from datetime import datetime
from pathlib import Path


def _vault_path() -> Path:
    configured = os.environ.get("OBSIDIAN_VAULT_PATH")
    if configured:
        return Path(configured)
    return Path.home() / "Documents" / "AI_EMPIRE_Vault"


def _slugify(text: str, max_words: int = 6) -> str:
    words = re.findall(r"[A-Za-z0-9]+", text)[:max_words]
    return "-".join(words) if words else "note"


def write_note(text: str, source_type: str = "voice", source_reference: str | None = None) -> dict:
    """Writes a single note into the vault's Inbox/ folder -- one file
    per capture, for Mohamed to file/link later, matching how most
    Obsidian quick-capture workflows work. Never raises -- same
    fail-closed principle as every other external call in this
    project."""
    if not text.strip():
        return {"ok": False, "reason": "No text to write."}

    inbox = _vault_path() / "Inbox"
    try:
        inbox.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        return {"ok": False, "reason": f"Could not create/access vault Inbox: {e}"}

    now = datetime.now()
    filename = f"{now.strftime('%Y-%m-%d %H-%M-%S')} {_slugify(text)}.md"
    note_path = inbox / filename

    frontmatter = (
        "---\n"
        f"created: {now.isoformat(timespec='seconds')}\n"
        f"source_type: {source_type}\n"
        f"source_reference: {source_reference or ''}\n"
        "---\n\n"
    )

    try:
        note_path.write_text(frontmatter + text.strip() + "\n", encoding="utf-8")
    except OSError as e:
        return {"ok": False, "reason": f"Could not write note: {e}"}

    return {"ok": True, "path": str(note_path)}
