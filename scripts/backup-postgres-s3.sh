#!/usr/bin/env bash
set -euo pipefail
: "${BACKUP_S3_URI:?Set BACKUP_S3_URI}"
: "${BACKUP_DATABASE_URL:?Set BACKUP_DATABASE_URL for casaviva_backup}"
backup_dir="$(mktemp -d)"
trap 'rm -rf -- "$backup_dir"' EXIT
backup_file="$backup_dir/casaviva-$(date -u +%Y%m%dT%H%M%SZ).dump"
pg_dump --format=custom --no-owner --no-acl --dbname="$BACKUP_DATABASE_URL" --file="$backup_file"
aws s3 cp "$backup_file" "$BACKUP_S3_URI/" --sse AES256
