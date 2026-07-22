-- Law 9 ("No AI agent permanently deletes... only exception: Working Memory")
-- was only enforced via RLS, which the service_role key (used by our own
-- backend) always bypasses. Confirmed by test: an UPDATE from the
-- service_role client succeeded despite RLS having no UPDATE policy.
--
-- A BEFORE UPDATE/DELETE trigger enforces immutability at the row level,
-- unconditionally, regardless of which role or key issues the query.

CREATE OR REPLACE FUNCTION prevent_audit_vault_mutation()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  RAISE EXCEPTION 'audit_vault is immutable per Law 9: UPDATE and DELETE are never permitted, regardless of role.';
END;
$$;

DROP TRIGGER IF EXISTS audit_vault_no_update ON audit_vault;
CREATE TRIGGER audit_vault_no_update
  BEFORE UPDATE ON audit_vault
  FOR EACH ROW EXECUTE FUNCTION prevent_audit_vault_mutation();

DROP TRIGGER IF EXISTS audit_vault_no_delete ON audit_vault;
CREATE TRIGGER audit_vault_no_delete
  BEFORE DELETE ON audit_vault
  FOR EACH ROW EXECUTE FUNCTION prevent_audit_vault_mutation();
