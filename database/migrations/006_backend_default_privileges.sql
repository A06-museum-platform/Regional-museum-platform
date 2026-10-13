-- Global creator defaults can grant browser roles access even when public's
-- per-schema defaults revoke it. Remove both layers for the migration role.
-- This permission-only policy is idempotent and also enforced after restores:
-- archive ACLs do not remove unexpected grants inherited from the target.
DO $$
DECLARE browser_role text;
BEGIN
  FOREACH browser_role IN ARRAY ARRAY['anon', 'authenticated'] LOOP
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = browser_role) THEN
      EXECUTE format('REVOKE ALL ON ALL TABLES IN SCHEMA public FROM %I', browser_role);
      EXECUTE format('REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM %I', browser_role);
      EXECUTE format('ALTER DEFAULT PRIVILEGES REVOKE ALL ON TABLES FROM %I', browser_role);
      EXECUTE format('ALTER DEFAULT PRIVILEGES REVOKE ALL ON SEQUENCES FROM %I', browser_role);
      EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM %I', browser_role);
      EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM %I', browser_role);
    END IF;
  END LOOP;
END $$;
