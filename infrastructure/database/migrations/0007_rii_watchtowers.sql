-- Phase 5 — Research & Innovation Division: Watchtowers
-- Ref: CONTEXT.md "PHASE 5 — Intelligence Divisions" (RII Division)
-- Run in: AI_EMPIRE's own Supabase project (lkcfbmcjwmxxvtpjspgr) SQL Editor.

CREATE TABLE IF NOT EXISTS rii_watchtowers (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  topic TEXT NOT NULL,
  active BOOLEAN DEFAULT true,
  seen_urls JSONB DEFAULT '[]'::jsonb,  -- real URLs already surfaced, so re-checks only alert on genuinely new results
  last_checked_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE rii_watchtowers ENABLE ROW LEVEL SECURITY;
CREATE INDEX IF NOT EXISTS idx_rii_watchtowers_active ON rii_watchtowers(active);
