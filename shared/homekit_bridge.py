"""HomeKit bridge trigger -- generic shared infra, not division-specific.

Bridges a voice command on this machine to an action on Mohamed's
iPhone, which nothing running on this Windows machine can otherwise
reach directly. The chain: this module calls a local Homebridge
instance's webhook plugin (homebridge-http-webhooks,
infrastructure/homekit_bridge/), which flips a virtual HomeKit push
button; the iPhone sees that button press over HomeKit and runs a
Shortcuts personal automation (configured on-device, with "Ask Before
Running" off) that performs the actual action -- e.g. opening
TradingView. This module's only job is firing the webhook call; it
has no visibility into whether the phone-side automation is even
configured, by design (that's real setup work only Mohamed can do on
his own device).

Homebridge must be running locally for this to do anything --
`npm start` (or the equivalent) inside infrastructure/homekit_bridge/,
same "must be manually running" caveat as n8n and every division
server in this project (see ARCHITECTURE.md's "Nothing persists
across a machine restart").
"""

import os

import requests

DEFAULT_WEBHOOK_URL = "http://127.0.0.1:51828"


def trigger_accessory(accessory_id: str) -> dict:
    """Fires a push-button accessory via Homebridge's HTTP webhook
    plugin. Never raises -- returns {"ok": False, "reason": ...} if
    Homebridge isn't running or the call otherwise fails, same
    fail-closed pattern as every other external call in this
    project."""
    base_url = os.environ.get("HOMEKIT_WEBHOOK_URL", DEFAULT_WEBHOOK_URL)
    try:
        resp = requests.get(
            f"{base_url}/",
            params={"accessoryId": accessory_id, "state": "true"},
            timeout=5,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        return {"ok": False, "reason": f"Homebridge webhook call failed: {e}"}

    return {"ok": True, "accessory_id": accessory_id}
