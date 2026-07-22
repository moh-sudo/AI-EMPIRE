# API Gateway — Hybrid Router

Single entry point for all AI requests: `POST /api/v1/route`.

## Setup

```bash
python -m venv .venv
.venv/Scripts/activate   # Windows
pip install -r apps/api_gateway/requirements.txt
python -m spacy download en_core_web_lg
```

Requires `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` in `.env` at the repo root.

## Run

```bash
uvicorn apps.api_gateway.main:app --reload --port 8000
```

## Request

```json
{
  "prompt": "some text",
  "data_classification": "CONFIDENTIAL",
  "division": "systems",
  "agent_id": "test-agent",
  "complex_reasoning": false
}
```

`data_classification` must be one of `SECRET`, `RESTRICTED`, `CONFIDENTIAL`, `INTERNAL`, `PUBLIC`.
