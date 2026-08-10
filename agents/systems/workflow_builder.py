"""Workflow Builder Agent -- Systems & Automation, AI Automation pillar.

On-demand, not a scheduled/polling agent like reliability_monitor.py --
Mohamed describes a workflow in plain language, this generates a new
n8n workflow JSON file matching the exact two-node
(scheduleTrigger -> httpRequest) pattern every one of the 16 existing
workflows in infrastructure/n8n/ already uses.

Two-stage, deliberately: an Ollama judgment call (via
shared/models/generate.py's chat()) interprets the free-text
description into structured parameters; a separate, deterministic
Python function then builds the actual JSON. The model never writes
the JSON directly -- asking it to produce a whole valid n8n workflow
freeform risks a subtly malformed or hallucinated structure that
looks right but silently fails to import. Structured-parameters-then-
template is the same shape as voice_capture.py's classify-then-
dispatch and content_transform.py's flashcard generation.

Action scope (see governance/policies/systems_automation_governance.md,
Rule 9 and Rule 10): this agent only ever writes a NEW file to
infrastructure/n8n/. It never connects to a live n8n instance, never
imports or activates a workflow, and never overwrites an existing
workflow file -- a name collision is refused, not resolved
automatically. Mohamed reviews and imports the generated file himself,
same as every workflow that already exists.
"""

import json
import re
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
WORKFLOWS_DIR = REPO_ROOT / "infrastructure" / "n8n"

# The full 7-division port map -- deliberately not imported from
# reliability_monitor.py, whose DIVISION_PORTS omits "systems" itself
# for a different reason (self-monitoring exclusion). Workflows can
# and do target the systems division's own server (see
# systems-telegram-poll.json, systems-health-check-scheduled.json).
DIVISION_PORTS = {
    "audit": 8001,
    "forex": 8002,
    "fixera": 8003,
    "personal": 8004,
    "learning": 8005,
    "rii": 8006,
    "systems": 8007,
}

# Matches every existing workflow file's meta.instanceId verbatim --
# an n8n instance identifier, already public in this repo.
_INSTANCE_ID = "2442c103091fc3db3a62ddff01333be403ece2b2cfb7e6ba914ccc82432a7656"

_CRON_PATTERN = re.compile(r"^\S+\s+\S+\s+\S+\s+\S+\s+\S+$")

_PARSE_PROMPT = (
    "You turn a description of a recurring automation into structured "
    "parameters for an n8n workflow. Extract every value from the real "
    "description at the very end of this prompt -- never reuse a value from "
    "the example below, it exists only to show the reply format.\n\n"
    "Reply with EXACTLY these five lines and nothing else:\n"
    "DIVISION: <one of audit, forex, fixera, personal, learning, rii, systems>\n"
    "NAME: <a short kebab-case workflow name you invent from the description>\n"
    "TRIGGER_TYPE: <cron if the description implies specific clock times or "
    'alignment ("every 4 hours" meaning on the hour marks, "twice a day", '
    '"at 6am and 6pm", "daily at 9am"); interval only for a short, simple '
    'repeating check with no clock alignment implied ("every 30 seconds", '
    '"every 5 minutes")>\n'
    "TRIGGER_VALUE: <if interval: convert to a whole number of SECONDS -- "
    '"15 minutes" becomes 900, "1 hour" becomes 3600, "30 seconds" stays 30; '
    "if cron: a valid 5-field cron expression, minute hour day month weekday, "
    'using comma-separated hours for multiple specific times, e.g. "0 6,18 * * *" '
    "for 6am and 6pm daily>\n"
    "ENDPOINT: <the exact HTTP path stated in the description, starting with "
    "/; if none is stated, invent a reasonable one>\n\n"
    "Two examples, for format only -- do not reuse these values:\n"
    'Description: "every 4 hours, ask RII to check its watchtowers at /check-watchtowers"\n'
    "DIVISION: rii\n"
    "NAME: rii-watchtower-check\n"
    "TRIGGER_TYPE: cron\n"
    "TRIGGER_VALUE: 0 */4 * * *\n"
    "ENDPOINT: /check-watchtowers\n\n"
    'Description: "twice a day, at 6am and 6pm, have Audit run its sweep at /run-sweep"\n'
    "DIVISION: audit\n"
    "NAME: audit-sweep-twice-daily\n"
    "TRIGGER_TYPE: cron\n"
    "TRIGGER_VALUE: 0 6,18 * * *\n"
    "ENDPOINT: /run-sweep\n\n"
    "Now extract the same five fields for this real description:\n"
)


