# AI_EMPIRE — System Architecture

**Owner:** Systems & Automation Division (System Architecture pillar)
**Status:** Living document — update this whenever a division, service, table, or integration is added or changed. This describes what actually exists and runs today, not the aspirational full spec (see `CONTEXT.md`'s "Implementation Phases" for where the project is headed).

## What this is

AI_EMPIRE is a personal multi-agent system running on a single Windows machine (plus one Mac for local LLM inference), organized into 6 divisions. Every division follows the same shape: a set of Python agent modules, a dedicated Telegram bot, an n8n workflow (scheduled and/or a 30-second Telegram poll), a FastAPI HTTP wrapper so n8n can trigger it (this n8n install has no shell-execution node), and entries in `agent_registry`.

## The 6 divisions

| Division | Port | Purpose |
|---|---|---|
| Fixera | 8003 | 8 agents supporting the separate, real Fixera home-services platform (own production Supabase, reached only via a scoped read-only connector — never shared credentials) |
| Forex | 8002 | 11 agents: research, strategy, psychology, journaling, risk management, market analytics, backtesting, performance review, CEO/Lead aggregation, and Entry & Exit (real MT5 execution, demo-only until Mohamed clears a real account) |
| Personal & Education | 8004 (Personal), 8005 (Learning) | Habit Tracker, Morning Executive Brief, Gmail/Calendar integration (Personal); SRS flashcards, content ingestion, curriculum tracker (Learning) |
| Research & Innovation | 8006 | Research Agent (real Tavily search + Ollama synthesis), Watchtowers (periodic topic monitoring) |
| Audit & Verification | 8001 | Security Audit, Financial Verification, Performance Monitor, Report Verification, QA, Bug Detection — the only division whose job is checking every other division |
| Systems & Automation | 8007 | Reliability & Monitoring Agent (live); System Architecture (this document); Software Development tooling; the cybersecurity lab; AI Automation, Integration & APIs, Databases & Infrastructure, and the rest of Security & Performance remain unbuilt |

## Service topology

Everything runs locally, started manually per session (nothing persists across a machine restart yet — see "Known gaps" below):

- **n8n** (port 5678) — the orchestration layer. Every division's scheduled briefings and Telegram polling loops are n8n workflows (`infrastructure/n8n/*.json`) that hit each division's FastAPI wrapper over HTTP.
- **Ollama** (`OLLAMA_BASE_URL`, on a separate Mac, LAN IP drifts periodically) — the local model (`llama3.2:3b`) used for judgment-style tasks: RII's research synthesis, Learning's flashcard generation, Audit's QA review and bug-diagnosis, Systems' original scoped-role experiment. Deliberately NOT used for code-fix drafting (Bug Detection's `propose_fix()` stays stubbed) or anything requiring stronger reasoning than a 3B model reliably provides.
- **Division servers** — one `uvicorn` process per division on its own port (table above), each a thin FastAPI wrapper (`agents/<division>/server.py`) around real agent logic.
- **apps/api_gateway** (the Phase 1 Hybrid Router) exists in code but is **not currently running** as a persistent service — confirmed 2026-08-06. Not part of the live topology yet.

## Data layer

**AI_EMPIRE's own Supabase** (project `lkcfbmcjwmxxvtpjspgr`) holds 18 tables across two access patterns:

- `agent_registry`, `routing_logs`, `audit_vault` (immutable — a hard trigger blocks UPDATE/DELETE for every role, since RLS alone is bypassed by the service-role key), `job_queue`, `platform_settings`, `memory_knowledge`, `memory_experience`, `memory_identity`, `model_registry`, `prompt_registry`, `personal_habits`, `personal_habit_completions`, `learning_cards`, `curriculum_phases`, `curriculum_subjects`, `rii_watchtowers`, `audit_performance_log`, `audit_bug_proposals`, `circuit_breakers`.
- **Access pattern 1 (everything except Systems & Automation):** `shared/db.py`'s `get_client()`, authenticated with the all-powerful `SUPABASE_SERVICE_KEY`. This is the project-wide default and bypasses Row-Level Security entirely — a real, acknowledged, systemic gap (see `governance/policies/systems_automation_governance.md`, Rule 1).
- **Access pattern 2 (Systems & Automation only, so far):** `shared/systems_db_connector.py` — a self-signed JWT carrying a custom `app_role: systems_agent` claim, checked by real RLS policies (`infrastructure/database/migrations/0010_systems_agent_rls_jwt.sql`) that only allow touching `circuit_breakers` and `audit_vault`. Proven with real negative tests (2026-08-06): the connector genuinely cannot read `agent_registry` or `routing_logs`, verified against real non-empty tables, not an empty-table coincidence. This is the model future divisions' agents should move toward, not pattern 1.

**Fixera's production Supabase** (separate project, separate account) is reached only through `shared/fixera_connector.py`, a direct Postgres connection as the `ai_empire_reader` role via Supabase's session pooler, scoped to 11 read-only views (`infrastructure/fixera_connector_reference.sql`) that deliberately exclude PII, OTPs, national IDs, and free-text personal fields. No AI_EMPIRE agent ever touches Fixera's real tables directly, and nothing is ever written back.

## External integrations

| Integration | Used by | Notes |
|---|---|---|
| Ollama (Mac, local LLM) | RII, Learning, Audit (QA + Bug Detection) | IP drifts on the LAN; check `.env`'s `OLLAMA_BASE_URL` if a division reports it unreachable |
| Telegram (one bot per division) | Every division | `TELEGRAM_{DIVISION}_BOT_TOKEN` + shared `TELEGRAM_CHAT_ID`; each division has its own `_telegram.py`/`telegram_listener.py`, deliberately duplicated rather than shared |
| Tavily | RII | Real web search, replaced an earlier DuckDuckGo-scraping approach that got blocked in live testing |
| Google OAuth | Personal | Gmail (read-only) + Calendar |
| MetaTrader5 | Forex | Requires a locally-running MT5 terminal; Windows-only, which is why CI doesn't install the full `requirements.txt` |
| Docker (via WSL2) | Systems & Automation | The cybersecurity lab (OWASP Juice Shop, bound to `127.0.0.1` only) |

## Dev tooling (added 2026-08-07)

- **Ruff** — lint + format, config in `pyproject.toml`.
- **pytest** — real tests in `tests/`, currently covering the Systems & Automation circuit-breaker state machine. `pythonpath = ["."]` in `pyproject.toml` is required for `agents.*`/`shared.*` imports to resolve — `python -m pytest` doesn't need it (adds cwd to `sys.path` automatically) but the bare `pytest` command CI runs does.
- **pre-commit** — `ruff check`, `ruff format --check`, and `infrastructure/scripts/secret_scan.py`, installed into `.git/hooks/pre-commit`. Hook `entry:` paths must be absolute (`C:/moh-sudo/.venv/Scripts/...`) — a relative `.venv/Scripts/...` path did not resolve correctly under pre-commit's own subprocess invocation on Windows.
- **GitHub Actions CI** (`.github/workflows/ci.yml`) — runs the same three checks plus pytest on every push to `moh-sudo/AI-EMPIRE`. Installs only `requirements-dev.txt` + `requests`, not the full `requirements.txt` (MetaTrader5 is Windows-only and can't install on the Linux runner).
- **`gh` CLI** — installed and authenticated as `moh-sudo`, so CI status can be checked directly rather than only through GitHub's web UI.

## Governance

`governance/constitution/` and `governance/policies/` hold the real (not aspirational) rules currently in force:
- `self_healing_governance.md` — the 12-rule policy + Two-Agent Rule governing any autonomous bug-fixing (Audit's Bug Detection).
- `law_13_security.md` + `security_audit_policy.md` — the security audit's scope and honest status (what's really checked vs. what doesn't apply yet to a single-machine setup).
- `systems_automation_governance.md` — the 10-rule policy for Systems & Automation specifically, since it's the first division whose agents can kill/restart real processes. Includes the real status of database-level access enforcement (Rule 1) and the cybersecurity lab's credential air-gap (Rule 8).

## Known gaps (honest, not hidden)

- **Nothing persists across a machine restart.** n8n and every division server must be manually restarted each session (`netstat -ano` for ports 5678/8001-8007 to check what's actually running).
- **Access pattern 1 (the blanket service-role key) is still what 5 of 6 divisions use.** The RLS+JWT pattern proven for Systems & Automation is real, tested, and ready to replicate — just not done yet for the others.
- **`apps/api_gateway`** (the originally-planned Hybrid Router) isn't running as a live service. Nothing currently depends on it.
- **No architectural-consistency enforcement exists yet** — a future Systems & Automation agent could check that new divisions follow the established `_telegram.py`/`_memory_helpers.py`/`server.py` pattern automatically; today that's just convention, checked by a human (or Claude) reading the code.
- **OpenAI embeddings have never actually worked.** `OPENAI_API_KEY` is a real key, but has had `insufficient_quota` (no billing credits) since early sessions — confirmed still failing live as of 2026-08-09. Every `safe_add_experience`/`safe_add_knowledge` call across every division catches this and falls back to `embedding=None`, so `memory_knowledge`/`memory_experience` have real content but nothing is semantically searchable — only exact-filter queries work. Silent, not loud, because that fallback is by design (a missing embedding shouldn't block a memory write) — but it means vector search has been dead code in practice since day one. Fix is entirely outside this codebase: add billing credits at platform.openai.com.
- **The local voice interface (`interfaces/voice_session.py`, `shared/voice/`) is architecture-only, not fully wired.** Speech-to-text (Whisper, meant to run on the Mac) and text-to-speech are both still stubbed pending stronger hardware. Voice-note handling only exists on Learning's Telegram bot today; every other division's bot is text-only. Real phone calling (Twilio) is a separate, larger, not-yet-started decision.
