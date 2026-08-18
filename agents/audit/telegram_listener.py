"""Telegram inbound listener -- Audit & Verification Division.

New (2026-08-03) -- the original 4 governance checks alert via email
only (see audit_agent.py); this bot is for the new real-time findings
(Security, Financial, Performance, Reports, Bug Detection) and for
Mohamed to acknowledge bug proposals.

Commands:
- "STATUS" -- on-demand full sweep across every new check, summarized
- "PROPOSAL <id> ACK" -- acknowledges a bug proposal (does not
  approve a fix -- there's no fix to approve yet in v0.1, this just
  confirms Mohamed has seen the diagnosis)
"""

import json
import os
import re
from pathlib import Path

import requests

STATE_FILE = Path(__file__).resolve().parent / ".telegram_offset.json"
DOWNLOADS_DIR = Path(__file__).resolve().parent / ".downloads"
_ACK_PATTERN = re.compile(r"^PROPOSAL\s+(\S+)\s+ACK$", re.IGNORECASE)


def _read_last_update_id() -> int | None:
    if not STATE_FILE.exists():
        return None
    try:
        return json.loads(STATE_FILE.read_text()).get("last_update_id")
    except (json.JSONDecodeError, OSError):
        return None


def _save_last_update_id(update_id: int) -> None:
    STATE_FILE.write_text(json.dumps({"last_update_id": update_id}))


def _handle_status() -> str:
    from agents.audit.financial_verification import run_financial_verification
    from agents.audit.performance_monitor import run_performance_check
    from agents.audit.report_verification import check_scheduled_reports_ran_today
    from agents.audit.security_audit import run_security_audit

    lines = ["[Audit & Verification -- on-demand status]"]

    security = run_security_audit()
    secret_count = len(security.get("secrets", {}).get("findings", []))
    history_count = len(security.get("git_history_secrets", {}).get("findings", []))
    lines.append(
        f"Security: {secret_count} potential hardcoded secret(s) (working tree), "
        f"{history_count} in git history, .env tracked by git: {security.get('env_tracking', {}).get('env_tracked_by_git', 'unknown')}"
    )

    financial = run_financial_verification()
    if financial.get("ok"):
        lines.append(f"Financial: {financial['checked']} payment(s) checked, {financial['flagged_count']} flagged")
    else:
        lines.append(f"Financial: unavailable ({financial.get('reason')})")

    reports = check_scheduled_reports_ran_today()
    if reports.get("ok"):
        missing = reports["missing_today"]
        lines.append(
            f"Reports: {len(missing)} missing today" + (f" -- {', '.join(missing)}" if missing else " -- all ran")
        )
    else:
        lines.append(f"Reports: unavailable ({reports.get('reason')})")

    perf = run_performance_check()
    lines.append(f"Performance: {len(perf['checked'])} operation(s) timed, {len(perf['findings'])} degraded/failed")

    return "\n".join(lines)


def _handle_ack(proposal_id: str) -> str:
    from shared.db import get_client

    result = (
        get_client().table("audit_bug_proposals").update({"status": "acknowledged"}).eq("id", proposal_id).execute()
    )
    if not result.data:
        return f"No proposal found with id {proposal_id}."
    return f"Proposal {proposal_id} acknowledged."


def _handle_text(text: str) -> str:
    text_stripped = text.strip()
    text_upper = text_stripped.upper()

    if text_upper == "STATUS":
        return _handle_status()

    match = _ACK_PATTERN.match(text_stripped)
    if match:
        return _handle_ack(match.group(1))

    return (
        'Reply "STATUS" for an on-demand sweep across all checks, or "PROPOSAL <id> ACK" to acknowledge a bug finding.'
    )


def check_for_audit_requests() -> dict:
    token = os.environ.get("TELEGRAM_AUDIT_BOT_TOKEN")
    expected_chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not expected_chat_id:
        return {"checked": False, "reason": "TELEGRAM_AUDIT_BOT_TOKEN/TELEGRAM_CHAT_ID not configured."}

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

    from agents.audit._telegram import send_telegram

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
        text = (msg.get("text") or "").strip()
        voice = msg.get("voice")
        if not text and voice:
            from shared.telegram_files import download_telegram_file
            from shared.voice.speech_to_text import transcribe

            local_path = download_telegram_file(token, voice["file_id"], ".ogg", DOWNLOADS_DIR)
            if local_path:
                transcription = transcribe(local_path)
                if transcription.get("ok"):
                    text = transcription["text"].strip()
        if not text:
            continue

        reply = _handle_text(text)
        send_telegram(reply, token_env="TELEGRAM_AUDIT_BOT_TOKEN")
        action_results.append({"text": text, "reply": reply})

    _save_last_update_id(highest_update_id)

    result = {"checked": True, "new_messages": len(updates), "triggered": bool(action_results)}
    if action_results:
        result["action_results"] = action_results
    return result
