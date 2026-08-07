-- Systems & Automation Division: least-privilege Postgres role
-- Ref: governance/policies/systems_automation_governance.md, Rule 1
--      ("Declared Scope Only")
--
-- Runs against AI_EMPIRE'S OWN Supabase project (ref lkcfbmcjwmxxvtpjspgr),
-- same project every other migration in this directory targets.
--
-- WHY THIS EXISTS: shared/db.py's get_client() -- used by every agent in
-- every division today, including the new Reliability & Monitoring Agent --
-- authenticates with SUPABASE_SERVICE_KEY, which bypasses Row-Level
-- Security entirely (the same gap that required a hard trigger for
-- audit_vault's immutability, see 0003_audit_vault_immutability_trigger.sql).
-- Nothing at the database level currently stops that agent's code from
-- reading/writing agent_registry, routing_logs, or any other division's
-- memory tables -- the only thing preventing it is that the code wasn't
-- written to do so. Mohamed asked for this to be enforced for real, not
-- just documented, after hearing about real cases of agents quietly
-- exceeding their intended scope.
--
-- This role is Systems & Automation's equivalent of Fixera's
-- ai_empire_reader role (infrastructure/fixera_connector_reference.sql) --
-- same pattern, applied to AI_EMPIRE's own database instead of Fixera's.
-- Even a fully compromised or buggy Reliability & Monitoring Agent process
-- connecting with this role's credentials cannot read or write anything
-- outside exactly what's granted below.
--
-- 1) Choose your own password below before running (replace the
--    placeholder), then set in moh-sudo's .env:
--      SYSTEMS_DB_HOST=<Project Settings -> Database -> Connection pooling host, this project>
--      SYSTEMS_DB_PORT=5432
--      SYSTEMS_DB_NAME=postgres
--      SYSTEMS_DB_USER=ai_empire_systems_agent.lkcfbmcjwmxxvtpjspgr
--      SYSTEMS_DB_PASSWORD=<the password you chose>
-- 2) Run this whole block in AI_EMPIRE's own Supabase SQL Editor.

CREATE ROLE ai_empire_systems_agent WITH LOGIN PASSWORD 'GaasHooyo527#2026';

-- Default-deny: this role gets nothing beyond what's explicitly granted
-- below. Being explicit here even though Postgres already defaults to
-- deny -- matches the same belt-and-suspenders style as the Fixera
-- connector setup.
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM ai_empire_systems_agent;
REVOKE ALL ON SCHEMA public FROM ai_empire_systems_agent;
GRANT USAGE ON SCHEMA public TO ai_empire_systems_agent;

-- circuit_breakers: the Reliability & Monitoring Agent's own operational
-- state -- reads its own prior state, writes new state on every check.
GRANT SELECT, INSERT, UPDATE ON circuit_breakers TO ai_empire_systems_agent;

-- audit_vault: write-only in practice -- INSERT for new entries, SELECT so
-- STATUS-style commands can read history back. UPDATE/DELETE are blocked
-- for every role, including this one, by the existing trigger in
-- 0003_audit_vault_immutability_trigger.sql -- this GRANT doesn't include
-- UPDATE/DELETE at all, so it's blocked twice over.
GRANT SELECT, INSERT ON audit_vault TO ai_empire_systems_agent;

-- Everything else -- agent_registry, routing_logs, memory_experience,
-- memory_knowledge, memory_identity, prompt_registry, platform_settings,
-- and any table any other division owns -- stays unreachable by this role.
-- No exceptions, no "just this once" grant added later without updating
-- this file and governance/policies/systems_automation_governance.md
-- together.
