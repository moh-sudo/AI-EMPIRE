-- Extends the RLS + custom JWT claim pattern proven for Systems &
-- Automation (0010_systems_agent_rls_jwt.sql) to the 5 "simplest
-- slice" divisions: fixera, forex, personal, learning, rii. Deferred
-- to a later migration: audit (needs cross-division, unfiltered reads
-- on several tables -- a genuinely different access shape, not this
-- pattern) and the multi-writer tables (audit_vault, routing_logs,
-- agent_registry -- shared across divisions, no single exclusive
-- claim fits).
--
-- Scope for each division below is exactly what that division's own
-- code actually does today (confirmed via a real audit of every
-- .table() call, not guessed) -- matching Rule 1's "scoped to only
-- ...  nothing else" principle. A division that later needs a new
-- operation on one of these tables gets a new migration then, not a
-- speculative grant now.
--
-- All 6 tables below (memory_experience, memory_knowledge,
-- personal_habits, personal_habit_completions, learning_cards,
-- learning_card_links, curriculum_phases, curriculum_subjects,
-- rii_watchtowers) have RLS enabled but zero existing policies --
-- confirmed by checking every migration that created them. Unlike
-- audit_vault (which had 2 pre-existing wide-open permissive
-- policies, requiring RESTRICTIVE policies to actually narrow
-- anything), these need only simple PERMISSIVE policies, same as
-- circuit_breakers in 0010 -- there's nothing else to combine with.

-- ---------------------------------------------------------------------
-- memory_knowledge -- INSERT only, all 5 divisions. No division reads
-- this today (the semantic-search RPC functions that would read it
-- have zero callers anywhere in agents/ -- confirmed, not assumed).
-- ---------------------------------------------------------------------
GRANT INSERT ON memory_knowledge TO authenticated;

CREATE POLICY "five_divisions_insert_own_memory_knowledge" ON memory_knowledge
  FOR INSERT TO authenticated
  WITH CHECK (
    (auth.jwt() ->> 'app_role' = 'fixera_agent' AND division = 'fixera') OR
    (auth.jwt() ->> 'app_role' = 'forex_agent' AND division = 'forex') OR
    (auth.jwt() ->> 'app_role' = 'personal_agent' AND division = 'personal') OR
    (auth.jwt() ->> 'app_role' = 'learning_agent' AND division = 'learning') OR
    (auth.jwt() ->> 'app_role' = 'rii_agent' AND division = 'rii')
  );

-- ---------------------------------------------------------------------
-- memory_experience -- INSERT for all 5; SELECT additionally for
-- forex only, since forex's performance_review.py is the only one of
-- the 5 that actually reads it today (own-division rows only).
-- ---------------------------------------------------------------------
GRANT SELECT, INSERT ON memory_experience TO authenticated;

CREATE POLICY "five_divisions_insert_own_memory_experience" ON memory_experience
  FOR INSERT TO authenticated
  WITH CHECK (
    (auth.jwt() ->> 'app_role' = 'fixera_agent' AND division = 'fixera') OR
    (auth.jwt() ->> 'app_role' = 'forex_agent' AND division = 'forex') OR
    (auth.jwt() ->> 'app_role' = 'personal_agent' AND division = 'personal') OR
    (auth.jwt() ->> 'app_role' = 'learning_agent' AND division = 'learning') OR
    (auth.jwt() ->> 'app_role' = 'rii_agent' AND division = 'rii')
  );

CREATE POLICY "forex_agent_select_own_memory_experience" ON memory_experience
  FOR SELECT TO authenticated
  USING (auth.jwt() ->> 'app_role' = 'forex_agent' AND division = 'forex');

-- ---------------------------------------------------------------------
-- personal_habits / personal_habit_completions -- personal_agent only.
-- No division column (single-owner tables) -- the app_role claim
-- alone is the full predicate, same shape as circuit_breakers.
-- ---------------------------------------------------------------------
GRANT SELECT, INSERT, UPDATE ON personal_habits TO authenticated;

CREATE POLICY "personal_agent_select_personal_habits" ON personal_habits
  FOR SELECT TO authenticated
  USING (auth.jwt() ->> 'app_role' = 'personal_agent');

CREATE POLICY "personal_agent_insert_personal_habits" ON personal_habits
  FOR INSERT TO authenticated
  WITH CHECK (auth.jwt() ->> 'app_role' = 'personal_agent');

CREATE POLICY "personal_agent_update_personal_habits" ON personal_habits
  FOR UPDATE TO authenticated
  USING (auth.jwt() ->> 'app_role' = 'personal_agent')
  WITH CHECK (auth.jwt() ->> 'app_role' = 'personal_agent');

