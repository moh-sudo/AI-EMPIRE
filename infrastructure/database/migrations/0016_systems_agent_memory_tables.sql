-- Extends the now-fixed memory_experience/memory_knowledge access
-- pattern (0015_memory_knowledge_select_fix.sql) to Systems &
-- Automation itself -- a separate, pre-existing gap noted while
-- fixing the other 5 divisions on 2026-08-18: Systems' own
-- agents/systems/_memory_helpers.py was still on the blanket key for
-- these two tables, unrelated to the pgvector misdiagnosis (it simply
-- never had its own scoped policy on them at all, unlike the other 5
-- divisions which had one from 0014 that turned out to be broken by
-- the missing-SELECT/RETURNING interaction).
--
-- Same shape as 0014/0015: INSERT for both tables, plus SELECT scoped
-- to systems' own rows only -- needed for the exact same reason 0015
-- fixed it for the other 5 divisions (PostgREST's default insert
-- behavior re-checks RLS under SELECT rules to return the inserted
-- row), not because Systems agents actually read these tables today.

-- Table-level GRANT SELECT, INSERT already exists on both tables from
-- 0014/0015 (for the "authenticated" role broadly) -- only new
-- policies are needed here, scoped to systems' own division.

CREATE POLICY "systems_agent_insert_own_memory_knowledge" ON memory_knowledge
  FOR INSERT TO authenticated
  WITH CHECK (auth.jwt() ->> 'app_role' = 'systems_agent' AND division = 'systems');

CREATE POLICY "systems_agent_select_own_memory_knowledge" ON memory_knowledge
  FOR SELECT TO authenticated
  USING (auth.jwt() ->> 'app_role' = 'systems_agent' AND division = 'systems');

CREATE POLICY "systems_agent_insert_own_memory_experience" ON memory_experience
  FOR INSERT TO authenticated
  WITH CHECK (auth.jwt() ->> 'app_role' = 'systems_agent' AND division = 'systems');

CREATE POLICY "systems_agent_select_own_memory_experience" ON memory_experience
  FOR SELECT TO authenticated
  USING (auth.jwt() ->> 'app_role' = 'systems_agent' AND division = 'systems');
