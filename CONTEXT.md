# AI_EMPIRE — CONTEXT.md
# Paste this at the start of every new Claude Code session

## Project Identity
- **Repository:** moh-sudo (GitHub: hit510/moh-sudo)
- **Owner:** Mohamed Shukri
- **Project:** AI_EMPIRE — Full-stack AI automation operating system
- **Status:** Milestone 1 (Architecture) COMPLETE. Now executing Milestone 2 (Implementation).

---

## Current Milestone
**Milestone 2: Implementation Complete**
Building the agents, workflows, and infrastructure defined in the frozen governance framework.

Milestone 1 → Architecture Complete ✅
Milestone 2 → Implementation Complete ❌ (in progress)
Milestone 3 → Operationally Mature ❌ (future)

---

## Tech Stack
- **Database:** Supabase (PostgreSQL + pgvector)
- **Workflow Orchestration:** n8n (self-hosted, HP i3)
- **AI Gateway:** Python FastAPI (Hybrid Router — single entry point for all AI requests)
- **Local AI Runtime:** Ollama (MacBook Air M1 for staging, future GPU Server for production)
- **Cloud AI:** Anthropic Claude Sonnet (primary), OpenAI GPT-4o (secondary fallback)
- **PII Sanitization:** Microsoft Presidio (runs on HP i3, CPU-only, Day 1)
- **Email:** Resend API
- **Payments:** M-Pesa Daraja (blocked on company registration — do not implement yet)
- **Version Control:** Git / GitHub

## Hardware Environments
- **Development:** HP i3 Laptop — all logic, schemas, n8n workflows, mock data only
- **Staging/Testing:** MacBook Air M1 — Ollama local models (7-8B), Presidio, FastAPI testing
- **Production:** Future $4k GPU Server (DGX Spark) — 70B+ models, all SECRET/RESTRICTED data

---

## Repository Structure
```
moh-sudo/
├── .env                    # SECRETS (GitIgnored — NEVER commit)
├── .gitignore
├── README.md
├── CONTEXT.md              # This file — paste at start of every session
├── governance/             # All frozen policy documents (read-only reference)
│   ├── constitution/
│   ├── principles/
│   ├── policies/
│   └── standards/
├── apps/
│   ├── api_gateway/        # FastAPI Hybrid Router
│   ├── admin/
│   └── dashboard/
├── agents/
│   ├── audit/
│   ├── rii/
│   ├── forex/
│   ├── personal/
│   ├── learning/
│   ├── systems/
│   └── fixera/             # Fixera Division's 8 agents — AI_EMPIRE agents, NOT Fixera's app code (see "Fixera Relationship")
├── shared/
│   ├── memory/             # Knowledge/Experience/Identity CRUD
│   ├── routing/            # Classification & model selection logic
│   ├── middleware/         # Presidio PII pipeline
│   ├── auth/               # Identity & Access Management
│   ├── prompts/            # Versioned prompt modules (Identity/Mission/Boundaries/Workflow)
│   ├── models/             # Local model configs
│   ├── notifications/      # Resend email templates
│   └── audit/              # Logging utilities
├── infrastructure/
│   ├── database/           # Supabase SQL migrations + RLS policies
│   ├── docker/
│   ├── scripts/            # Weekly secret scan, BCP simulations
│   └── deployments/
└── tests/
    ├── unit/
    ├── integration/
    └── bcp/                # BCP scenario simulations
```

---

## Implementation Phases (current focus)

### PHASE 1 — Platform Foundation (CURRENT)
Goal: Build the nervous system all agents depend on.

**1.1 Supabase**
- Enable pgvector extension
- Create tables: audit_vault, routing_logs, agent_registry
- Configure RLS per Access Control Matrix

**1.2 FastAPI Hybrid Router** (`apps/api_gateway/`)
- Single endpoint: POST /api/v1/route
- Logic: receive prompt + metadata → Presidio PII scan → classify (PUBLIC/INTERNAL/CONFIDENTIAL/RESTRICTED/SECRET) → route to Local (Ollama) if RESTRICTED/SECRET, Cloud (Claude) if PUBLIC/INTERNAL/CONFIDENTIAL with sanitization
- Log every request to routing_logs
- Required fields in routing_logs: routing_destination, sanitization_status, model_identifier, data_classification, capability_matched, budget_impact

**1.3 n8n**
- Install locally on HP i3
- Connect to Supabase via Postgres node
- Create webhooks for external triggers

**1.4 Secrets Management**
- .env file (already in .gitignore)
- Weekly Python script to scan for accidentally committed secrets

### PHASE 2 — Core Shared Services
Goal: Minimal Memory Engine before first agent.

- Memory CRUD: memory_knowledge, memory_experience, memory_identity tables + vector embeddings
- Model Registry table + Prompt Registry table with Immutable Core loading
- Notification Service: Resend integration + 8 core Fixera email templates

### PHASE 3 — Governance Validation
Goal: First agent — Audit Agent v0.1

- n8n cron (daily 6:00 AM) → query routing_logs + agent_registry → anomaly check (>20% error rate, unclassified data in cloud logs) → Red/Amber/Green report → save to audit_vault → email Mohamed if Amber/Red
- Test on MacBook Air M1 with Ollama (Llama 3 8B)

### PHASE 4 — Fixera Division Agents (revised 2026-07-23 — see "Fixera Relationship")
Goal: Build Fixera Division's 8 agents as real AI_EMPIRE agents, connected to Fixera's own separate production database through a narrow, scoped, task-authorized connector — never a migration, never a shared table.

- Build the 8 Fixera Division agents (Service Delivery, Financial Ops, Trust & Safety, Platform Governance, Marketplace Intelligence, Customer Support, Partner Verification, Partner Support) in `agents/fixera/`, registered in `agent_registry`, prompts in `shared/prompts/fixera_{agent}_{version}.json`
- Build the scoped Fixera data connector: each agent gets read (and, where the Approval Matrix's sub-threshold Auto-Process track allows, limited write — e.g. Financial Ops processing below-threshold transactions) access to only the specific Fixera tables/fields its task requires, per Law 6. Above-threshold or disputed actions still require Mohamed's approval per the Escalation Ladder — no agent gets blanket write access.
- Fixera's own database schema/triggers are never edited by an AI_EMPIRE agent directly. Gaps found (sendCancellationConfirmation missing, `trg_wallet_gate` ignoring `platform_settings.wallet_minimum`, `services.js` hardcoding) are fixed as Fixera's own codebase work in `C:\fixera`, informed by what the Fixera agents/Audit division observe — not applied by AI_EMPIRE writing into Fixera's live schema.
- M-Pesa Daraja: DO NOT implement until company registration complete

### PHASE 5 — Intelligence Divisions
- Personal Division: Morning Executive Brief n8n workflow, Habit Tracker
- Learning Division: SRS engine, Content Transformation pipeline
- RII Division: Research Agent + Watchtowers
- Forex Division: Research Agent, Trade Journal to memory_experience

### PHASE 6 — Enterprise Automation
- Weekly Executive Review generation
- Risk Register auto-population from Audit findings
- Vendor API health monitoring

### PHASE 7 — Production Readiness
- Penetration testing (FastAPI router + Supabase RLS)
- DR simulation (Supabase failure + backup restoration)
- All 5 BCP scenario playbook drills
- Golden Dataset validation per division
- Governance audit (all agents in Registry, all prompts versioned)
- Vendor DPA verification checklist
- Supply chain security scan

### PHASE 8 — Production Launch
- GPU Server deployment
- Real-time monitoring dashboards
- Mohamed's Constitutional sign-off for Production Mode

---

## Key Database Tables (Phase 1 priority)

### audit_vault
```sql
CREATE TABLE audit_vault (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  timestamp TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  agent_id TEXT NOT NULL,
  division TEXT NOT NULL,
  action TEXT NOT NULL,
  outcome TEXT NOT NULL,
  data_classification TEXT NOT NULL,
  law_reference TEXT,
  data_hash TEXT,
  metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
-- Immutable: no UPDATE or DELETE allowed (Law 9)
ALTER TABLE audit_vault ENABLE ROW LEVEL SECURITY;
CREATE POLICY "audit_vault_insert_only" ON audit_vault FOR INSERT WITH CHECK (true);
CREATE POLICY "audit_vault_select" ON audit_vault FOR SELECT USING (true);
```

### routing_logs
```sql
CREATE TABLE routing_logs (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  timestamp TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  prompt_hash TEXT NOT NULL,
  data_classification TEXT NOT NULL,
  routing_destination TEXT NOT NULL,
  sanitization_status TEXT NOT NULL,
  model_identifier TEXT NOT NULL,
  capability_matched TEXT,
  tokens_used INTEGER,
  cost_usd NUMERIC(10,6),
  latency_ms INTEGER,
  division TEXT,
  agent_id TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE routing_logs ENABLE ROW LEVEL SECURITY;
```

### agent_registry
```sql
CREATE TABLE agent_registry (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  agent_id TEXT UNIQUE NOT NULL,
  agent_name TEXT NOT NULL,
  division TEXT NOT NULL,
  lifecycle_stage TEXT NOT NULL CHECK (lifecycle_stage IN ('Design','Shadowing','Supervised','Autonomous','Retired')),
  model_class TEXT NOT NULL CHECK (model_class IN ('A','B','C','D')),
  approved_data_classifications TEXT[] NOT NULL,
  last_review TIMESTAMPTZ,
  next_review TIMESTAMPTZ,
  approved_by TEXT,
  approved_date TIMESTAMPTZ,
  shadowing_successor_id TEXT,
  status TEXT DEFAULT 'active',
  metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE agent_registry ENABLE ROW LEVEL SECURITY;
```

---

## Critical Governance Rules (enforce in ALL code)

### Routing Rules (Hybrid Router must enforce)
- SECRET → Local Runtime ONLY or BLOCKED. Never to cloud.
- RESTRICTED → Local Runtime default. Cloud only if Presidio sanitization applied first.
- CONFIDENTIAL → Local default. Cloud allowed if complex reasoning needed + Presidio applied.
- INTERNAL → Local default (cost saving).
- PUBLIC → Either. Default to Local.

### Hard Rules
- No agent may permanently delete data from audit_vault or routing_logs (Law 9)
- All credentials in .env only — never in code, prompts, or logs
- Prompts use modular structure: Identity / Mission / Boundaries (Immutable) / Workflow
- Business rules (thresholds, prices, SLAs) in database tables, NEVER hardcoded in code
- Every routing_logs entry must include sanitization_status field
- Audit Agent daily check: flag any routing_destination='cloud' where sanitization_status='none' and data contains PII patterns
- Payment threshold is in approval_matrix table — not hardcoded anywhere

### Fixera-specific (from production codebase audit)
- `workers.can_receive_jobs` (not `is_available`) is the correct wallet gate field
- `payments.status→'paid'` fires TWO DB triggers automatically — do not duplicate
- Email channel: Resend only. Push (FCM) is wired but no-op. WhatsApp is human-only. SMS not integrated.
- `services.js` (413-line hardcoded array) is the current runtime source for service catalog — NOT the DB table. Fix this in Phase 4.
- `platform_settings.wallet_minimum` exists but trigger ignores it (hardcoded 500) — fix in Phase 4.
- SLA hours hardcoded in TWO places — consolidate in Phase 4.
- OTPs are client-side Math.random() 4-digit — fine for friction, not cryptographic.
- M-Pesa: amounts always server-looked-up from payments row, never trusted from client — keep this pattern.

---

## Fixera Relationship (decided 2026-07-23, corrected from two earlier reverted attempts)
Fixera and AI_EMPIRE are **two permanently separate Supabase projects/databases**. Fixera's production database (bookings, payments, customers — real revenue, real customers) is **never migrated, merged, or shared as a table** with AI_EMPIRE's database. This overrides the Implementation Roadmap's original Phase 4.1 plan ("connect existing Fixera app to new Supabase project"), which was a full database migration — rejected as too risky to put live production data inside a system still being actively built.

**But Fixera's 8 agents are real AI_EMPIRE agents**, not excluded from the system. They're built in `agents/fixera/`, registered in `agent_registry`, run through the Hybrid Router, and communicate with other divisions (Audit & Verification, RII, etc.) through the Master Orchestrator exactly as the governance document specifies — using AI_EMPIRE's own `routing_logs`/`audit_vault`/`agent_registry`.

**How agents reach Fixera's actual data:** through a narrow, scoped connector (API calls to Fixera's backend, or a minimally-privileged Supabase credential Fixera issues specifically for this purpose) — never a raw shared table, never blanket access. Each agent's access is scoped to exactly what its task needs (Law 6), and higher-stakes actions (above-threshold payments, disputed transactions) still require Mohamed's approval per the Escalation Ladder regardless of what the connector technically permits.

