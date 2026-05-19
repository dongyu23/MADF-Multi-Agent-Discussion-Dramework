-- MADF initial database setup
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 审计只读用户（旁路半独立架构）
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'madf_audit_ro') THEN
        CREATE ROLE madf_audit_ro WITH LOGIN PASSWORD 'madf_audit_ro';
    END IF;
END
$$;

GRANT CONNECT ON DATABASE madf TO madf_audit_ro;
GRANT USAGE ON SCHEMA public TO madf_audit_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO madf_audit_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO madf_audit_ro;
