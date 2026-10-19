#!/usr/bin/env bash
set -euo pipefail

# Docker executes this only for a fresh named volume. Never reset an existing DB.
psql --username "$POSTGRES_USER" --dbname postgres --set ON_ERROR_STOP=1 \
  --set owner_password="$POSTGRES_OWNER_PASSWORD" \
  --set runtime_password="$POSTGRES_RUNTIME_PASSWORD" <<'SQL'
CREATE ROLE medi_chat_owner LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD :'owner_password';
CREATE ROLE medi_chat_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD :'runtime_password';
CREATE DATABASE medi_chat_dev OWNER medi_chat_owner;
CREATE DATABASE medi_chat_test OWNER medi_chat_owner;
SQL

for database in medi_chat_dev medi_chat_test; do
  psql --username "$POSTGRES_USER" --dbname "$database" --set ON_ERROR_STOP=1 <<SQL
REVOKE ALL ON DATABASE $database FROM PUBLIC;
GRANT CONNECT ON DATABASE $database TO medi_chat_owner, medi_chat_app;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO medi_chat_app;
CREATE EXTENSION pg_trgm;
ALTER DEFAULT PRIVILEGES FOR ROLE medi_chat_owner IN SCHEMA public GRANT SELECT,INSERT,UPDATE,DELETE ON TABLES TO medi_chat_app;
ALTER DEFAULT PRIVILEGES FOR ROLE medi_chat_owner IN SCHEMA public GRANT USAGE,SELECT ON SEQUENCES TO medi_chat_app;
SQL
done