**Fixes to Fixera's own code/schema** (the `wallet_minimum` trigger bug, `services.js` migration, `sendCancellationConfirmation`) happen as independent work in `C:\fixera`, not as something an AI_EMPIRE agent writes into Fixera's live database. AI_EMPIRE's Audit division can surface the finding; Fixera's own repo is where it gets fixed.

The "Fixera-specific (from production codebase audit)" notes above are kept (not deleted, unlike an earlier reverted attempt) because they're exactly what the Fixera agents built in Phase 4 will need to know when working with Fixera's data through the connector.

---

## Conventions
- All SQL migrations go in: infrastructure/database/migrations/
- All n8n workflow exports go in: infrastructure/n8n/
- Prompt files follow naming: {division}_{agent}_{version}.json
- Every commit message uses conventional commits: feat:, fix:, chore:, docs:
- Never commit .env — check with `git status` before every push
- Weekly secret scan script lives at: infrastructure/scripts/secret_scan.py

---

## What NOT to build yet
- M-Pesa Daraja integration (blocked on company registration)
- FCM push notifications (wired but no-op — leave for Phase 6)
- WhatsApp automation (human-only deep links currently)
- Laws 13-18 implementation (undrafted constitutional proposals)
- 70B model deployment (Phase 8 — GPU Server required)

---

## Session Update Instructions
At the end of each Claude Code session, update this file with:
1. What was completed this session
2. Current phase status
3. Any new decisions or discoveries about the codebase
4. Next session's first task

This keeps continuity across sessions without losing context.

---

## Session Log

### 2026-07-22 — Phase 1 complete
**Completed:**
- Repo scaffolded fresh at `C:\moh-sudo` (the `moh-sudo` GitHub repo did not exist/was inaccessible; no prior local copy existed either — started clean). `apps/fixera/` intentionally NOT created — Fixera and AI_EMPIRE are kept as fully separate projects/repos/Supabase orgs per explicit user decision, which conflicts with this file's own Phase 4 plan to merge them. That conflict is unresolved and must be revisited before Phase 4.
- New, separate Supabase project created (project ref `lkcfbmcjwmxxvtpjspgr`), NOT the Fixera project.
- `infrastructure/database/migrations/0001_phase1_foundation.sql` applied: pgvector, `audit_vault`, `routing_logs`, `agent_registry`, `circuit_breakers` (seeded), `job_queue`, `platform_settings.compute_budgets`. RLS enabled on all 6 tables.
- `apps/api_gateway/`: FastAPI Hybrid Router (`POST /api/v1/route`) built and verified end-to-end against the live Supabase project — 5-tier routing rules, Presidio PII scan (fail-closed), routing_logs + audit_vault (Severity 2 incident) logging all confirmed working with real requests.
- `infrastructure/scripts/secret_scan.py` written and passing clean.
- n8n installed locally via npm, connected to Supabase via the **Session pooler** (IPv4) — direct connection (`db.<ref>.supabase.co`) is IPv6-only and failed on this network. Test workflow (`infrastructure/n8n/test-supabase-connection.json`) verifies connectivity by reading `circuit_breakers`.
- `.env` confirmed never committed (zero git history). Two stray plaintext copies of the Supabase service key found outside the repo (`OneDrive\Dokumente\.env.txt`, `.env.local2.txt`) and deleted.

**Current phase status:** Phase 1 — COMPLETE. All 7 completion criteria verified.

**Decisions/discoveries:**
- Supabase org for this project should stay separate from Fixera's org (`fixera.services1@gmail.com's Org`) — used a different account/org.
- routing_logs' required field "budget_impact" (per this file's Phase 1.2 spec) maps to the `cost_usd` column in the actual migration — see comment in `apps/api_gateway/supabase_client.py`.
- RESTRICTED classification currently always routes local in the router (never cloud, even sanitized) — a conservative reading of "Cloud only if Presidio sanitization applied first" that was never explicitly exercised; revisit if RESTRICTED→cloud is actually needed later.

**Next session's first task:** Resolve the Fixera/AI_EMPIRE merge conflict in the Phase 4 plan (this file still says to build `apps/fixera/` and connect the existing Fixera app), then start Phase 2 (Core Shared Services — Memory CRUD, Model/Prompt Registry, Notification Service).

### 2026-07-22 — Phase 2 complete
**Completed:**
- `infrastructure/database/migrations/0002_phase2_core_services.sql` applied: `memory_knowledge`, `memory_experience`, `memory_identity` (all pgvector, 1536-dim), `model_registry` (seeded), `prompt_registry`, plus `match_memory_knowledge`/`match_memory_experience` RPCs for cosine-similarity search. RLS enabled on all.
- `shared/memory/`: knowledge + experience CRUD with OpenAI embedding generation (`shared/memory/embeddings.py`), identity key-value CRUD. Verified end-to-end against live Supabase using stub zero-vectors (no real `OPENAI_API_KEY` yet, so similarity scores were NaN as expected — structure confirmed working, real similarity needs a real key).
- `shared/models/registry.py`: model_registry CRUD.
- `shared/prompts/loader.py`: Immutable Core (Boundaries) hash verification. Tested both paths live — valid load succeeds, a tampered Boundaries section is blocked and logs a Severity 2 `audit_vault` incident. Sample prompt at `shared/prompts/systems_reliability-monitor_v1.json`.
- `shared/notifications/resend_client.py`: generic Resend sender, **no Fixera-specific templates** — explicitly deferred per user decision (Phase 2 spec originally called for "8 core Fixera email templates"; skipped until the Phase 4 Fixera/AI_EMPIRE relationship is resolved).
- `shared/audit/incidents.py`: shared audit_vault logging helper (used by both the prompt loader and, going forward, other shared modules).

**Current phase status:** Phase 2 — COMPLETE (generic scope only; Fixera email templates explicitly deferred).

**Decisions/discoveries:**
- The Fixera/AI_EMPIRE Phase 4 conflict resurfaced immediately in Phase 2's own spec (Fixera email templates) — this is not a Phase-4-only issue, watch for it recurring in later phases too.
- Real embedding generation and Resend sending are untested against live external APIs — both `OPENAI_API_KEY` and `RESEND_API_KEY` are still placeholders in `.env`.

**Next session's first task:** Resolve the Fixera/AI_EMPIRE relationship (recommend doing this before it blocks more work), then start Phase 3 (Governance Validation — Audit Agent v0.1). Also: get real `OPENAI_API_KEY`/`RESEND_API_KEY` values in `.env` to fully exercise Phase 2's embedding and email paths.

### 2026-07-23 — Fixera relationship resolved (after two reverted attempts)
**What happened:** Two earlier attempts at this got it wrong and were reverted. Attempt 1 deleted Fixera from CONTEXT.md entirely (no relationship at all) — wrong, because Fixera genuinely needs to feed the Audit/Verification division, through the Master Orchestrator, to Research (RII). Attempt 2 was caught before editing anything. Both source documents (`AI_EMPIRE_Master_Governance_v2.docx`, `AI_EMPIRE_Implementation_Roadmap_v1.docx` — both in `Downloads\Ai-main files\`, previously only CONTEXT.md's summary had been read) were then read in full to find the actual data-sharing laws (Law 6: Privacy — "only access information required for the task"; Law 11: No Unauthorized Information Leakage) and the real technical plan.

**What the roadmap actually specified:** Phase 4.1 was a literal database migration ("connect existing Fixera app to new Supabase project," "verify RLS policies intact after migration") — Fixera's live production data moving into AI_EMPIRE's Supabase project, with Law 6/11 enforced afterward via RLS/classification within one shared database. That's a real, deliberate design choice in the source document, not a misreading — but it was rejected here as too risky for a live revenue system sitting inside a database an early-stage, actively-changing project also has full access to.

**Final resolution:** See the new "Fixera Relationship" section above. Two permanently separate Supabase projects. Fixera's 8 agents are real AI_EMPIRE agents (built in `agents/fixera/`, registered in `agent_registry`, communicating with other divisions through the Master Orchestrator as designed) — but they reach Fixera's actual production data through a narrow, scoped, task-authorized connector, never a shared table or migration. Fixes to Fixera's own schema/code happen in `C:\fixera` directly, not via an AI_EMPIRE agent writing into Fixera's live database. Phase 4 in this file rewritten accordingly — the "Fixera-specific" governance notes were kept (not deleted) since Phase 4's agents will need them.

**Current phase status:** No phase change — planning correction only. Phase 2 remains COMPLETE; Phase 3 not yet started.

**Next session's first task:** Start Phase 3 (Governance Validation — Audit Agent v0.1). The scoped Fixera connector and the 8 Fixera agents are Phase 4 work, not needed yet. Still pending: real `OPENAI_API_KEY`/`RESEND_API_KEY` in `.env`.

### 2026-07-23 — Phase 3 complete (Audit Agent v0.1)
**Completed:**
- `agents/audit/checks.py`: the 4 anomaly checks mapped onto the actual schema. `routing_logs` has no error/status column, so ">20% error rate" is defined as blocked-attempts (logged to `audit_vault`, action=`route_request`, outcome=`blocked`) over total attempts in the last 24h. The other 3 checks (unsanitized CONFIDENTIAL+ routed to cloud, stale `agent_registry` reviews, `routing_logs` missing `capability_matched`/`cost_usd`) map directly.
- `agents/audit/audit_agent.py`: runs the checks, classifies Red (any Critical finding) / Amber (any other finding) / Green (clean), saves immutably to `audit_vault`, emails Mohamed on Amber/Red via `shared/notifications/resend_client.py`.
- Registered in `agent_registry` (`audit-agent-v0.1`, division `audit`, lifecycle `Shadowing`, model_class `D` — deterministic rule-based, no LLM in v0.1).
- **Found and fixed a real gap**: `audit_vault`'s "immutable" claim only held via RLS, which the `service_role` key our own backend uses always bypasses in Supabase. Verified an UPDATE succeeded despite RLS having no UPDATE policy. Fixed with `0003_audit_vault_immutability_trigger.sql` — a `BEFORE UPDATE/DELETE` trigger that unconditionally rejects mutation regardless of role. Re-verified: both UPDATE and DELETE now correctly blocked even from the service_role client.
- `agents/audit/server.py`: this n8n installation has no shell/command-execution node (confirmed live in the n8n UI — it explicitly suggests HTTP Request instead), so a minimal FastAPI wrapper (`POST /run`) exposes the Audit Agent for n8n to call over HTTP.
- `infrastructure/n8n/audit-agent-daily.json`: Schedule Trigger (daily 06:00, cron `0 6 * * *`) → HTTP Request (`POST http://127.0.0.1:8001/run`). Activated in n8n; manually executed once and confirmed a fresh `audit_vault` row landed immediately.

**Verified live against Supabase:** Green baseline (clean data), then each of the 4 checks individually triggered via deliberate test rows and correctly detected; overall status correctly prioritizes Critical → Red over Amber-level findings.

**Not yet verified:** actual email delivery — `RESEND_API_KEY` is still a placeholder in `.env`, so Amber/Red emails haven't actually been sent (the code path exists and fails gracefully — logs a Severity 2 incident — if the send fails).

**Current phase status:** Phase 3 — COMPLETE (4 of 5 completion criteria fully verified; email delivery pending a real `RESEND_API_KEY`).

**Operational note:** both `agents/audit/server.py` (port 8001) and n8n itself need to be running as persistent processes for the 06:00 cron to actually fire — currently just manually-started dev processes, not yet running as proper background services.

**Next session's first task:** Get a real `RESEND_API_KEY` in `.env` and verify an actual Amber/Red email arrives (trigger a deliberate anomaly, confirm delivery). Then start Phase 4 (Fixera Division's 8 agents + the scoped connector, per the "Fixera Relationship" section).

