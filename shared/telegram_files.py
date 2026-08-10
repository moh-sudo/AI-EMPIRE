"""Telegram file download -- generic shared infra, not division-specific.

Every division's bot that handles a voice note, PDF, or other upload
needs the same two calls: Telegram delivers a file_id, not raw bytes,
so getFile() resolves that to a path, then a second request fetches
the actual content. Unlike _telegram.py/telegram_listener.py
(deliberately duplicated per division since they carry real
division-specific logic), this function has none -- it's the same
two Telegram API calls regardless of which bot is asking, so it lives
here once instead of being copy-pasted into every division.
"""

from pathlib import Path

import requests


def download_telegram_file(token: str, file_id: str, suffix: str, downloads_dir: Path) -> str | None:
    """Real download -- Telegram's getFile + file-content endpoints.
    Returns a local path, or None on failure."""
    try:
        resp = requests.get(f"https://api.telegram.org/bot{token}/getFile", params={"file_id": file_id}, timeout=15)
        resp.raise_for_status()
        file_path = resp.json()["result"]["file_path"]

        downloads_dir.mkdir(exist_ok=True)
        local_path = downloads_dir / f"{file_id}{suffix}"
        file_resp = requests.get(f"https://api.telegram.org/file/bot{token}/{file_path}", timeout=30)
        file_resp.raise_for_status()
        local_path.write_bytes(file_resp.content)
        return str(local_path)
    except (requests.RequestException, KeyError):
        return None
