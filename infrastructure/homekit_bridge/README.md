# HomeKit Bridge

Bridges a voice command on the HP laptop to a real action on Mohamed's
iPhone -- nothing running on this Windows machine can otherwise reach
a different physical device directly.

The chain: voice command -> `shared/homekit_bridge.py`'s
`trigger_accessory()` -> this local Homebridge instance's
`homebridge-http-webhooks` plugin -> a virtual HomeKit push-button
accessory changes state -> the iPhone sees that over HomeKit -> an
iOS Shortcuts personal automation (configured on the phone, "Ask
Before Running" off) performs the actual action.

## Setup

```bash
npm install
cp config.example.json config.json
```

Edit `config.json`: replace the placeholder `username` with a random
MAC-address-style string (e.g. `0E:3E:41:8A:2C:11`) and the placeholder
`pin` with a HomeKit-format PIN (`XXX-XX-XXX`) -- or just leave them
as-is and let Homebridge generate real ones on first run (it will
print a working PIN either way). `config.json` is gitignored on
purpose, same reason as `.env` -- `pin` is a real HomeKit pairing
credential.

## Run

```bash
npx homebridge -U . -I
```

`-U .` uses this directory for Homebridge's own storage/persistence
(`persist/`, also gitignored -- it holds the actual HomeKit pairing
keypair once paired). `-I` prints the pairing QR code/PIN on startup.

Must be manually started each session -- same "nothing persists across
a machine restart" caveat as n8n and every division server in this
project (see `ARCHITECTURE.md`'s Known Gaps).

## One-time phone setup (Mohamed's own device, can't be done remotely)

1. Open the **Home** app on the iPhone, add accessory, scan the QR
   code (or enter the PIN) Homebridge printed on startup.
2. Once paired, open **Shortcuts** -> **Automation** -> **+** ->
   **Create Personal Automation** -> pick the accessory that appeared
   (e.g. "Open TradingView") as the trigger ("is pressed").
3. Add an action: **Open App** -> TradingView (or **Open URL** with a
   TradingView deep link).
4. Turn **off** "Ask Before Running" -- without this, the automation
   still asks for a tap every time, defeating the point.

## Adding a new voice-triggered action

1. Add a new push-button entry to `config.json`'s `pushbuttons` array
   (unique `id`, a `name` that'll show up in the Home app).
2. Add the matching phrase -> `id` pair to
   `interfaces/wake_listener.py`'s `VOICE_COMMANDS` dict.
3. Repeat the phone-side Shortcuts automation setup above for the new
   accessory.
