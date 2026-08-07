-- Phase 5 — Learning Division: SRS engine + Content Transformation
-- Ref: CONTEXT.md "PHASE 5 — Intelligence Divisions" (Learning Division)
-- Run in: AI_EMPIRE's own Supabase project (lkcfbmcjwmxxvtpjspgr) SQL Editor.

-- Simplified SM-2 spaced-repetition state lives directly on the card
-- (not a separate join table) -- a card has exactly one active review
-- schedule, no need for the extra join.
CREATE TABLE IF NOT EXISTS learning_cards (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  category TEXT NOT NULL,
  front TEXT NOT NULL,
  back TEXT NOT NULL,
  source_type TEXT,        -- 'paste' | 'url' | 'document' | 'video' | 'voice' | 'manual'
  source_reference TEXT,   -- URL, filename, etc. -- optional
  active BOOLEAN DEFAULT true,

  -- SM-2 state
  interval_days INTEGER DEFAULT 0,
  ease_factor NUMERIC(4,2) DEFAULT 2.5,
  repetitions INTEGER DEFAULT 0,
  next_review_date DATE DEFAULT CURRENT_DATE,
  last_reviewed_at TIMESTAMPTZ,

  created_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE learning_cards ENABLE ROW LEVEL SECURITY;
CREATE INDEX IF NOT EXISTS idx_learning_cards_next_review ON learning_cards(next_review_date) WHERE active = true;
CREATE INDEX IF NOT EXISTS idx_learning_cards_category ON learning_cards(category);
