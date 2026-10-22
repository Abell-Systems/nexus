-- ADR 0037 gate 3: roles and grants of the corpus database (specification; tested by test_roles.py).
-- Placeholders in braces are filled by the caller: {db} database, {loader} {app} {frozen} role names. Passwords are never in this file.
--
-- Model
--   admin   the bootstrap superuser of the container (POSTGRES_PASSWORD). Used only to bootstrap, to finalize a version and by an operator.
--   loader  may create a schema and load it; it cannot read or change anything once the version is finalized.
--   app     read-only on finalized versions; no DDL, no schema creation. It needs TEMPORARY only because alternative A keeps the
--           eligible-asset ids in a session-local temporary table; remove that grant if the adapter passes them as a parameter instead.
--   frozen  NOLOGIN owner of finalized schemas and tables: nobody connects as it, so nobody can alter or drop a finalized version.

-- Bootstrap (run by admin once per database)
CREATE ROLE {frozen} NOLOGIN;
CREATE ROLE {loader} LOGIN;   -- password set separately, never in SQL files or argv
CREATE ROLE {app} LOGIN;
REVOKE ALL ON DATABASE {db} FROM PUBLIC;
REVOKE CONNECT ON DATABASE postgres FROM PUBLIC;    -- the image's default databases accept any role by default
REVOKE CONNECT ON DATABASE template1 FROM PUBLIC;
GRANT CONNECT ON DATABASE {db} TO {loader}, {app};
GRANT CREATE ON DATABASE {db} TO {loader};      -- allows CREATE SCHEMA, nothing else
GRANT TEMPORARY ON DATABASE {db} TO {app};
REVOKE ALL ON SCHEMA public FROM PUBLIC;

-- Finalize one version (run by admin, never by the loader): freeze ownership, then grant read to app.
-- Parameter {schema} is the version schema, e.g. operational_v1.
ALTER SCHEMA {schema} OWNER TO {frozen};
DO $$
DECLARE t record;
BEGIN
  FOR t IN SELECT tablename FROM pg_tables WHERE schemaname = '{schema}' LOOP
    EXECUTE format('ALTER TABLE %I.%I OWNER TO {frozen}', '{schema}', t.tablename);
  END LOOP;
END $$;
REVOKE ALL ON SCHEMA {schema} FROM {loader};
REVOKE ALL ON ALL TABLES IN SCHEMA {schema} FROM {loader};
GRANT USAGE ON SCHEMA {schema} TO {app};
GRANT SELECT ON ALL TABLES IN SCHEMA {schema} TO {app};
