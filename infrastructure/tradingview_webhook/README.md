# TradingView Webhook Agent

Receives Mohamed's own TradingView Pine Script alerts and relays them to
Telegram (CEO/Lead bot) plus logs them to Supabase `memory_knowledge`.
Pure visibility only -- never feeds into any Strategy checklist or
execution path. See `shared/prompts/forex_tradingview_webhook_v1.json`
(repo root) for this agent's registered identity/mission/boundaries.

## Deploy

Import this repo into Vercel, set **Root Directory** to
`infrastructure/tradingview_webhook`, and configure these environment
variables in the Vercel project's Settings -> Environment Variables:

| Variable | Value |
|---|---|
| `WEBHOOK_SECRET` | A random secret string -- must match the `secret` field TradingView sends in the alert message JSON |
| `SUPABASE_URL` | Same value as in `.env` at the repo root |
| `SUPABASE_SERVICE_KEY` | Same value as in `.env` at the repo root |
| `TELEGRAM_CEO_BOT_TOKEN` | Same value as in `.env` at the repo root |
| `TELEGRAM_CHAT_ID` | Same value as in `.env` at the repo root |

## TradingView alert setup

In the Pine Script alert's "Message" field, use JSON with a `secret`
field matching `WEBHOOK_SECRET` and a `message` field with whatever
text you want relayed, e.g.:

```json
{"secret": "your-webhook-secret-here", "message": "{{ticker}} FVG detected on {{interval}}, close={{close}}"}
```

Set the alert's Webhook URL to `https://<your-deployment>.vercel.app/api/webhook`.