def _parse_description(description: str) -> dict:
    """Ollama judgment call, parsed into a plain dict. Never raises --
    returns {"ok": False, "reason": ...} on any failure, same
    fail-closed pattern as every other external call in this
    project."""
    from shared.models.generate import chat

    result = chat(description, system=_PARSE_PROMPT)
    if not result.get("ok"):
        return {"ok": False, "reason": result["reason"]}

    fields: dict[str, str] = {}
    for line in result["reply"].strip().splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        fields[key.strip().upper()] = value.strip()

    required = {"DIVISION", "NAME", "TRIGGER_TYPE", "TRIGGER_VALUE", "ENDPOINT"}
    missing = required - fields.keys()
    if missing:
        return {"ok": False, "reason": f"Model reply missing fields: {sorted(missing)}", "raw_reply": result["reply"]}

    return {"ok": True, **{k.lower(): v for k, v in fields.items()}}


def _validate_parsed(parsed: dict) -> str | None:
    """Returns an error reason string, or None if valid. Deliberately
    strict -- a bad parse should fail closed, never produce a workflow
    file that looks plausible but is actually wrong."""
    if parsed["division"] not in DIVISION_PORTS:
        return f"Unknown division '{parsed['division']}'. Must be one of: {sorted(DIVISION_PORTS)}"
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", parsed["name"]):
        return f"Workflow name '{parsed['name']}' isn't valid kebab-case."
    if parsed["trigger_type"] not in ("interval", "cron"):
        return f"Unknown trigger type '{parsed['trigger_type']}'. Must be 'interval' or 'cron'."
    if parsed["trigger_type"] == "interval" and not parsed["trigger_value"].isdigit():
        return f"Interval trigger value '{parsed['trigger_value']}' isn't a whole number of seconds."
    if parsed["trigger_type"] == "cron" and not _CRON_PATTERN.match(parsed["trigger_value"]):
        return f"Cron trigger value '{parsed['trigger_value']}' isn't a valid 5-field cron expression."
    if not parsed["endpoint"].startswith("/"):
        return f"Endpoint '{parsed['endpoint']}' must start with /."
    return None


def _build_workflow_json(parsed: dict) -> dict:
    """Deterministic template -- the only thing that ever produces the
    actual n8n JSON. Matches the exact node shape every existing
    workflow in infrastructure/n8n/ already uses."""
    port = DIVISION_PORTS[parsed["division"]]
    trigger_id = str(uuid.uuid4())
    http_id = str(uuid.uuid4())

    if parsed["trigger_type"] == "interval":
        trigger_name = f"Every {parsed['trigger_value']}s"
        rule = {"interval": [{"field": "seconds", "secondsInterval": int(parsed["trigger_value"])}]}
    else:
        trigger_name = "Scheduled"
        rule = {"interval": [{"field": "cronExpression", "expression": parsed["trigger_value"]}]}

    http_name = f"Call {parsed['division'].capitalize()} {parsed['endpoint'].strip('/')}"

    return {
        "name": parsed["name"],
        "nodes": [
            {
                "parameters": {"rule": rule},
                "type": "n8n-nodes-base.scheduleTrigger",
                "typeVersion": 1.2,
                "position": [0, 0],
                "id": trigger_id,
                "name": trigger_name,
            },
            {
                "parameters": {
                    "method": "POST",
                    "url": f"http://127.0.0.1:{port}{parsed['endpoint']}",
                    "options": {},
                },
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.2,
                "position": [208, 0],
                "id": http_id,
                "name": http_name,
            },
        ],
        "pinData": {},
        "connections": {trigger_name: {"main": [[{"node": http_name, "type": "main", "index": 0}]]}},
        "active": True,
        "settings": {"executionOrder": "v1", "binaryMode": "separate", "availableInMCP": False},
        "versionId": str(uuid.uuid4()),
        "meta": {"instanceId": _INSTANCE_ID},
        "nodeGroups": [],
        "id": uuid.uuid4().hex[:20],
        "tags": [],
    }


def build_workflow(description: str) -> dict:
    """Full pipeline: description -> parsed params -> validated ->
    written to infrastructure/n8n/<name>.json. Never raises, never
    overwrites an existing file."""
    parsed = _parse_description(description)
    if not parsed.get("ok"):
        return {"ok": False, "stage": "parse", "reason": parsed["reason"]}

    error = _validate_parsed(parsed)
    if error:
        return {"ok": False, "stage": "validate", "reason": error, "parsed": parsed}

    output_path = WORKFLOWS_DIR / f"{parsed['name']}.json"
    if output_path.exists():
        return {"ok": False, "stage": "write", "reason": f"{output_path.name} already exists -- refusing to overwrite."}

    workflow = _build_workflow_json(parsed)
    try:
        output_path.write_text(json.dumps(workflow, indent=2) + "\n", encoding="utf-8")
    except OSError as e:
        return {"ok": False, "stage": "write", "reason": str(e)}

    return {"ok": True, "path": str(output_path), "parsed": parsed}
