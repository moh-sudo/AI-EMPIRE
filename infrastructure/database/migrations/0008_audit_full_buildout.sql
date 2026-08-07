-- Audit & Verification Division -- full buildout (Security, Financial,
-- Performance, Reports, QA, Bug Detection). Ref: Mohamed's 7-area
-- request + Self-Healing Governance Policy, 2026-08-03.
-- Run in: AI_EMPIRE's own Supabase project (lkcfbmcjwmxxvtpjspgr) SQL Editor.

-- Performance Monitoring: real historical timings per division/operation,
-- so degradation can be detected against a real baseline, not a guess.
CREATE TABLE IF NOT EXISTS audit_performance_log (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  division TEXT NOT NULL,
  operation TEXT NOT NULL,
  duration_seconds NUMERIC(10,3) NOT NULL,
  ok BOOLEAN NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE audit_performance_log ENABLE ROW LEVEL SECURITY;
CREATE INDEX IF NOT EXISTS idx_audit_perf_division_op ON audit_performance_log(division, operation, created_at);

-- Bug Detection & Debugging: proposed fixes awaiting Mohamed's approval
-- (Self-Healing Governance Policy v0.1 -- every fix needs explicit
-- approval, no auto-deploy tier yet).
CREATE TABLE IF NOT EXISTS audit_bug_proposals (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  agent_id TEXT,
  division TEXT,
  symptom TEXT NOT NULL,          -- what was observed (the recurring failure pattern)
  root_cause TEXT,                -- Ollama diagnosis
  proposed_fix TEXT,              -- deliberately NULL in v0.1 -- fix-drafting stubbed
  risk_level TEXT DEFAULT 'unknown',
  status TEXT NOT NULL DEFAULT 'pending',  -- pending | approved | rejected | fix_unavailable
  created_at TIMESTAMPTZ DEFAULT NOW(),
  resolved_at TIMESTAMPTZ
);
ALTER TABLE audit_bug_proposals ENABLE ROW LEVEL SECURITY;
CREATE INDEX IF NOT EXISTS idx_audit_bug_status ON audit_bug_proposals(status);
