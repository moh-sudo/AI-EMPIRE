-- Phase 1 — Platform Foundation
-- Ref: CONTEXT.md "Key Database Tables (Phase 1 priority)" + "Operational Efficiency Standard"

CREATE EXTENSION IF NOT EXISTS vector;

-- ---------------------------------------------------------------------
-- audit_vault — immutable, no UPDATE/DELETE allowed (Law 9)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_vault (
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
ALTER TABLE audit_vault ENABLE ROW LEVEL SECURITY;
CREATE POLICY "audit_vault_insert_only" ON audit_vault FOR INSERT WITH CHECK (true);
CREATE POLICY "audit_vault_select" ON audit_vault FOR SELECT USING (true);

-- ---------------------------------------------------------------------
-- routing_logs — every Hybrid Router decision, one row per request
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS routing_logs (
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

-- ---------------------------------------------------------------------
-- agent_registry — every agent, its lifecycle stage and clearances
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS agent_registry (
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

-- ---------------------------------------------------------------------
-- circuit_breakers — health state per service, survives restarts
-- Health states: Healthy -> Warning -> Open Circuit -> Fallback -> Recovery Test
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS circuit_breakers (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  service_name TEXT UNIQUE NOT NULL,
  state TEXT NOT NULL DEFAULT 'healthy'
    CHECK (state IN ('healthy','warning','open_circuit','fallback','recovery_test')),
  failure_count INTEGER NOT NULL DEFAULT 0,
  last_failure_at TIMESTAMPTZ,
  last_success_at TIMESTAMPTZ,
  auto_restart_permitted BOOLEAN NOT NULL DEFAULT false,
  opened_at TIMESTAMPTZ,
  metadata JSONB,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE circuit_breakers ENABLE ROW LEVEL SECURITY;

-- Seed the services this standard names explicitly.
-- Supabase itself is intentionally auto_restart_permitted = false (Law: no
-- automatic restart for database services — risk of mid-transaction corruption).
INSERT INTO circuit_breakers (service_name, auto_restart_permitted)
VALUES
  ('fastapi_router', true),
  ('ollama', true),
  ('n8n', true),
  ('supabase', false)
ON CONFLICT (service_name) DO NOTHING;

-- ---------------------------------------------------------------------
-- job_queue — priority queue backing n8n workflow priority
-- Work classes: A-Immediate, B-Near Real-Time, C-Background, D-Maintenance
-- Priority: 1 highest (Security/Human) .. 5 lowest (Retraining/Maintenance)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS job_queue (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  job_type TEXT NOT NULL,
  work_class TEXT NOT NULL CHECK (work_class IN ('A','B','C','D')),
  priority SMALLINT NOT NULL CHECK (priority BETWEEN 1 AND 5),
  status TEXT NOT NULL DEFAULT 'queued'
    CHECK (status IN ('queued','running','completed','failed','cancelled')),
  payload JSONB,
  division TEXT,
  agent_id TEXT,
  scheduled_for TIMESTAMPTZ DEFAULT NOW(),
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  error TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE job_queue ENABLE ROW LEVEL SECURITY;
CREATE INDEX IF NOT EXISTS idx_job_queue_status_priority
  ON job_queue (status, priority, scheduled_for);

-- ---------------------------------------------------------------------
-- platform_settings — business rules & thresholds live here, never hardcoded
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS platform_settings (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  key TEXT UNIQUE NOT NULL,
  value JSONB,
  compute_budgets JSONB NOT NULL DEFAULT '{
    "embedding_updates_min_per_day": 20,
    "analytics_min_per_day": 15,
    "vendor_review_min_per_day": 10,
    "knowledge_consolidation_min_per_day": 30
  }'::jsonb,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE platform_settings ENABLE ROW LEVEL SECURITY;

-- Note on RLS: circuit_breakers, job_queue, and platform_settings have RLS
-- enabled with no policies defined, so anon/authenticated roles get zero
-- access by default. Only the Supabase service_role key (used by the
-- FastAPI Hybrid Router backend) bypasses RLS. audit_vault and routing_logs
-- follow CONTEXT.md's explicit policies above; agent_registry currently
-- has RLS enabled with the same no-policy default pending an Access
-- Control Matrix policy set.
