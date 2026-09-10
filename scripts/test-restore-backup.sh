#!/usr/bin/env bash
set -euo pipefail
: "${RESTORE_TEST_DATABASE_URL:?Set an isolated disposable database URL}"
: "${BACKUP_FILE:?Set a local pg_dump custom-format file}"
case "$RESTORE_TEST_DATABASE_URL" in *casaviva_restore_test*) ;; *) echo "The target database name must contain casaviva_restore_test" >&2; exit 2 ;; esac
pg_restore --clean --if-exists --no-owner --no-acl --dbname="$RESTORE_TEST_DATABASE_URL" "$BACKUP_FILE"
psql "$RESTORE_TEST_DATABASE_URL" -v ON_ERROR_STOP=1 -c "SELECT COUNT(*) FROM listings_listing; SELECT COUNT(*) FROM audit_auditevent;"