GRANT SELECT, INSERT ON personal_habit_completions TO authenticated;

CREATE POLICY "personal_agent_select_personal_habit_completions" ON personal_habit_completions
  FOR SELECT TO authenticated
  USING (auth.jwt() ->> 'app_role' = 'personal_agent');

CREATE POLICY "personal_agent_insert_personal_habit_completions" ON personal_habit_completions
  FOR INSERT TO authenticated
  WITH CHECK (auth.jwt() ->> 'app_role' = 'personal_agent');

-- ---------------------------------------------------------------------
-- learning_cards / learning_card_links / curriculum_phases /
-- curriculum_subjects -- learning_agent only.
-- ---------------------------------------------------------------------
GRANT SELECT, INSERT, UPDATE ON learning_cards TO authenticated;

CREATE POLICY "learning_agent_select_learning_cards" ON learning_cards
  FOR SELECT TO authenticated
  USING (auth.jwt() ->> 'app_role' = 'learning_agent');

CREATE POLICY "learning_agent_insert_learning_cards" ON learning_cards
  FOR INSERT TO authenticated
  WITH CHECK (auth.jwt() ->> 'app_role' = 'learning_agent');

CREATE POLICY "learning_agent_update_learning_cards" ON learning_cards
  FOR UPDATE TO authenticated
  USING (auth.jwt() ->> 'app_role' = 'learning_agent')
  WITH CHECK (auth.jwt() ->> 'app_role' = 'learning_agent');

-- learning_card_links needs UPDATE too (not just SELECT/INSERT) --
-- engine.py's link_cards() does an upsert (INSERT ... ON CONFLICT),
-- which requires UPDATE privilege for the conflict-resolution branch.
GRANT SELECT, INSERT, UPDATE ON learning_card_links TO authenticated;

CREATE POLICY "learning_agent_select_learning_card_links" ON learning_card_links
  FOR SELECT TO authenticated
  USING (auth.jwt() ->> 'app_role' = 'learning_agent');

CREATE POLICY "learning_agent_insert_learning_card_links" ON learning_card_links
  FOR INSERT TO authenticated
  WITH CHECK (auth.jwt() ->> 'app_role' = 'learning_agent');

CREATE POLICY "learning_agent_update_learning_card_links" ON learning_card_links
  FOR UPDATE TO authenticated
  USING (auth.jwt() ->> 'app_role' = 'learning_agent')
  WITH CHECK (auth.jwt() ->> 'app_role' = 'learning_agent');

GRANT SELECT, INSERT ON curriculum_phases TO authenticated;

CREATE POLICY "learning_agent_select_curriculum_phases" ON curriculum_phases
  FOR SELECT TO authenticated
  USING (auth.jwt() ->> 'app_role' = 'learning_agent');

CREATE POLICY "learning_agent_insert_curriculum_phases" ON curriculum_phases
  FOR INSERT TO authenticated
  WITH CHECK (auth.jwt() ->> 'app_role' = 'learning_agent');

GRANT SELECT, INSERT, UPDATE ON curriculum_subjects TO authenticated;

CREATE POLICY "learning_agent_select_curriculum_subjects" ON curriculum_subjects
  FOR SELECT TO authenticated
  USING (auth.jwt() ->> 'app_role' = 'learning_agent');

CREATE POLICY "learning_agent_insert_curriculum_subjects" ON curriculum_subjects
  FOR INSERT TO authenticated
  WITH CHECK (auth.jwt() ->> 'app_role' = 'learning_agent');

CREATE POLICY "learning_agent_update_curriculum_subjects" ON curriculum_subjects
  FOR UPDATE TO authenticated
  USING (auth.jwt() ->> 'app_role' = 'learning_agent')
  WITH CHECK (auth.jwt() ->> 'app_role' = 'learning_agent');

-- ---------------------------------------------------------------------
-- rii_watchtowers -- rii_agent only.
-- ---------------------------------------------------------------------
GRANT SELECT, INSERT, UPDATE ON rii_watchtowers TO authenticated;

CREATE POLICY "rii_agent_select_rii_watchtowers" ON rii_watchtowers
  FOR SELECT TO authenticated
  USING (auth.jwt() ->> 'app_role' = 'rii_agent');

CREATE POLICY "rii_agent_insert_rii_watchtowers" ON rii_watchtowers
  FOR INSERT TO authenticated
  WITH CHECK (auth.jwt() ->> 'app_role' = 'rii_agent');

CREATE POLICY "rii_agent_update_rii_watchtowers" ON rii_watchtowers
  FOR UPDATE TO authenticated
  USING (auth.jwt() ->> 'app_role' = 'rii_agent')
  WITH CHECK (auth.jwt() ->> 'app_role' = 'rii_agent');
