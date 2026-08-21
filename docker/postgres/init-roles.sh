#!/bin/sh
set -eu

psql --set=ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  --set=app_password="$CASAVIVA_APP_PASSWORD" \
  --set=db_name="$POSTGRES_DB" \
  --set=migrator_password="$CASAVIVA_MIGRATOR_PASSWORD" \
  --set=readonly_password="$CASAVIVA_READONLY_PASSWORD" \
  --set=backup_password="$CASAVIVA_BACKUP_PASSWORD" <<'SQL'
SELECT format('CREATE ROLE casaviva_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD %L', :'app_password') WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'casaviva_app') \gexec
SELECT format('CREATE ROLE casaviva_migrator LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD %L', :'migrator_password') WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'casaviva_migrator') \gexec
SELECT format('CREATE ROLE casaviva_readonly LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD %L', :'readonly_password') WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'casaviva_readonly') \gexec
SELECT format('CREATE ROLE casaviva_backup LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD %L', :'backup_password') WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'casaviva_backup') \gexec

ALTER ROLE casaviva_app WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD :'app_password';
ALTER ROLE casaviva_migrator WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD :'migrator_password';
ALTER ROLE casaviva_readonly WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD :'readonly_password';
ALTER ROLE casaviva_backup WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD :'backup_password';

ALTER DATABASE :"db_name" OWNER TO casaviva_migrator;
GRANT CONNECT ON DATABASE :"db_name" TO casaviva_app, casaviva_readonly, casaviva_backup;
GRANT USAGE ON SCHEMA public TO casaviva_app, casaviva_readonly, casaviva_backup;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO casaviva_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO casaviva_app;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO casaviva_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO casaviva_backup;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO casaviva_backup;
ALTER DEFAULT PRIVILEGES FOR ROLE casaviva_migrator IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO casaviva_app;
ALTER DEFAULT PRIVILEGES FOR ROLE casaviva_migrator IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO casaviva_app;
ALTER DEFAULT PRIVILEGES FOR ROLE casaviva_migrator IN SCHEMA public GRANT SELECT ON TABLES TO casaviva_readonly;
ALTER DEFAULT PRIVILEGES FOR ROLE casaviva_migrator IN SCHEMA public GRANT SELECT ON TABLES TO casaviva_backup;
ALTER DEFAULT PRIVILEGES FOR ROLE casaviva_migrator IN SCHEMA public GRANT SELECT ON SEQUENCES TO casaviva_backup;
SQL
