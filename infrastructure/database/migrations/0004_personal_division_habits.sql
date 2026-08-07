-- Phase 5 — Personal Division: Habit Tracker
-- Ref: CONTEXT.md "PHASE 5 — Intelligence Divisions" (Personal Division)
-- Run in: AI_EMPIRE's own Supabase project (lkcfbmcjwmxxvtpjspgr) SQL Editor.

CREATE TABLE IF NOT EXISTS personal_habits (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  name TEXT NOT NULL,
  active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE personal_habits ENABLE ROW LEVEL SECURITY;

CREATE TABLE IF NOT EXISTS personal_habit_completions (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  habit_id UUID NOT NULL REFERENCES personal_habits(id) ON DELETE CASCADE,
  completed_date DATE NOT NULL,
  completed_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(habit_id, completed_date)
);
ALTER TABLE personal_habit_completions ENABLE ROW LEVEL SECURITY;
CREATE INDEX IF NOT EXISTS idx_habit_completions_date ON personal_habit_completions(completed_date);
CREATE INDEX IF NOT EXISTS idx_habit_completions_habit ON personal_habit_completions(habit_id);
