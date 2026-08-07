-- Systems & Automation Division: least-privilege access via RLS + a
-- custom JWT claim, replacing the Postgres-role approach from
-- 0009_systems_agent_scoped_role.sql.
--
-- WHY: 0009's ai_empire_systems_agent role is real and correctly scoped,
-- but live testing (2026-08-06) found Supabase's Supavisor pooler rejects
-- its connections before they ever reach Postgres (confirmed via
-- Postgres's own logs showing zero trace of the failed attempts) -- a
-- real platform-level issue, not a credentials mistake. See
-- governance/policies/systems_automation_governance.md, Rule 1's status
-- note for the full diagnostic trail.
--
-- This migration achieves the exact same goal -- a compromised or buggy
-- Reliability & Monitoring Agent process cannot read or write anything
-- outside circuit_breakers/audit_vault, enforced by the database, not
-- application code -- through Supabase's REST API (PostgREST) instead of
-- a raw Postgres connection through Supavisor. This is the SAME
-- transport every agent in every division already uses successfully via
-- shared/db.py's create_client() (never had a connection issue), just
-- with a different, narrowly-scoped JWT instead of the all-powerful
-- service_role key. The 0009 role is left in place, unused but harmless,
-- documented as real infrastructure blocked on an external platform
-- issue rather than deleted.
--
-- The 'ai_empire_systems_agent.lkcfbmcjwmxxvtpjspgr' role stays exactly
-- as-is from 0009 -- this migration does not touch it.

-- Base table privileges for the 'authenticated' Postgres role (the
-- standard Supabase role for any request carrying a valid signed JWT).
-- This alone does NOT open real access -- there are no real end-users of
-- this project, and even if added later, the RLS policies below gate
-- every row/operation on a specific custom claim regardless of who else
-- might authenticate as 'authenticated' in the future.
GRANT SELECT, INSERT, UPDATE ON circuit_breakers TO authenticated;
GRANT SELECT, INSERT ON audit_vault TO authenticated;

-- circuit_breakers has no pre-existing RLS policies -- these permissive
-- policies fully define what's allowed; RLS's own default-deny covers
-- everything else (including DELETE, which is granted to no one).
CREATE POLICY "systems_agent_select_circuit_breakers" ON circuit_breakers
  FOR SELECT TO authenticated
  USING (auth.jwt() ->> 'app_role' = 'systems_agent');

CREATE POLICY "systems_agent_insert_circuit_breakers" ON circuit_breakers
  FOR INSERT TO authenticated
  WITH CHECK (auth.jwt() ->> 'app_role' = 'systems_agent');

CREATE POLICY "systems_agent_update_circuit_breakers" ON circuit_breakers
  FOR UPDATE TO authenticated
  USING (auth.jwt() ->> 'app_role' = 'systems_agent')
  WITH CHECK (auth.jwt() ->> 'app_role' = 'systems_agent');

-- audit_vault already has 2 permissive policies from Phase 1
-- (audit_vault_insert_only, audit_vault_select -- both USING/WITH CHECK
-- true, no TO clause so they apply to every role). Permissive policies
-- combine with OR, so simply adding another permissive policy would not
-- narrow anything -- those two would still let any request through
-- regardless of claim. RESTRICTIVE policies combine with AND instead,
-- which is what actually narrows effective access down to only requests
-- carrying the right claim, without editing or removing the existing
-- Phase 1 policies (currently inert for 'authenticated' anyway, since it
-- had no table grant until this migration -- left alone rather than risk
-- anything else relying on them).
CREATE POLICY "systems_agent_restrict_select_audit_vault" ON audit_vault
  AS RESTRICTIVE
  FOR SELECT TO authenticated
  USING (auth.jwt() ->> 'app_role' = 'systems_agent');

CREATE POLICY "systems_agent_restrict_insert_audit_vault" ON audit_vault
  AS RESTRICTIVE
  FOR INSERT TO authenticated
  WITH CHECK (auth.jwt() ->> 'app_role' = 'systems_agent');

-- UPDATE/DELETE on audit_vault stay fully blocked for 'authenticated' --
-- no GRANT for those operations above, RLS default-deny with zero
-- policies for them, and the existing BEFORE UPDATE/DELETE trigger from
-- 0003_audit_vault_immutability_trigger.sql blocks them unconditionally
-- regardless of role. Three independent layers, not just one.
