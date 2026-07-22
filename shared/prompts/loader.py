import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from shared.audit.incidents import log_incident
from shared.db import get_client

PROMPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = PROMPTS_DIR.parent.parent

REQUIRED_SECTIONS = ("identity", "mission", "boundaries", "workflow")


class ImmutableCoreTamperedError(Exception):
    """Raised when a prompt file's Boundaries section no longer matches
    the hash recorded at registration/approval time."""


def _hash_boundaries(boundaries: str) -> str:
    return hashlib.sha256(boundaries.encode("utf-8")).hexdigest()


def _read_prompt_file(file_path: str) -> dict:
    full_path = Path(file_path)
    if not full_path.is_absolute():
        full_path = REPO_ROOT / file_path
    with open(full_path, "r", encoding="utf-8") as f:
        prompt = json.load(f)
    missing = [s for s in REQUIRED_SECTIONS if s not in prompt]
    if missing:
        raise ValueError(f"Prompt file {file_path} missing required section(s): {missing}")
    return prompt


def register_prompt(
    *,
    agent_id: str,
    division: str,
    version: str,
    file_path: str,
    approved_by: Optional[str] = None,
) -> dict:
    """Registers a prompt module's current Boundaries hash as the
    approved baseline. Call this deliberately, after governance review —
    never automatically on every load."""
    prompt = _read_prompt_file(file_path)
    boundaries_hash = _hash_boundaries(prompt["boundaries"])

    result = (
        get_client()
        .table("prompt_registry")
        .upsert(
            {
                "agent_id": agent_id,
                "division": division,
                "version": version,
                "file_path": file_path,
                "boundaries_hash": boundaries_hash,
                "approved_by": approved_by,
                "approved_date": datetime.now(timezone.utc).isoformat() if approved_by else None,
            },
            on_conflict="agent_id,version",
        )
        .execute()
    )
    return result.data[0]


def load_prompt(*, agent_id: str, version: str) -> dict:
    """Loads a registered prompt module and verifies its Immutable Core
    (Boundaries) section still matches the hash recorded at
    registration. A mismatch blocks the load and logs a Severity 2
    audit_vault incident — never silently loads a modified Boundaries
    section, same fail-closed posture as the Hybrid Router's PII checks.
    """
    result = (
        get_client()
        .table("prompt_registry")
        .select("*")
        .eq("agent_id", agent_id)
        .eq("version", version)
        .eq("active", True)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise ValueError(f"No active registered prompt for agent_id={agent_id} version={version}")

    registry_entry = result.data[0]
    prompt = _read_prompt_file(registry_entry["file_path"])
    current_hash = _hash_boundaries(prompt["boundaries"])

    if current_hash != registry_entry["boundaries_hash"]:
        log_incident(
            agent_id=agent_id,
            division=registry_entry["division"],
            action="load_prompt",
            outcome="blocked",
            severity=2,
            reason=(
                f"Immutable Core (Boundaries) hash mismatch for "
                f"{registry_entry['file_path']} — possible unauthorized edit."
            ),
        )
        raise ImmutableCoreTamperedError(
            f"Boundaries section of {registry_entry['file_path']} has changed "
            f"since approval; refusing to load."
        )

    return prompt