### 2026-07-23 — Email delivery verified, Phase 3 now fully complete
**Completed:**
- New, separate Resend account created (`mahmmed2000shukri@gmail.com` — after discovering `mohamed2002shukri@gmail.com`'s Resend account already had `Fixera Production`/`fixera_partner_app` API keys in it, so that one was not actually clean).
- Verified a sending subdomain, `ai-empire.fixera.africa`, under that new account. Uses the same root domain as Fixera (`fixera.africa`, owned via Namecheap) but a distinct subdomain — shares only the DNS zone (administrative visibility), not the Resend account, API key, quota, or Fixera's own existing `send.fixera.africa` sending setup on the same domain.
- `RESEND_API_KEY` (new account) added to `.env`. `shared/notifications/resend_client.py`'s default `from_address` updated to `AI_EMPIRE <audit@ai-empire.fixera.africa>` (was the Resend sandbox address, which can only send to the account's own email).
- Triggered the Audit Agent for real: no email-send failure was logged (previous runs had logged failures for "RESEND_API_KEY not configured" and then "sandbox mode, can't send to other recipients" — this run logged neither), and the user confirmed receiving the actual Red report email at `mohamed2002shukri@gmail.com`.

**Current phase status:** Phase 3 — COMPLETE. All 5 completion criteria verified, including real email delivery.

**Decisions/discoveries:** Resend accounts start in sandbox mode (can only send to the account's own address) until a domain is verified — worth remembering for any future Resend account setup. Domain DNS record values must be copied via the provider's copy button, not manually transcribed from a truncated on-screen display — an initial verification attempt failed because truncated placeholder text got pasted instead of the real (much longer) values.

**Next session's first task:** Start Phase 4 (Fixera Division's 8 agents + the scoped connector, per the "Fixera Relationship" section).

