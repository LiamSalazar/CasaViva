#!/usr/bin/env bash
set -Eeuo pipefail
readonly ENV_FILE=/opt/casaviva/shared/backup.env
[[ -f "$ENV_FILE" ]] || { echo "FAIL backup.env missing"; exit 1; }
[[ "$(stat -c '%a' "$ENV_FILE")" == 600 ]] || { echo "FAIL backup.env must be 0600"; exit 1; }
set -a; source "$ENV_FILE"; set +a
[[ "$BACKUP_DATABASE_URL" == postgresql://casaviva_backup:* ]] || { echo "FAIL backup role"; exit 1; }
[[ "$BACKUP_S3_URI" == s3://* ]] || { echo "FAIL backup S3 URI"; exit 1; }
systemctl is-enabled --quiet casaviva-postgres-backup.timer
systemctl is-active --quiet casaviva-postgres-backup.timer
systemctl show casaviva-postgres-backup.service -p Result -p ExecMainStatus --no-pager
systemctl list-timers casaviva-postgres-backup.timer --no-pager
echo "PASS backup systemd preflight"
