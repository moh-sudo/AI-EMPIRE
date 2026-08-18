-- Fixes the real root cause of what was previously (mis)diagnosed as
-- a "pgvector + RLS" platform bug (see systems_automation_governance.md,
-- 2026-08-11 entry). Re-verified live 2026-08-18: memory_experience
-- (which ALSO has a pgvector VECTOR column) inserts fine under a
-- scoped role for forex specifically -- the failure is not about
-- vector columns at all.
--
-- Root cause, confirmed live: for any division/table combination
-- missing a SELECT grant, PostgREST's default insert behavior
-- (Prefer: return=representation) tries to SELECT the just-inserted
-- row back to return it, which re-checks RLS under SELECT-visibility
-- rules. With zero SELECT grant, that implicit check always fails,
-- surfacing as the exact same generic "new row violates row-level
-- security policy" error as a genuine WITH CHECK failure would, even
-- though the actual INSERT policy was passing correctly the whole
-- time. Confirmed directly two ways: (1) the same memory_knowledge
-- insert succeeds immediately when requesting Prefer: return=minimal
-- (skipping the RETURNING re-check entirely), and (2) memory_experience
-- inserts under forex_agent (which already has its own SELECT policy
-- from 0014) succeed, while the identical insert under personal_agent
-- (no SELECT policy) reproduces the exact same failure.
--
-- Fix: grant each division SELECT on its own rows only, mirroring
-- memory_experience's existing forex-only SELECT policy shape,
-- extended everywhere it's missing -- lets the RETURNING clause
-- succeed for a division's own just-inserted rows without opening
-- general read access to other divisions' data. Still genuinely
-- least-privilege: the read is inherently self-limited to exactly
-- what that division can already write.

-- ---------------------------------------------------------------------
-- memory_knowledge -- SELECT missing for all 5 divisions (INSERT-only
-- by original design in 0014).
-- ---------------------------------------------------------------------
GRANT SELECT ON memory_knowledge TO authenticated;

CREATE POLICY "five_divisions_select_own_memory_knowledge" ON memory_knowledge
  FOR SELECT TO authenticated
  USING (
    (auth.jwt() ->> 'app_role' = 'fixera_agent' AND division = 'fixera') OR
    (auth.jwt() ->> 'app_role' = 'forex_agent' AND division = 'forex') OR
    (auth.jwt() ->> 'app_role' = 'personal_agent' AND division = 'personal') OR
    (auth.jwt() ->> 'app_role' = 'learning_agent' AND division = 'learning') OR
    (auth.jwt() ->> 'app_role' = 'rii_agent' AND division = 'rii')
  );

-- ---------------------------------------------------------------------
-- memory_experience -- SELECT already exists for forex (0014); missing
-- for the other 4 divisions, which is why their inserts have been
-- failing under the same RETURNING mechanism.
-- ---------------------------------------------------------------------
CREATE POLICY "four_divisions_select_own_memory_experience" ON memory_experience
  FOR SELECT TO authenticated
  USING (
    (auth.jwt() ->> 'app_role' = 'fixera_agent' AND division = 'fixera') OR
    (auth.jwt() ->> 'app_role' = 'personal_agent' AND division = 'personal') OR
    (auth.jwt() ->> 'app_role' = 'learning_agent' AND division = 'learning') OR
    (auth.jwt() ->> 'app_role' = 'rii_agent' AND division = 'rii')
  );