### 2026-07-23 — Phase 4 started: 8 Fixera agents registered, connector attempt reverted
**Completed:**
- All 8 Fixera Division agents registered in `agent_registry` + `prompt_registry` (`fixera-{slug}-v0.1`, division `fixera`, lifecycle `Design`, model_class `B` per the governance doc's Hallucination Mitigation table). Prompt files at `shared/prompts/fixera_{slug}_v1.json`. No workflow logic implemented yet for any of them — Identity/Mission/Boundaries only, consistent with how none of the source documents specify per-agent implementation detail.
- Researched Fixera's actual production schema (bookings, workers, payments, disputes, reviews) via an Explore agent plus direct `information_schema` queries run by the user in Fixera's SQL Editor — the code-inferred schema for `bookings`/`workers` turned out to be wrong in places (no `amount` column on bookings, no `can_receive_jobs` column or `trg_wallet_gate` trigger on workers despite both being referenced in Fixera's own migrations and governance notes — that migration was apparently never applied to production). Ground-truth column lists now documented in `infrastructure/fixera_connector_reference.sql`.
- Designed and built the scoped Fixera connector: 5 narrow read-only views (`ai_empire_bookings_summary`, `ai_empire_payments_summary`, `ai_empire_disputes_summary`, `ai_empire_reviews_summary`, `ai_empire_workers_summary`) excluding PII/sensitive fields (OTPs, raw addresses, phone numbers, mpesa references, national IDs, photos, all free-text statement/comment fields), plus a dedicated `ai_empire_reader` Postgres role with SELECT-only grants on exactly those 5 views. Partner Verification's data need (raw `owner_national_id`/KYC documents) deliberately excluded/deferred pending a separate, more careful design.
- **Could not get the connection working.** Password authentication to Fixera's Supabase pooler (Supavisor) failed consistently across many attempts: initial passwords, a full password rotation, waiting out Supavisor's documented circuit-breaker cooldown, both session (5432) and transaction (6543) pooler ports, and finally a complete fresh DROP+CREATE of the role with an exact password verified identical on both sides. Direct (non-pooled, IPv6) connection wasn't testable — this network has no functional IPv6 (DNS resolves the AAAA record but there's no real route, confirmed via `Test-NetConnection` and the absence of an IPv6 address in Windows' network adapter details). Root cause undetermined; likely a genuine Supavisor limitation with custom roles rather than a configuration error — see the commit message on `infrastructure/fixera_connector_reference.sql` for full detail.
- **Reverted everything on Fixera's side**: `REVOKE` + `DROP ROLE ai_empire_reader` + `DROP VIEW` on all 5 views. Fixera's database has none of this anymore — only the read-only research queries ever touched it. Removed `FIXERA_DB_*` from `.env`. The verified-correct view/role SQL is preserved in `infrastructure/fixera_connector_reference.sql` for a future retry (e.g., from a network with working IPv6, or after consulting Supabase support/community).

**Current phase status:** Phase 4 — IN PROGRESS. 8 agents registered; connector not yet working (reverted, ready to retry).

**Decisions/discoveries:** Also found, unrelated to the connector itself: Fixera's own `trg_wallet_gate` trigger and `can_receive_jobs` column don't actually exist in production despite being referenced in Fixera's migrations and this file's own "Fixera-specific" governance notes — the wallet-minimum enforcement Fixera's docs assume is live isn't. Worth Fixera's own team looking at; not touched from here per the "Fixera Relationship" model.

**Next session's first task:** Either retry the Fixera connector (SQL ready in `infrastructure/fixera_connector_reference.sql`, ideally from a network with working IPv6 or after checking Supabase's Supavisor documentation/support for custom-role pooler issues), or move on to giving the 8 registered Fixera agents real workflow logic using mock/test data in the meantime (similar to how Audit Agent v0.1 started before Phase 4 connected it to anything live).

### 2026-07-23 — 3 of 7 Fixera agents given real logic (mock data, connector still pending)
**Completed:** `agents/fixera/service_delivery.py`, `financial_ops.py`, `trust_safety.py` -- each unit-tested against mock data matching the connector view schemas, each moved `agent_registry.lifecycle_stage` from `Design` to `Shadowing`.

- **Service Delivery**: `match_partner` (Phase 1 flat-pool dispatch + wallet gate, per Fixera's own roadmap note that the fuller multi-factor Dispatch Decision Framework is their future Phase 2), `detect_lifecycle_event`, `build_lifecycle_email` for the 3 emails this agent owns. Found a real scope boundary: `ai_empire_bookings_summary` excludes customer email/phone (PII minimization), so email sending needs an explicit recipient rather than a lookup -- noted, not silently worked around.
- **Financial Operations**: `classify_transaction`/`classify_batch` -- auto_process / escalate_human / emergency_hold per the Escalation Ladder's Track 1. Decision-only; never executes a payment (Approval Matrix: AI Agent No, Mohamed Yes). M-Pesa itself stays out of scope (blocked on company registration).
- **Trust & Safety**: `triage_dispute` (48h SLA tiers), `detect_review_pattern_signals` (clustered low-rating fraud signal, flag-only), `workers_due_for_kyc_reverification`. Found a gap: the connector view has no verification-date column, so re-verification scheduling uses `created_at` as a stand-in -- flagged as a real limitation, not hidden.

**Current phase status:** Phase 4 — IN PROGRESS. 8 agents registered, 3 with tested logic (Service Delivery, Financial Operations, Trust & Safety), 4 still placeholder-only (Platform Governance, Marketplace Intelligence, Customer Support, Partner Support), Partner Verification deliberately deferred. Connector still not connected to anything live.

**Next session's first task:** Continue with the remaining 4 agents (Platform Governance, Marketplace Intelligence, Customer Support, Partner Support), same pattern -- real logic against mock data, unit-tested, `lifecycle_stage` updated. Partner Verification and the connector itself stay deferred.

### 2026-07-23 — All 7 in-scope Fixera agents now have real logic
**Completed:** the remaining 4 agents, same pattern as the first 3 (unit-tested against mock data, `lifecycle_stage` Design -> Shadowing):

- **Platform Governance**: `check_column_drift`/`check_trigger_drift`/`check_view_drift` implementing the Execution Truth Principle. Tested against real data, not synthetic -- correctly re-derives the exact 3 discrepancies found earlier this session (`can_receive_jobs` column, `trg_wallet_gate` trigger, `partner_wallet_status` view, all documented but missing in production), plus a negative case confirming no false positives.
- **Marketplace Intelligence**: `demand_by_service`, `partner_utilization` (bookings-per-worker ratio, handles the zero-worker case without a `ZeroDivisionError`), `bottleneck_services`.
- **Customer Support**: `triage_ticket` (SLA tiers by priority), `prioritize_queue`, `build_status_update_email` (verified to never mention refunds -- that's Financial Ops' job). Found a gap: no ticket-summary view exists in the connector (Fixera's `moving_support_tickets`/`ticket_notes` tables weren't in the initial 5-view scope) -- built against a generic mock shape pending that.
- **Partner Support**: `check_needs_escalation` (12h window, tighter than Customer Support's 24h since partner issues can mean a worker stops taking jobs; urgent overrides age), `build_team_notification` (internal-facing, not partner-facing). Same ticket-view gap as Customer Support.

**Current phase status:** Phase 4 — all 7 in-scope agents have real, unit-tested logic. Only two things remain: (1) Partner Verification, deliberately deferred pending a dedicated design for handling `owner_national_id`/KYC documents safely; (2) the connector itself, reverted and unresolved (Supavisor auth issue). None of the 7 agents' logic is connected to live Fixera data yet -- everything tested against mock data shaped like the (currently nonfunctional) connector views.

**Decisions/discoveries:** Two small connector gaps surfaced while building agent logic: no dedicated worker verification-date column (Trust & Safety's KYC re-check uses `created_at` as a stand-in), and no ticket-summary view at all (Customer Support and Partner Support both built against generic mock shapes). Worth adding to `infrastructure/fixera_connector_reference.sql` whenever the connector gets revisited.

**Next session's first task:** Retry the Fixera connector (see the 2026-07-23 "Phase 4 started" entry above for what was tried) so the 7 built agents can run against real data instead of mocks. Alternatively, design Partner Verification's sensitive-data handling, or move to a different phase/division entirely.

### 2026-07-23 — Fixera connector working
**What happened:** Recreated the same views/role/grants (unchanged SQL) and it worked. Confirmed live: connected as `ai_empire_reader`, read real rows from all 5 views, write access correctly blocked (`InsufficientPrivilege`), and access to raw tables outside the 5 views (tried `workers` directly) also correctly blocked -- scoping works exactly as designed.

**Root cause of the earlier persistent failures, now better understood:** not a fundamental Supavisor/custom-role limitation as suspected. While testing the connector module, two consecutive calls with identical, verified-correct credentials succeeded, then an immediately following identical call failed with the same "password authentication failed" error -- directly observed, not inferred. This points to Supavisor running multiple backend pooler nodes behind one hostname that don't all have a newly-created role's credentials cached at the same time; which node a given connection lands on determines success or failure until the nodes converge. Added retry logic (4 attempts, 2s apart) to `shared/fixera_connector.py` as the correct fix for that -- confirmed reliable across repeated runs afterward.

**Completed:** `shared/fixera_connector.py` -- `fetch_all(resource, limit=None)`, a deliberately narrow interface (resource is one of `bookings`/`payments`/`disputes`/`reviews`/`workers`, mapped internally to the exact 5 views) rather than a raw SQL passthrough, so callers can't query outside what's actually granted.

**Current phase status:** Phase 4 -- connector is live and working. All 7 in-scope agents (Service Delivery, Financial Operations, Trust & Safety, Platform Governance, Marketplace Intelligence, Customer Support, Partner Support) have tested logic ready to consume it, but none have been wired to call `fetch_all` yet -- they still take data as function parameters (tested with mock dicts). Only Partner Verification remains fully deferred.

**Next session's first task:** Wire the 7 agents to actually call `shared.fixera_connector.fetch_all(...)` instead of only accepting mock data as parameters, and test each one end-to-end against real (if currently sparse -- 1 booking, 2 workers, 0 payments/disputes/reviews) production data. Then decide on Partner Verification's design.

### 2026-07-23 — 4 agents wired to the live connector, verified against real production data
**Completed:** added a `run_*()` live entry point to each agent whose data the connector actually covers, keeping the existing tested pure-logic functions unchanged (still take data as parameters -- correct separation of concerns, no need to hit the DB to unit-test a decision):

- **Service Delivery**: `run_dispatch_sweep()`. Verified against the one real booking in production -- already `in_progress` with a worker assigned, correctly excluded from the "needs dispatch" sweep (confirmed by inspecting the raw row, not just trusting an empty result).
- **Financial Operations**: `run_classification_sweep()`. No fraud-signal source exists yet, so `fraud_flagged_ids` stays empty rather than fabricated. Noted a minor theoretical looseness (payment.ref_id vs dispute.booking_id isn't filtered by ref_type) -- safe in practice since these are UUIDs, cross-type collision isn't realistic, but documented for future tightening.
- **Trust & Safety**: `run_trust_safety_sweep()`. Confirmed psycopg2 returns `timestamp with time zone` columns as timezone-aware `datetime` objects (not strings) -- the existing `isinstance(str)` branches in each check handle this transparently, no special-casing needed between mock and live data.
- **Marketplace Intelligence**: `run_intelligence_sweep()`. Correctly surfaced a genuine bottleneck signal from real data (`Cleaning`: 1 open booking, 0 available workers right now).

**Not wired (documented reasons, not oversights):** Platform Governance needs `information_schema` metadata, a different kind of query than the connector's deliberately narrow `fetch_all()` allows -- extending that scope is a separate decision. Customer Support and Partner Support need a ticket view that doesn't exist in the connector at all (known gap from earlier this session).

**Current phase status:** Phase 4 -- 4 of 7 in-scope agents now genuinely run against live Fixera data. Remaining open items: extend the connector for ticket data (Customer/Partner Support) and schema metadata (Platform Governance) if those are wanted live too, and Partner Verification's sensitive-data design (still deferred).

**Next session's first task:** Either extend the connector (ticket view, schema-metadata access) to wire the remaining 3 agents, design Partner Verification's approach to `owner_national_id`/KYC documents, or move to a different phase/division (Personal, Learning, RII, Forex all still not started per CONTEXT.md's phase plan).

### 2026-07-23 — Ticket view added, 6 of 7 agents now live
**Completed:** added `ai_empire_tickets_summary` (6th connector view) reading `support_tickets`, same privacy rules as the other 5 (excludes `subject`/`message` free-text, `admin_note`, `user_name`/`user_email` PII; includes `refund_decision` since reading an already-made decision to communicate status is these agents' actual job, distinct from authorizing one).

- **Customer Support**: `run_support_queue_sweep()`. Verified against 4 real tickets -- a genuine, concerning finding: all 4 are customer-type, all breached SLA, open 500+ hours (20+ days). Also found and fixed a real gap: production uses a `"high"` priority value that wasn't in `SLA_HOURS_BY_PRIORITY` (was silently falling back to the default 24h tier) -- added an explicit 8h tier for it.
- **Partner Support**: `run_partner_support_sweep()`. Found and fixed a real bug while wiring to live data: `build_team_notification` referenced a nonexistent `partner_id` field -- the actual `support_tickets` column is `user_id` (confirmed via `information_schema`). Correctly returns empty against real data (no partner-type tickets exist yet -- verified by inspecting the actual 4 rows, not just trusting an empty result).

**Current phase status:** Phase 4 -- 6 of 7 in-scope agents now genuinely run against live Fixera data (Service Delivery, Financial Operations, Trust & Safety, Marketplace Intelligence, Customer Support, Partner Support). Only Platform Governance remains mock-based, needing `information_schema` access the connector deliberately doesn't provide. Partner Verification remains fully deferred.

**Next session's first task:** Decide whether Platform Governance needs live schema-metadata access (a deliberate connector-scope extension, not a quick add) or stays mock-based long-term since its job is inherently about comparing documentation against reality, which mock data can't really simulate. Otherwise: design Partner Verification's approach, or move to a different phase/division.

### 2026-07-24 — Fixera onboarding rebuilt to match real legal requirements; Partner Verification agent built and wired live (all 8 Fixera agents now real)

**Fixera onboarding (C:\fixera\worker\src\pages\auth\OnboardingPage.jsx, separate repo, not committed to git yet):** Before designing Partner Verification, read Fixera's actual legal/policy docs (`FIXERA-LEGAL-DOCUMENTATION-CORRECTED.txt` Sections 2/3/5, `DEPOSIT-RULES-AND-REGULATIONS.md`, `DEPOSIT-COMMISSION-DEDUCTION-RULES.md`, `WALLET-SYSTEM-BLUEPRINT.md`) to ground both the onboarding form and the verification agent in Fixera's real Partner-Specific Agreements rather than assumptions. Key finding: the wallet-deposit-as-commission-pool model is explicitly scoped to Service Workers & Riders ONLY (Master Partner Agreement §5) -- Vendors/Suppliers/Movers/Water Carriers pay the same flat KSh 500 deposit but settle via monthly bank transfer / weekly M-Pesa B2C instead, at 20% commission (vs 15% for workers/riders). Relevant if Financial Operations' wallet-depletion logic is ever extended to those 4 types.

Rebuilt onboarding for all 6 partner types against the real per-type checklist (§3/§5 of the legal doc):
- **Movers/water carriers** (already built pre-session): added Business Operating License, company portfolio, crew safety-equipment + GPS-tracking declarations (movers); Health/Fitness Certification + Background Check Clearance (water carriers).
- **Riders**: added Date of Birth (18+ proof), Proof of Residence, Background Check Clearance -- riders previously had *zero* background-check control despite handling customer items, a real gap found by comparing against the Rider Specific Agreement. Vehicle insurance flipped from optional to required.
- **All service workers (plumbing/electrical/painting/cleaning) + riders**: background checks now require an issue date via a shared `BackgroundCheckField` component, with an inline warning if the certificate is older than 6 months (per explicit user policy). Added optional SHA (Social Health Authority) number + compliance certificate fields.
- **Vendors/Suppliers**: added KRA PIN certificate, Tax Compliance certificate, Business Operating/Trading License, Business Address Proof uploads; a new "Insurance & References" step (public/product liability insurance, 3+ professional references, reusing the same references array pattern movers use); itemized 5-policy checklist (previously a passive, non-interactive bullet list).
- **Real bug found and fixed**: `buildServiceDetails()` for suppliers read from `data.supplierBizRegUrl`/`data.supplierBizRegNumber`, two state fields no form control ever wrote to (the actual Business step writes to the shared `bizRegUrl`/`bizRegNumber`). Every supplier who completed onboarding would have had business registration silently dropped from `service_details`. Fixed; dead state fields removed.
- All changes lint-clean (only 4 pre-existing, unrelated errors) and `vite build` verified after every edit. Not yet committed to Fixera's git repo (separate decision, not made this session).

**Partner Verification agent (agents/fixera/partner_verification.py): built, unit-tested, and wired to live data.** This was the one deliberately-deferred agent all session, blocked on a safe design for `service_details`/KYC handling. Design (confirmed with user before touching Fixera's DB, same process as every other connector change):

- New Postgres function `ai_empire_redact_to_presence(jsonb)` (in Fixera's own DB) recursively walks `workers.service_details` and replaces every string leaf with a presence boolean -- except keys ending `ExpiryDate` (redacts to "is this date still in the future," i.e. not yet expired) and other keys ending `Date` (redacts to "is this date within the last 6 months," i.e. recently issued -- matches the *BgCheckDate fields added to onboarding above). Booleans (consent checkboxes) and arrays (crew/references) pass through structurally, recursing into their elements. No raw ID numbers, photo URLs, phone numbers, or names ever cross into AI_EMPIRE.
- New 7th connector view `ai_empire_partner_verification_summary` (role, verification_status, onboarding_complete, created_at, has_profile_photo/has_id_photo/has_tax_pin, redacted service_details) -- added to `_ALLOWED_VIEWS` as `"partner_verification"`, documented in `infrastructure/fixera_connector_reference.sql`.
- `agents/fixera/partner_verification.py`: per-role (and per-worker-service) requirements lists built directly from the legal docs' Sections 3/5, cross-referenced against exactly what the rebuilt onboarding form now captures. `check_partner()` returns every missing/stale item; `run_verification_sweep()` returns only partners with something missing. Unit-tested against mock data (clean partner, stale-cert partner, mover with no crew, empty vendor) before wiring live.
- **Corrected prompt boundaries**: the original v1 placeholder prompt said "routine approvals... may proceed," directly contradicting the user's explicit instruction that Mohamed is the sole approver and the agent only ever flags. Registered a v2 prompt with corrected boundaries (`fixera-partner-verification-v0.1`, prompt version v2) rather than editing v1 in place, since Boundaries are hash-locked against tampering; v1 deactivated, its file removed.
- **First live run surfaced a real, concerning finding**: the one existing partner record in Fixera's production DB has `verification_status: 'approved'` but `service_details` is entirely `NULL` and no profile/ID photo on file -- likely a legacy record predating this session's onboarding rebuild, flagged to the user for investigation, not auto-corrected (per design, this agent never touches `verification_status`).
- `agent_registry.lifecycle_stage` updated from `Design` to `Shadowing`.

**Current phase status (superseded, see next entry):** Phase 4 -- COMPLETE. All 8 Fixera agents (Service Delivery, Financial Operations, Trust & Safety, Marketplace Intelligence, Customer Support, Partner Support, Platform Governance, Partner Verification) have real logic; 7 of 8 run against live Fixera data end-to-end (Platform Governance stays mock-based, needs `information_schema` access the connector deliberately doesn't provide -- a distinct, deferred decision, not an oversight).

### 2026-07-24 (later same day) — Platform Governance wired live; Fixera repo cleanup, admin role split shipped, deploy pipeline gap found

**Platform Governance is now the 8th and final agent running against live data -- Phase 4 is genuinely fully complete, nothing mock-based remains.** User chose "extend the connector" over "stay mock-based permanently" for this one. Added 3 new `information_schema`-backed views (`ai_empire_schema_columns_summary`, `ai_empire_schema_triggers_summary`, `ai_empire_schema_views_summary` -- structure only, zero row data) as the connector's 8th/9th/10th views, plus `run_governance_sweep()` in `agents/fixera/platform_governance.py` using a `DOCUMENTED_COLUMNS`/`DOCUMENTED_TRIGGERS`/`DOCUMENTED_VIEWS` baseline. First live run correctly found exactly the 3 known real gaps (`can_receive_jobs` column, `trg_wallet_gate` trigger, `partner_wallet_status` view -- all documented in Fixera's own `enforce_wallet_minimum.sql`, none actually present in production), confirming the drift-detection logic works end-to-end.

**Fixera housekeeping, unrelated to AI_EMPIRE's own agents but done in the same session:**
- Found and deleted an empty, never-committed `web/secrate1.txt` in Fixera's repo (zero git history, zero risk, but a red flag worth killing on sight).
- Committed the 3 outstanding change sets sitting in Fixera's working directory: the onboarding rebuild (see prior entry), a pre-existing admin-role split (`support`→`support`/`partner_support`, `operations`→`service_delivery`/`platform_governance`/`marketplace_intelligence`, matching the AI Division org chart -- found already written but uncommitted from earlier in this same long session), and two small dark-mode hover fixes. Pushed to `origin/main`.
- **Found and fixed a real deploy-pipeline gap**: neither Fixera Vercel project (`partner-app` nor `project-xyk3n`) had GitHub auto-deploy connected -- every past deployment (going back months) was a manual `vercel --prod` CLI push by an agent session. This meant real fixes (e.g. an earlier "Fix Fixy AI chat auth" commit) were sitting in git for potentially a long time without ever reaching production. Manually deployed both apps to catch them up to the current commits. Walked the user through connecting GitHub properly (Vercel Project Settings -> Git -> Connect Git Repository) for a real auto-deploy pipeline going forward -- **this got stuck mid-setup** (Vercel's UI kept looping back to "install the GitHub app" even after GitHub confirmed the app was installed with `moh-sudo/fixera` access; team-level Apps page showed nothing; a fresh `vercel.com/new` import attempt hit a stuck blank page). Paused at the user's request -- unresolved, revisit with a fresh browser session. Manual `vercel --prod` deploys remain the working fallback in the meantime.
- Along the way, user found and deleted an old, unrelated personal GitHub account (`hit510`) that had zero collaborator access to `moh-sudo/fixera` (confirmed via the repo's own Collaborators & teams page before deletion) -- unrelated to Fixera, safe cleanup.
- Wrote `C:\fixera\PENDING-LEGAL-ADDENDUM-2026-07-24.md` -- a draft note (not legal text, doesn't touch any lawyer-drafted document) capturing two requirements added to the onboarding app this session that aren't yet reflected in Fixera's actual drafted legal docs (the 6-month background-check recency rule, SHA compliance), plus a note that 4 of the 5 policy checkboxes shown to partners don't yet correspond to separately-readable documents. For the user's upcoming lawyer/advocate consultation.

**Current phase status:** Phase 4 -- fully COMPLETE, all 8 Fixera agents live, nothing mock-based remains in this division. Legal addendum committed and pushed to Fixera's repo same day. Fixera onboarding form's live smoke-test still pending on the user's side (not yet reported back). Vercel GitHub auto-deploy setup for Fixera stays paused/unresolved.

### 2026-07-24 (later same day) -- Phase 5 started: Forex Division, 5 of 11 agents built and live

**Design corrected against the actual source documents before building anything.** User pushed back on an assumption-driven 9-agent sketch and insisted on checking `AI_EMPIRE_Master_Governance_v2.docx` / `AI_EMPIRE_Implementation_Roadmap_v1.docx` directly rather than guessing -- this caught a real, meaningful discrepancy. The authoritative design (governance doc section 3.1, roadmap section 5.4) specifies Forex as a 3-stage gate -- **Research (40%) -> Technical Analysis (30%) -> Trading Psychology (30%, runs BEFORE execution) -> Execution Gate (all 3 must pass, never silent reject, Law 4)** -- plus an explicitly-named **Trade Journal** logging to `memory_experience`. This is much leaner than the initially-sketched 9 independent agents. Also resolved a separate ambiguity: an overview table said Fixera was "Lead + 7 agents," but the detailed section (3.6) confirms 8 flat agents with no Lead role -- Fixera's existing build already matches spec correctly, no changes needed there.

**Final structure, per explicit user decision after seeing the real spec:** keep the fuller **11-agent** vision as a deliberate expansion on top of the base design -- Market Analytics, Strategy, Risk Management, Entry & Exit, Journaling, Psychology Coaching, Backtesting, News Filter, Performance Review, plus a standalone **Research Agent** (kept separate rather than folded into Market Analytics/News Filter) and a **CEO/Lead Agent** on top of all 10. The Lead role maps directly onto governance Law 12 (Chain of Command & Agent Authority Matrix -- Work Quality Authority, Deadlock Protocol escalates to Master Orchestrator on 2nd rejection, always reaches Mohamed, never silently blocks).

**Grounding data gathered from the user, not invented:**
- Read `JOURNEY OF MY FOREX TRADING.docx` (handwritten trading journal) directly -- real trading style (top-down ICT/SMC: daily/weekly bias -> 4H/1H structure -> FVG/BOS/CHOCH/OB -> liquidity/POI -> premium/discount), real traded pairs (EURUSD, GBPUSD, USDCAD, XAUUSD, NAS100, also monitors DXY), real session windows in NY time (Asian 8PM-5AM, London 2AM-11AM, New York 8AM-5PM -- journal said 5AM, treated as a likely typo), and real self-identified psychology patterns (entry-timing anxiety, panic, named distractions: phone/gossip/admiring/friends/family, sleep target 9:30PM-3:30AM, revenge-trading rule).
- Broker/execution reality: Exness, IC Markets, FundedNext -- none have native TradingView broker integration (not on TradingView's official Trading Panel list), so real execution will need a TradingView-webhook-to-MT4/5-bridge (proven third-party tools like PineConnector/TradersPost recommended over a custom build for the first pass, given real money is at stake). Entry & Exit deliberately deferred until Research/Strategy/Risk/Psychology are proven -- user explicitly confirmed demo/paper account first.
- News sources: ForexFactory + central bank RSS (Fed/ECB/BOE -- all free, no API key) confirmed working live; X/Twitter API confirmed technically feasible at pay-per-use pricing (~$7-30/month estimated for read-only polling of a few accounts) after 2026 pricing research; Financial Juice has no real public API (only an unofficial third-party scraper, not building on that); Bloomberg needs a paid Terminal subscription, out of scope for now.
- `OPENAI_API_KEY` confirmed still a placeholder -- `memory_experience`/`memory_knowledge` embeddings can't be generated yet. Not blocking: added `agents/forex/_memory_helpers.py` (safe_add_experience/safe_add_knowledge) that gracefully falls back to a NULL-embedding write via direct insert when the real embedding call raises `RuntimeError`, so real data accumulates now and just needs a future embedding backfill once a real key is added.

**5 of 11 agents built, unit-tested, and live-verified, all registered in `agent_registry`/`prompt_registry`:**
- **Research Agent** (`agents/forex/research.py`): live-tested against real ForexFactory calendar (71 real events) and Fed/ECB/BOE RSS feeds (20/15/50 real items respectively). Bank of Canada RSS tried but returned an empty feed -- CAD calendar coverage comes via ForexFactory instead. Filters to Medium/High-impact events on USD/EUR/GBP/CAD (the currencies relevant to the user's actual pairs). Publishes structured reports to `memory_knowledge`.
- **Strategy Agent** (`agents/forex/strategy.py`): started as a deterministic free-text `validate_setup()` checker against the journal's own ICT/SMC criteria (found and fixed a real bug during testing -- missing-session rejections had no explanatory note). Massively expanded mid-build after the user provided two large SMC and ICT reference documents plus a charting-toolkit reference -- now publishes 4 separate `memory_knowledge` entries (journal-sourced, SMC, ICT, toolkit) and adds `smc_entry_checklist()`, a 12-item discrete-typed-input checklist with a real numeric reward:risk >= 2.0 check and a direction-vs-pricing-zone contradiction check (buying at premium / selling at discount is explicitly flagged against the "buy cheap, sell expensive" principle). ICT-only concepts (displacement, daily bias distinct from raw HTF trend) are documented in the reference but deliberately not yet folded into their own checklist function.
- **Psychology Coaching Agent** (`agents/forex/psychology.py`): `pre_session_checkin()` and `post_loss_checkin()` grounded in the journal's own named patterns (sleep schedule, named distractions, revenge-trade language detection). Expanded after the user provided a 10-principle psychology reference (published to `memory_knowledge`) plus a 7-item `pre_trade_checklist()` -- a per-trade gate distinct from the once-per-session check, where 2 of the 7 items (calm/not-emotional, outcome-independence) are treated as individually critical since they're the most direct gateways to emotionally-driven losses.
- **Journaling Agent** ("Trade Journal", `agents/forex/journaling.py`): the one agent explicitly named in the original spec. `log_trade()` builds natural-language context (for future semantic search) plus structured metadata; `log_reflection()` covers the same 5 categories (mistake/profit/lesson/psychology/general) the user's existing TradeTrack tool and handwritten journal already use.
- **News Filter Agent** (`agents/forex/news_filter.py`): reuses Research's calendar fetch rather than duplicating it. Real bug found and fixed during testing -- the original version silently treated a feed outage (a genuine 429 rate-limit hit during testing, from repeated calls across agent tests) as "no news, safe to trade." Fixed to fail closed: `data_unavailable=True` + `should_pause=True` instead, so an unverifiable state is never mistaken for a confirmed-clear one -- directly implements the journal's own rule against trading during volatile news windows.
- **Risk Management Agent** (`agents/forex/risk_management.py`, added after the entry above): explicitly a discussion agent per Mohamed's own request, not silent enforcement (Law 4). Fetched FundedNext's real published rules directly from `fundednext.com/general-rules/cfds/trading-objectives` (WebFetch, not a third-party summary) -- confirmed Mohamed's actual account is Stellar Lite $10,000: 4% daily loss limit ($400), 8% *static* (non-trailing) drawdown floor ($800, fixed at account start), 8%/4% two-phase profit targets, 5 min trading days. `evaluate_fundednext_risk()` checks a proposed risk against both the remaining daily-loss buffer and the remaining static-drawdown buffer (correctly compounds prior same-day losses). Exness/IC Markets have no deposit yet ("depends on my pocket, not sure yet") -- `evaluate_personal_account_risk()` is purely advisory (0.5-1% guidance from the SMC/ICT references) and takes balance as an explicit per-call input rather than a stored size. Unit-tested, 6 cases including a compound prior-loss scenario, all correct. **Two personal overrides added on top of the reference material, per Mohamed's explicit instruction**: daily loss operative limit is his own $250, not FundedNext's actual $400 (both numbers still tracked/surfaced in the messaging); Strategy Agent's `smc_entry_checklist()` reward:risk minimum raised from the reference's 2:1 to his own 3:1 ("lose 100 gain 300 ... very safe very easy and repeatable").
- **Market Analytics Agent** (`agents/forex/market_analytics.py`): pulls real OHLC candles directly from a locally-running MT5 terminal via the official `MetaTrader5` Python package. Chosen over every third-party alternative evaluated in real depth this session -- Finnhub and Polygon/Massive (rebranded Oct 2025) both have free tiers that are 15-20 min delayed, real-time requires paying; TradingView has no public API at all, only unofficial scrapers (`tradingview_scraper`, 21 stars, "for educational purposes") or Chrome-DevTools desktop-automation MCP servers, both fragile and likely ToS-violating. MT5 is free, genuinely real-time, and is literally Mohamed's own broker's feed rather than a third-party approximation -- directly satisfies his explicit requirement to not be "behind the market candle." `classify_structure()` (pure logic, no MT5 dependency) does sliding-window swing-high/low detection and classifies uptrend/downtrend/ranging/unknown -- unit-tested with 5 synthetic scenarios, **two real bugs found and fixed**: (1) overlapping detection windows produced duplicate adjacent swing points at a single turning point, which broke the rising/falling comparison outright (an uptrend was misclassified as a downtrend); (2) `not rising` was wrongly treated as equivalent to `falling`, misclassifying flat/ranging price action as a downtrend -- fixed to a real three-way rising/falling/flat comparison.
- **Market Analytics live-verified same day**, once Mohamed installed MT5 and logged into an Exness demo account (server `ExnessKE-MT5Trial9`). **Found and fixed a real broker-naming gap**: Exness suffixes every symbol with `m` (EURUSD -> EURUSDm) and names the Nasdaq 100 `USTEC`, not `NAS100` -- hardcoding one broker's names would have broken on IC Markets/FundedNext. Added `resolve_symbol()`: dynamically finds the actual broker symbol for a clean pair name (prefix search for suffix variants, an explicit alias table for names that differ entirely like NAS100/USTEC), cached per process. Confirmed `mt5.symbols_get()` shows no crypto symbols at all on this specific account (forex/commodities/oil only, 318 symbols total) -- ruled out testing with a weekend-live crypto pair, used real EURUSDm H4 history instead (200 real candles, most recent bar exactly at Friday's weekend close, confirming genuinely current data). `run_market_analytics_sweep()` confirmed working end-to-end across all 5 traded pairs, logged to `memory_knowledge`. `lifecycle_stage` bumped from `Design` to `Shadowing`, matching the other 7.
- **Journaling Agent updated with account tagging** (`agents/forex/journaling.py` v0.2): per Mohamed's explicit instruction, the Exness demo account is meant to be genuine training/track-record history, not a throwaway log -- "I want it to become a training and learning opportunity for my forex agents... and also for this demo need to have its own journal basically the same as a real account." Added a required `account` field to `TradeLogEntry` (e.g. `exness_demo`, `fundednext_stellar_lite_10k`) and an optional one to `log_reflection()`. Re-tested, both log correctly with account tagging in context and metadata. This also sets the bar for the not-yet-built Performance Review Agent: it should track demo-account history as a real "readiness for real money" signal, not just a P&L summary -- Entry & Exit stays demo-only until there's an actual accumulated track record showing Research/Strategy/Risk Management/Psychology genuinely working together, not just until the code runs without erroring.

- **Backtesting Agent** (`agents/forex/backtesting.py`): grounded in the journal's own rule ("Practicing / BACKTASTING EVERY WEEKEND") and the SMC reference's "confidence comes from testing, not hope." Deliberately kept **separate** from Journaling's real/demo trade log (different `event_type`: `backtest_trade` vs `trade_closed`) so backtest results never get mixed into Performance Review's real-account readiness signal -- same reasoning as Journaling's account tagging, different kinds of history must stay distinguishable. `compute_stats()` (pure logic) computes win rate, profit factor, average achieved reward:risk, and expectancy -- reports the raw math plainly rather than inventing arbitrary quality tiers; the "30+ trades for a reliable sample" note is flagged explicitly as a general statistical heuristic, not something Mohamed specified. Unit-tested against a winning-edge sample (4 wins at 3:1 + 6 losses -> profit factor 2.0) and a losing-edge sample (profit factor 0.75) -- both correct, live DB writes confirmed.

- **Performance Review Agent** (`agents/forex/performance_review.py`): the agent that actually decides whether an account has earned trust for real money -- not a P&L summary, a fail-closed readiness gate. Required extending Psychology's `log_checkin()` with an optional `account` param first (v0.3, purely additive) so discipline history could be tied to a specific account, same as Journaling's trades. `assess_readiness()` requires all of: 30+ logged trades (same statistical heuristic as Backtesting, flagged as a heuristic not Mohamed's own number), profit factor > 1.0, at least some psychology check-in history, and a pause rate under 20% -- any one unmet means not-ready, never silently assumed ready, and every verdict comes with explicit reasons. Unit-tested across 5 scenarios (genuinely ready, too-few-trades, bad profit factor, no psychology data, high pause rate -- all correct) plus a live end-to-end test against real `exness_demo` data, which correctly returned NOT READY (1 real trade, profit factor 0.0, zero psychology check-ins yet) -- an honest reflection of the account's actual sparse state. This is explicitly the gate Entry & Exit needs to clear before it's trusted with anything beyond demo.

- **CEO/Lead Agent** (`agents/forex/ceo_lead.py`) -- **built ahead of Entry & Exit, deliberately reordered**: since Entry & Exit is still blocked on external decisions (Telegram/WhatsApp, an unvetted execution bridge) and gated on Performance Review's not-yet-met readiness bar anyway, CEO/Lead had no such blockers -- all 9 other agents already existed to coordinate over. Implements the real Execution Gate combination logic from governance Law 12 and the Forex Division's own design (Research + Technical Analysis + Trading Psychology all required, never silent rejection, always reaches Mohamed per Law 4): `evaluate_execution_gate()` requires every named gate to pass or it pauses with explicit per-gate reasons. `check_cross_agent_agreement()` implements the Deadlock Protocol -- distinguishes a genuine cross-agent contradiction (e.g. Strategy asserts bullish but Market Analytics' independently-computed structure says downtrend) from an ordinary single-gate failure, since Law 12 says a real disagreement should escalate rather than be silently resolved either way. `run_daily_briefing()` is the concrete coordination output: aggregates Research/News Filter/Market Analytics/Performance Review into one combined report instead of four separate pings -- **live-tested end-to-end successfully**, pulling real ForexFactory events, real Fed/ECB press items, real MT5 structure across all 5 traded pairs, and Performance Review's honest NOT READY status, all logged to `memory_knowledge` as one voice. Broad exception handling per section is deliberate (documented as such in the code) -- this is the top of the call stack whose entire job is "don't let one sub-system's failure take down the whole briefing," same fail-safe principle used throughout the division just applied across whole agents instead of within one. Unit-tested (6 cases: all-pass, one-gate-fails, no-inputs, agreement, genuine disagreement, unknown-value -- all correct).

**Still to build:** Only **Entry & Exit** remains -- deliberately last, demo-account-first, gated on Performance Review's readiness signal (currently NOT READY). 3 open-source TradingView-to-MT4/5 execution bridges already researched as candidates: niiisho/TradingView-MT5-Bridge (55 stars, 100% local, no internet exposure needed, best fit so far), Zypheronz/TradingView-Webhook-MT5-Bridge (0 stars, requires an internet-exposed endpoint, not recommended without much more scrutiny), marketcalls/OpenAlgo (broader platform, not yet evaluated in depth). Telegram vs WhatsApp for the eventual alert/command bridge still unconfirmed.

**Current phase status:** Phase 5 -- IN PROGRESS. **10 of 11 Forex agents built and fully live-verified** (all at `lifecycle_stage: Shadowing`). Only Entry & Exit remains, and it's intentionally the last piece -- blocked on external decisions rather than anything technical, and correctly gated shut by Performance Review's own honest readiness assessment. `TradingEconomics`/Bloomberg/Financial Juice remain unresolved for News Filter's future expansion (cost/access blockers, not technical ones).

**Next session's first task:** Get Mohamed's answer on Telegram vs WhatsApp and pick/vet an execution bridge (niiisho's TradingView-MT5-Bridge is the current front-runner), then build Entry & Exit -- the last Forex agent. Keep it demo-only until Performance Review actually reports READY for `exness_demo` (currently far from it: 1 trade, needs 30+ and a working psychology history). Also resume the paused Fixera Vercel-GitHub auto-deploy setup and follow up on the Fixera onboarding smoke-test whenever the user reports back.

### 2026-07-25 -- Mohamed's full handwritten forex notebook (42 pages, transcribed verbatim) ingested into Strategy/News Filter/Risk Management/Psychology

**What happened:** Mohamed provided a full verbatim transcription of his handwritten forex notebook (42 pages) mid-session, declining to settle the Telegram-vs-WhatsApp question first -- this session prioritized the notebook instead. Same pattern as the 2026-07-24 SMC/ICT/toolkit references: split by topic across the agents that already own that kind of content, rather than one giant blob, so each stays independently queryable in `memory_knowledge`.

**6 new `memory_knowledge` entries published, all live-verified (ids in the commit/session record):**
- **Strategy Agent** (3 entries): chart-reading fundamentals (timeframe selection, indicators, market structure, chart patterns, confluence, RR>=1:2, backtesting via TradingView replay); trendline strategy (swing-point-based trendline drawing, bounce-off-trendline + Stochastic cross-back confirmation, SL above swing high / TP 2x SL); time-and-price/ICT supplementary detail (precise EST kill-zone times distinct from the journal's broader NY-time session windows, HTF-vs-LTF Order Block roles, Market Maker Model/AMD, CRT, RTO, IPDA, and a detailed Inducement-identification rule: late BOS, in premium, internal not external, immediate rejection).
- **News Filter Agent** (1 entry): CPI/NFP/ISM Services PMI trading rules, the universal "wait 2-5 minutes after release, wait for candle close, wait for structure confirmation" rule.
- **Risk Management Agent** (1 entry): Mohamed's own daily/weekly/monthly/yearly profit-target ladder ($300/$1,500/$6,000/$72,000). His challenge-account math (8% of $10,000 = $800, 0.5-1% risk per trade) was checked against the existing `FUNDEDNEXT_STELLAR_LITE_10K` model and matches exactly -- confirms the existing numbers, nothing to change there.
- **Psychology Agent** (1 entry): personal pre-trading mindset notes (calm mind, no fear/greed/overconfidence, small adaptable daily target, moral discipline, journaling as key to success).

**New deterministic functions added, unit-tested (throwaway `_tmp_verify_notebook_batch.py`, same pattern as `_tmp_verify_strategy.py`):**
- `agents/forex/strategy.py`: `asian_range_strategy_checklist()` (the Asian Range Break & Reversal / London-NY kill-zone strategy, a full 5-item discrete checklist -- mark the Asian range only before 12AM NY, wait for London's sweep, BOS/CHoCH, entry from the OB/FVG that created, target the opposite side); `ema_stochastic_signal()` (200EMA trend filter + Stochastic oversold/overbought-with-cross-back signal); `dxy_bias_check()` (DXY direction vs proposed pair direction, flags when a setup "fights DXY" -- USDCAD/XAUUSD extended via USD-is-base logic since only EURUSD/GBPUSD/USDJPY were explicitly named, flagged as inferred rather than hiding that distinction).
- `agents/forex/news_filter.py`: `interpret_indicator_surprise()` (actual-vs-forecast for PMI/NFP/CPI-core/unemployment-rate/claims/wages -> expected USD/XAUUSD/EURUSD-GBPUSD direction); `post_news_reentry_status()` (fake-move-window / confirmation-window / clear-for-structure-check phases from the universal post-release wait rule -- a real gap the existing `should_pause_for_news()` never covered, since that only gates *before* a release, not what to do after one fires).
- `agents/forex/risk_management.py`: `check_daily_target_status()` (profit-side counterpart to the existing daily-loss check -- a real stop-trading-for-the-day cap once the $300 target is hit, per Mohamed's own explicit rule, not a soft goal).
- `agents/forex/psychology.py`: **found and fixed a real gap** while transcribing the mindset notes -- his own notes say "No fear, No Greed, No over confidence" but `pre_session_checkin()`'s bad-state keyword list only ever had fear/overconfident/panic/stress; "greed" was missing despite being one of his own three named things to avoid. Added.

`agent_registry.metadata.notes` updated for all 4 touched agents (Strategy v0.4, News Filter v0.2, Risk Management v0.3, Psychology v0.4), same running-snapshot convention as prior sessions.

**Current phase status:** Phase 5 -- unchanged structurally (still 10 of 11 agents built, Entry & Exit still the only one remaining). This session was knowledge-enrichment across 4 existing agents, not new-agent work.

**Next session's first task:** Unchanged from the entry above -- get Mohamed's answer on Telegram vs WhatsApp, vet an execution bridge, then build Entry & Exit.

### 2026-07-25 (later still) -- Two more strategies dictated live, added to Strategy Agent

**First Candle Rule** (`first_candle_rule_checklist()`, `FIRST_CANDLE_RULE_REFERENCE_TEXT`): opening-range break strategy anchored to the 9:30-9:35 AM NY cash-market open (most relevant to NAS100 among currently traded pairs) -- mark the opening candle's high/low, drop to the 1-minute chart, wait for a break confirmed specifically by a Fair Value Gap (not a candle close or wick alone), stop at the first candle closed outside the range, no need to wait for a retrace into the FVG. Mohamed says this alone made him over $1,000 in a single month. The dictated reward:risk ("six six two to one") was ambiguous in transcription -- confirmed directly with Mohamed as 1:2 rather than guessed, since this is a real number that decides position sizing; kept as its own `MOHAMED_FIRST_CANDLE_MIN_REWARD_TO_RISK` distinct from the SMC checklist's stricter personal 3:1.

**Daily Bias / ICT 2022 Model** (`daily_bias_ict2022_checklist()`, `DAILY_BIAS_ICT2022_REFERENCE_TEXT`): Mohamed describes this as the single strategy that made him a profitable trader ($40,000 in a month, by his own account) -- 6 daily levels (previous day high/low, Asian session high/low, London session high/low) marked each day; after the 9:30 AM NY open, one typically gets swept. Two valid outcomes modeled as distinct scenarios: the standard ICT 2022 Model reversal (sweep -> displacement/FVG opposite the sweep -> retracement into the FVG -> continuation to the opposite liquidity target), and -- his own emphasized case, credited with actually making him profitable -- a failed-reversal continuation, where the reversal attempt gets invalidated and price continues in the original sweep direction instead. Modeled as a real valid scenario (`failed_reversal_continuation`), not a rejected setup, since he was explicit this is "the most explosive" of the two. No fixed reward:risk was given for this strategy -- deliberately left ungated rather than inventing a number.

Both unit-tested (throwaway `_tmp_verify_first_candle_rule.py` / `_tmp_verify_daily_bias_ict2022.py`, same pattern as the notebook batch) and published live to `memory_knowledge`. `agent_registry` metadata for `forex-strategy-v0.1` updated to v0.6.

**Current phase status:** Phase 5 -- still structurally unchanged, still knowledge-enrichment on Strategy specifically, not new-agent work.

**Next session's first task:** Unchanged -- get Mohamed's answer on Telegram vs WhatsApp, vet an execution bridge, then build Entry & Exit. If more strategies keep arriving, keep following the same split-by-topic-and-confirm-ambiguous-numbers pattern rather than batching a big backlog.

### 2026-07-25 (later still) -- Entry & Exit built: Phase 5 is now structurally complete, all 11 Forex agents exist

**Telegram confirmed** (not WhatsApp) -- free bot API, no business-account friction, easiest to self-host.

**Execution bridge vetted, then found unnecessary.** niiisho/TradingView-MT5-Bridge checked directly (not just recalled from prior research): MIT license, 55 stars/12 forks/30 commits, no open issues, fully local architecture (Chrome extension -> localhost:8080 -> MT5 EA polling, no internet-exposed endpoint), actively maintained (v2.0.1). No independent reviews found beyond the repo itself, but the architecture claim is sound and verifiable. **Decided not to use it**: that bridge exists to relay TradingView Pine Script alerts into MT5. This system's signals already originate in Python (Strategy/CEO-Lead agents), and Market Analytics already has a live, working MT5 connection via the official `MetaTrader5` package -- so Entry & Exit calls `mt5.order_send()` directly, reusing Market Analytics' `connect()`/`resolve_symbol()`. Removes an entire dependency (Chrome extension, local HTTP relay, an extra always-running process) for no loss of capability.

**`agents/forex/entry_exit.py` built -- the 11th and final Forex agent, registered (`forex-entry-exit-v0.1`, lifecycle `Shadowing`).** Combines CEO/Lead's Execution Gate verdict, Risk Management's risk verdict, and its own account-permission check into one tradeable/not-tradeable decision (`build_trade_proposal()` / `is_proposal_tradeable()`), formats it for Telegram (`format_telegram_message()` / `send_telegram_alert()`), and only ever touches MT5 through `execute_order()`.

Three hard safety rules enforced in code, not just documented: (1) `execute_order()` refuses unless `confirmed=True` is passed explicitly -- Mohamed's own go-ahead per governance Law 4, never inferred from a passing gate; (2) real accounts (FundedNext, live Exness/IC Markets) stay blocked from trading at all until Performance Review reports that specific account READY -- demo accounts are always allowed, since that's how the readiness track record itself gets built (verified live: a real `check_execution_allowed()` call against `fundednext_stellar_lite_10k` correctly returned blocked, calling the real Performance Review agent); (3) before sending an order, the connected MT5 terminal's server name is checked against the proposal's account and refuses on any mismatch, rather than silently firing on whatever account happens to be logged in.

**Unit-tested (11 cases, `_tmp_verify_entry_exit.py`):** demo-always-allowed, unknown-account-refused, real-account-correctly-blocked (live DB call), full-pass tradeable, gate-fail/risk-breach/real-account-not-ready all correctly not-tradeable, message formatting, Telegram graceful-no-credentials-yet, and `execute_order` refusing both on missing confirmation and on an untradeable proposal -- all verified to happen *before* any MT5 connection is attempted.

**Deliberately NOT yet done, and flagged rather than rushed:** (1) live MT5 order execution itself -- needs a running terminal and Mohamed's explicit go-ahead before firing even a demo trade, not something to trigger unattended; (2) Telegram sending -- needs `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID` in `.env`, which requires Mohamed to create a bot via @BotFather and share the token (an external account-creation step this session can't do on his behalf); (3) the human-confirmation UX is currently a plain function argument (`confirmed=True`), not a live two-way Telegram reply listener -- that needs persistent-process infrastructure (same category as `agents/audit/server.py` + n8n) and is deliberately deferred to v0.2 rather than scope-creeping this build.

**Current phase status: Phase 5 (Forex Division) is now structurally COMPLETE -- all 11 agents exist and have real, unit-tested logic.** Nothing left to build; what remains is operational wiring (Telegram credentials) and earning trust (Performance Review readiness, currently NOT READY for every account) before Entry & Exit is ever allowed to fire for real, exactly as designed.

**Next session's first task:** Get `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID` from Mohamed (walk him through @BotFather + finding his chat id) and add to `.env`. Once that's live, test `send_telegram_alert()` end-to-end. Separately, whenever Mohamed is ready, do one explicit, supervised live-fire test of `execute_order()` against the `exness_demo` account with his direct go-ahead in the room -- not something to run unattended. Otherwise: resume the paused Fixera Vercel-GitHub auto-deploy setup, follow up on the Fixera onboarding smoke-test, or move to a different division (Personal, Learning, RII all still not started per this file's phase plan).

### 2026-07-26 -- Telegram wired up and live-verified; local repo pushed to GitHub for the first time

**Telegram bot created and tested end-to-end.** Mohamed created the bot via @BotFather himself and saved the token directly into `.env` (never pasted in chat, for good reason -- verified present without ever printing it back). Chat ID (`5180861581`, private chat `momo_T9`) fetched via `getUpdates` after Mohamed messaged the bot once. `send_telegram_alert()` sent a real test message, confirmed delivered. `agent_registry` for `forex-entry-exit-v0.1` updated to v0.2. Still open: MT5 order execution itself remains untested (needs a live supervised go-ahead, not something to trigger unattended), and the two-way Telegram confirm/reject loop is still deferred v0.2 infrastructure work -- the actual confirm step today is still the `confirmed=True` code argument, not a Telegram reply.

**Local repo connected to GitHub for the first time and pushed.** This local `C:\moh-sudo` repo had never had a remote configured -- all 5 phases of work had only ever existed on Mohamed's machine. Investigated the GitHub repo Mohamed thought this should go to (`moh-sudo/moh-sudo`) before pushing anything: turned out to be unrelated leftover work -- Fixera frontend HTML mockups (a landing page plus a fuller "Justlife-style" app UI redesign sitting in an unmerged PR), not the AI_EMPIRE codebase, and with no `main`/`master` branch at all. Rather than overwrite or reuse a misleadingly-named repo, Mohamed created a fresh empty repo (`moh-sudo/AI-EMPIRE`) and this local repo was connected to it as `origin` and pushed -- all 3 existing commits (Fixera Partner Verification/Platform Governance, the full Forex Division build, the CONTEXT.md log) now live on GitHub, local and remote confirmed matching at the same commit hash. The old `moh-sudo/moh-sudo` repo was left untouched.

**Current phase status:** Phase 5 -- Entry & Exit's operational wiring is now one step further along (Telegram done); still gated on Performance Review readiness and a supervised live-fire test before it can act on anything beyond visibility.

**Next session's first task:** Whenever Mohamed is ready, do one explicit, supervised live-fire test of `execute_order()` against `exness_demo` with his direct go-ahead in the room. Otherwise: resume the paused Fixera Vercel-GitHub auto-deploy setup, follow up on the Fixera onboarding smoke-test, or move to a different division (Personal, Learning, RII all still not started per this file's phase plan). Remember to `git push` after future local commits now that a remote actually exists.

### 2026-07-26 (later) -- CEO/Lead briefing now reaches Telegram, both scheduled and on-demand

Mohamed asked how to check "how's the market today" without being at his trading setup, and asked for both a scheduled push and an on-demand chat trigger, plus free-form Q&A. Free-form Q&A was explicitly deferred -- checked `OPENAI_API_KEY` and confirmed it's still a placeholder (10 characters, not a real key), a known gap since Phase 2 -- so anything needing an actual language model stays out of scope until a real key exists. What was built instead reuses only deterministic, already-built agents (Research/Market Analytics/News Filter/Performance Review via `run_daily_briefing()`), no AI-generated opinions involved.

**Built:**
- `run_daily_briefing_and_notify()` (`agents/forex/ceo_lead.py`) -- wraps `run_daily_briefing()` and delivers it over Telegram, with `_chunk_for_telegram()` splitting on section boundaries first (only hard-splitting a single oversized section as a last resort) to respect Telegram's 4096-character message limit. Unit-tested (short text, multi-section long text, single oversized section -- all correct).
- `agents/forex/telegram_listener.py` -- the on-demand half. `check_for_briefing_requests()` polls Telegram's `getUpdates`, tracks the last-processed update id in a local JSON file (a documented limitation for a single-machine setup, not hidden -- harmless here since the only effect of ever reprocessing an old message is re-sending a briefing, not a destructive action), and restricts triggering to Mohamed's own `TELEGRAM_CHAT_ID` -- any other sender's messages are consumed (to advance the offset) but never act.
- `agents/forex/server.py` -- FastAPI wrapper (port 8002) exposing `/run-briefing` (scheduled) and `/check-telegram` (on-demand polling target), same reasoning as `agents/audit/server.py`: this n8n installation has no shell-execution node.
- Two n8n workflows (built, **not yet activated**): `forex-ceo-briefing-scheduled.json` (cron `0 9 * * *` and `0 15 * * *` -- n8n runs in this machine's system timezone, EAT/UTC+3, confirmed via `date`; 9:00/15:00 EAT = 2AM/8AM NY only while NY observes EDT, roughly March-November -- during EST the real NY-time equivalent shifts by an hour, documented rather than silently wrong) and `forex-ceo-briefing-telegram-poll.json` (every 30s).

**Live-verified, unintentionally but conclusively:** a test script reset the local offset file, which caused `check_for_briefing_requests()` to re-see Mohamed's earlier test message as new and genuinely trigger `run_daily_briefing_and_notify()` -- a real briefing was generated (fresh ForexFactory/central-bank data) and actually delivered to his Telegram. Confirmed via the resulting `memory_knowledge` row's timestamp. Full pipeline works end-to-end.

**Not yet done:** the two n8n workflows exist as files but aren't imported/activated in the running n8n instance yet, and `agents/forex/server.py` isn't running as a persistent process yet (needs `uvicorn agents.forex.server:app --port 8002`, same manually-started-for-now pattern as the Audit Agent's server).

**Next session's first task:** Import both n8n workflow JSONs into the running n8n instance, start `agents/forex/server.py` on port 8002, and activate both workflows. Then confirm a real scheduled push arrives at 9:00 or 15:00 EAT, and confirm the on-demand path works with a fresh, deliberate test message (not another accidental offset reset).

### 2026-07-26 (later) -- Two separate Telegram bots, OpenAI key added (billing not yet enabled)

**Split into two bots per Mohamed's explicit request:** he correctly flagged that Entry & Exit's trade-execution alerts and CEO/Lead's routine market briefings were sharing one bot/chat -- a real trade proposal needing his confirmation could get buried under a routine update. Refactored: `agents/forex/_telegram.py` now holds the shared `send_telegram(message, token_env, chat_id_env)` helper; Entry & Exit uses `TELEGRAM_BOT_TOKEN`, CEO/Lead uses a new, separate `TELEGRAM_CEO_BOT_TOKEN`. Both live-verified with real test messages after the refactor, delivered to their own respective chats. Same private chat_id (`5180861581`) works for both bots -- confirmed Telegram's private-chat id is tied to Mohamed's account, not the bot.

**Incident, handled transparently:** while verifying `TELEGRAM_CEO_BOT_TOKEN` was saved, a `grep` check printed the full `.env` line (token included) into tool output instead of just confirming presence -- a real mistake, caught and disclosed immediately. Mohamed rotated the token via BotFather before it was wired into anything; the exposed value was never used. Verification of secrets from this point on uses the same non-printing pattern used for the very first token (length/format check only, e.g. `len(token)`, `":" in token`, `key.startswith("sk-")`) -- never a raw grep/print of the value.

**Mohamed asked for both bots to "communicate like a normal person"** -- i.e. natural-language chat, not just fixed template text. This needs an actual LLM in the loop, which the whole Forex Division has deliberately avoided everywhere else (every agent so far is rule-based/deterministic, precisely so nothing said is invented). Checked Ollama as a free local alternative first (already referenced in this project's own Phase 1 governance docs, part of the intended Hybrid Router design) -- not installed on this machine (`ollama: command not found`), would need a fresh install + a multi-GB model download. Mohamed chose to go with OpenAI instead, framing it as the paid half of a hybrid setup with Ollama addable later when actually needed.

**`OPENAI_API_KEY` updated to a real key** (`sk-proj...`, 164 chars, verified present without ever printing it). Live test call to `gpt-4o-mini` failed with `insufficient_quota` (429) -- the key is valid but the OpenAI account has no billing/credit set up yet. **Blocked on Mohamed adding a payment method + credit at platform.openai.com/settings/organization/billing before any conversational layer can actually be built and tested.**

**Current phase status:** Phase 5 -- still structurally complete. This session was entirely operational/delivery-layer work (Telegram bot separation, OpenAI key added) plus laying groundwork for a future conversational layer, not new agent logic.

**Next session's first task:** Once Mohamed confirms OpenAI billing is set up, re-run the `gpt-4o-mini` test call to confirm real quota works, then design the conversational layer -- almost certainly reusing the existing prompt boundaries system (identity/mission/boundaries/workflow, hash-locked) so each bot can converse naturally while staying constrained to its own actual job, matching Mohamed's own "communicate like a normal person but do their job respectfully" framing. Otherwise: the still-open n8n activation step from the entry above, or resume Fixera's paused items.

### 2026-07-26 (end of session) -- Agenda for next session, machine put to rest

Mohamed listed several things to pick up next time, explicitly deferred rather than built this session:

1. **Alert-timing correction for the scheduled briefing.** Currently `forex-ceo-briefing-scheduled.json` fires twice (9:00/15:00 EAT = 2AM/8AM NY during EDT -- London open and NY open). Mohamed wants a ping at **all three** session opens instead -- Asian, London, AND New York (three alerts, not two). Needs the Asian-open EAT-equivalent worked out and a third Schedule Trigger node added.
2. **Per-pair trading timetable.** Mohamed wants a designed schedule for which of his traded pairs (EURUSD, GBPUSD, USDCAD, XAUUSD, NAS100) to focus on during which session/time window -- not yet discussed in any detail, needs a real conversation about his actual pair-to-session preferences before building anything.
3. **A Fixera "CEO" equivalent agent** -- something that chats/reports to Mohamed about Fixera's status, filling the same role Forex's CEO/Lead Agent plays for the Forex Division (aggregating other agents' output into one voice). Fixera's 8 agents (Service Delivery, Financial Ops, Trust & Safety, Platform Governance, Marketplace Intelligence, Customer Support, Partner Support, Partner Verification) currently have no equivalent aggregation/reporting layer -- each just runs its own sweep independently.
4. **A Fixera Marketing Agent** -- handles advertisement, video content, and posting across platforms. Entirely new scope, not part of Fixera's original 8-agent design; needs its own discussion of what "posting on all platforms" actually means in terms of real API access (which platforms, what content pipeline).
5. **Marketplace price regulation** -- something that oversees/regulates the prices vendors and suppliers set when listing their commodities on Fixera. Also new scope, needs discussion of what "regulate" means here (a hard cap? a flagging/review system? comparison against market rates?) before any design decision.

**LLM/OpenAI status, explicitly left as-is per Mohamed's own instruction:** `OPENAI_API_KEY` is a real key but billing/credit isn't set up yet (confirmed via a live `gpt-4o-mini` call returning `insufficient_quota`) -- Mohamed will handle billing whenever he's ready, no action needed until he says so. Ollama (the free local alternative) needs a more powerful machine than what's currently available -- also explicitly deferred, not abandoned.

**Machine put to rest at Mohamed's explicit request** (end of 2026-07-26 session): both long-running background processes -- the Audit Agent server (`agents/audit/server.py`, port 8001, running since 2026-07-23) and n8n itself (running since 2026-07-23) -- were stopped. **This means the daily 06:00 audit sweep will NOT fire until both are manually restarted** (matches this file's own existing note that neither persists across restarts yet -- this session just made that gap concrete by actually stopping them rather than them dying from a reboot). Nothing from this session's own work (Telegram bots, `agents/forex/server.py`) was left running either -- it was never started as a persistent process in the first place, only exercised via one-off test scripts that already exited on their own.

**Next session's first task:** Restart n8n and `agents/audit/server.py` (port 8001) first, before anything else, so the daily audit resumes. Then work through the 5-item agenda above in whatever order Mohamed wants to start -- none of them have any technical blocker, they're all genuinely just pending discussions/decisions, not stalled builds.

### 2026-07-26 (morning) -- Restarted n8n + Audit server, caught and fixed a permanent false-Red bug

Restarted both processes per the plan above (confirmed live: Audit server 200 OK on port 8001, n8n responding on port 5678 -- its `audit-agent-daily` workflow was already active from before, n8n's workflow activation state survives a process restart since it's stored in n8n's own local DB). Since both were down overnight, today's scheduled 06:00 audit never fired -- ran it manually to cover the gap instead.

**That manual run came back Red.** Traced it to a single `routing_logs` row (`agent_id: test-anomaly-injector`, dated 2026-07-22) -- a synthetic row deliberately inserted back when `check_unsanitized_cloud_routing()` was first built, specifically to verify the check could detect a real violation (documented in this file's own 2026-07-23 Phase 3 entry: "each of the 4 checks individually triggered via deliberate test rows"). That row was never cleaned up afterward.

**Real, permanent bug found in the process:** unlike the other 3 checks (`error_rate_24h` is 24h-windowed, `missing_audit_fields` is 24h-windowed, `stale_agent_reviews` only looks at currently-active/overdue records), `check_unsanitized_cloud_routing()` (`agents/audit/checks.py`) has **no time window at all** -- it scans the entire history of `routing_logs`. Left alone, that one 4-day-old test row would have triggered a false Red on every single future daily audit, forever. Mohamed chose to delete the stale row rather than also time-bound the check itself -- so the check's all-time lookback is being kept as intentional (any historical unsanitized-cloud-routing event of CONFIDENTIAL+ data really is worth surfacing until someone actually looks at it), but this means **any future test/synthetic data written to `routing_logs` needs to be cleaned up afterward, or it will permanently poison the daily audit the same way.**

Deleted the stale row, re-ran the sweep, confirmed Green. Mohamed's own inbox will have a Red alert email from the first (uncleaned) run this morning -- that's the system correctly doing its job on the data it had at the time, safe to disregard now that the underlying cause is resolved.

**Next session's first task:** Continue with the 5-item agenda from the entry above (alert-timing correction, per-pair timetable, Fixera CEO-equivalent agent, Fixera Marketing Agent, marketplace price regulation). If any future Phase testing writes synthetic rows to `routing_logs` (or similar tables the Audit Agent scans without a time window), delete them immediately afterward rather than leaving them for a future session to rediscover as a false alarm.

### 2026-07-26 (later) -- Alert-timing corrected to 3 pushes/day, all n8n workflows activated, a real live crash bug found and fixed

**Alert timing corrected per Mohamed's explicit instruction:** he reads charts in NY time for all 3 sessions (matches the existing `SESSION_WINDOWS` already in `strategy.py`), but wants notifications in his own local time (Nairobi/EAT). Added a 3rd Schedule Trigger to `forex-ceo-briefing-scheduled.json` for the Asian session open (8PM NY = 03:00 EAT), alongside the existing London (2AM NY = 09:00 EAT) and NY (8AM NY = 15:00 EAT) triggers -- now 3 pushes/day instead of 2. Same EDT-only caveat as before: these EAT times only match the stated NY times while NY observes daylight saving (roughly March-November).

**All 3 n8n workflows actually imported and activated for the first time** (`n8n import:workflow` + `n8n update:workflow --active=true` per workflow, then an n8n restart since the CLI warns changes need a restart to take effect while the server is running): `audit-agent-daily`, `forex-ceo-briefing-scheduled` (3 triggers), `forex-ceo-briefing-telegram-poll`. Along the way, found (via `n8n list:workflow`) a second, completely empty `audit-agent-daily` workflow (zero nodes) sitting in the database alongside the real one -- harmless dead weight from some earlier failed attempt, left inert since this n8n version's CLI has no `delete:workflow` command. Confirmed the on-demand poll is genuinely live by watching `agents/forex/server.py`'s own request log show repeated `/check-telegram` hits every ~30 seconds.

**A real, live bug was caught and fixed in the process.** One of those `/check-telegram` polls corresponded to an actual Telegram message Mohamed had sent, which correctly triggered `run_daily_briefing_and_notify()` -- but it crashed with `openai.RateLimitError` (429, insufficient_quota) instead of sending anything back. Root cause: `agents/forex/_memory_helpers.py`'s `safe_add_knowledge`/`safe_add_experience` were written to catch `RuntimeError` -- the exception `generate_embedding()` raises when `OPENAI_API_KEY` is a placeholder -- as the trigger for a graceful NULL-embedding fallback. Now that a real (but quota-exhausted) key is in `.env`, embedding generation fails with `openai.APIError` (RateLimitError is a subclass) instead, a completely different exception type the original `except RuntimeError` never caught -- so every memory write across the entire Forex Division started silently crashing instead of falling back, the moment the real key was added. Fixed by catching `(RuntimeError, APIError)` in both functions; re-verified live -- a write now succeeds with `embedding=None` exactly as originally designed. This was a genuine regression from adding the OpenAI key, not a new key-setup step causing it -- worth remembering that a "real but not fully working" credential can break more than a missing one does, since it changes which failure path code takes.

**Current phase status:** Phase 5 -- structurally unchanged. This was scheduling/infrastructure work plus a real bug fix, not new agent logic.

**Next session's first task:** Continue the remaining 4-item agenda (per-pair timetable, Fixera CEO-equivalent agent, Fixera Marketing Agent, marketplace price regulation). Also worth double-checking OpenAI billing status whenever Mohamed sets it up -- once quota is restored, `safe_add_knowledge`/`safe_add_experience` will start generating real embeddings automatically, no code change needed, but it's worth confirming a real embedding actually lands (not just the graceful NULL fallback) the first time after billing goes live.

---

## Operational Efficiency Standard (v1.0)
**Owner:** Systems & Automation Division (Reliability & Monitoring Agent)
**Placement:** Systems & Automation Division Operational Standard — NOT Enterprise Principles
**Subordinate to:** Constitution → Enterprise Principles (Sustainable Excellence, Proportionality) → this standard
**Core Principle:** "Nothing consumes compute unless there is work to perform."

### Work Classification
| Class | Definition | Examples | Max Latency |
|---|---|---|---|
| A — Immediate | Must execute immediately; blocks user flow | Customer booking, Payment, Login, Emergency Alert | <1 second |
| B — Near Real-Time | Asynchronous but visible | Notifications, Dispatch, Report Updates | <30 seconds |
| C — Background | Invisible to users; improves system intelligence | Embedding generation, Analytics, Vendor Reviews | Minutes/Hours |
| D — Maintenance | System upkeep; pauses if higher-priority work arrives | DB Vacuum, Index Rebuilding, Model Downloads | Scheduled Windows |

### Dynamic Load States (5)
- **Idle:** No requests. CPU near zero. Models unloaded.
- **Active:** Normal workload. All services available.
- **High Load:** Many requests. Class C/D jobs delayed; customer traffic prioritized.
- **Recovery:** Post-outage restoration sequence: DB → Router → Memory → Agents.
- **Maintenance:** Manual or scheduled. Only essential traffic accepted; everything else queued.

### Priority Queue
1. Security Incident, Human Authority Request
2. Customer Payment, Booking
3. Notifications, Dispatch
4. Analytics, Reporting
5. Retraining, Embeddings, Maintenance

### Smart Model Loading
- Small Models (<8B): remain loaded 30 minutes (low memory footprint)
- Large Models (>8B): unload after 5 minutes of inactivity
- Huge Models (>70B): never preload; load strictly on demand
- Frequently Used: remain "warm" during high-traffic periods; unload automatically overnight

### Circuit Breakers & Self-Healing
- Health states: Healthy → Warning → Open Circuit → Fallback → Recovery Test
- **Reliability & Monitoring Agent** performs health check every 5-10 minutes (Router, DB, n8n, Ollama)
- Automatic restart PERMITTED for stateless services: FastAPI router, Ollama, n8n
- Automatic restart NOT PERMITTED for database services (Supabase) — Monitoring Agent alerts Mohamed and holds all write operations until manual authorization. Risk of data corruption on mid-transaction restart.

### Energy-Aware Computing
- **Laptop environments (Phase 1-2 only):** Battery <20% → pause embeddings, model downloads, retraining. CPU >90% → pause analytics, reports, indexing.
- **GPU Server (Phase 8):** No battery rules. Replace with thermal/power-draw monitoring.
- GPU Busy: queue new AI requests rather than forcing a model load (all environments)

### Operational Compute Budgets
Stored in platform_settings.compute_budgets (JSONB) — configurable without code changes. Starting values:
- Embedding Updates: 20 min/day
- Analytics: 15 min/day
- Vendor Review: 10 min/day
- Knowledge Consolidation: 30 min/day

### Implementation Notes for Claude Code
- Add compute_budgets JSONB column to platform_settings table in Phase 1
- Reliability & Monitoring Agent is the owner of all health checks — register in agent_registry
- Circuit breaker state stored in Supabase (circuit_breakers table) so state survives restarts
- Priority queue implemented as n8n workflow priority + Supabase job_queue table
