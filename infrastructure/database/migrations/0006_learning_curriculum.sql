-- Phase 5 — Learning Division: Curriculum tracking (AI Empire University)
-- Ref: Mohamed's full curriculum doc, 2026-08-03 -- 6-phase degree structure.
-- Run in: AI_EMPIRE's own Supabase project (lkcfbmcjwmxxvtpjspgr) SQL Editor.

CREATE TABLE IF NOT EXISTS curriculum_phases (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  phase_number INTEGER NOT NULL UNIQUE,
  name TEXT NOT NULL,
  goal TEXT,
  projects JSONB,       -- list of project names, from the source doc
  assessments JSONB,    -- list of assessment types, from the source doc
  created_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE curriculum_phases ENABLE ROW LEVEL SECURITY;

CREATE TABLE IF NOT EXISTS curriculum_subjects (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  phase_id UUID NOT NULL REFERENCES curriculum_phases(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  sequence_order INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'not_started',  -- not_started | in_progress | completed
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE curriculum_subjects ENABLE ROW LEVEL SECURITY;
CREATE INDEX IF NOT EXISTS idx_curriculum_subjects_phase ON curriculum_subjects(phase_id, sequence_order);
CREATE INDEX IF NOT EXISTS idx_curriculum_subjects_status ON curriculum_subjects(status);
