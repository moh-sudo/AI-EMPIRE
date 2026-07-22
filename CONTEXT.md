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
│   ├── fixera/             # Existing Fixera codebase integration
│   ├── admin/
│   └── dashboard/
├── agents/
│   ├── audit/
│   ├── rii/
│   ├── forex/
│   ├── personal/
│   ├── learning/
│   ├── systems/
│   └── fixera/
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

### PHASE 4 — Fixera MVP
Goal: Integrate existing codebase, close gaps.

- Connect existing Fixera app to new Supabase project
- Build sendCancellationConfirmation (currently missing — silent status flip)
- Migrate services.js → Supabase services table (verify DB is actual runtime source)
- Verify trg_wallet_gate trigger uses platform_settings.wallet_minimum (currently hardcoded 500 — fix this)
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
