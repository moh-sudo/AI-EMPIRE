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
