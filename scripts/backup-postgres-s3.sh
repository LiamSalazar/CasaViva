#!/usr/bin/env bash
set -Eeuo pipefail
: "${BACKUP_S3_URI:?Set BACKUP_S3_URI}"
: "${BACKUP_DATABASE_URL:?Set BACKUP_DATABASE_URL for casaviva_backup}"
metric() {
  local value="$1"; local args=()
  [[ -n "${AWS_REGION:-}" ]] && args+=(--region "$AWS_REGION")
  aws cloudwatch put-metric-data --namespace CasaViva/Pilot --metric-name BackupSuccess --value "$value" --unit Count "${args[@]}" || true
}
trap 'metric 0' ERR
backup_dir="$(mktemp -d)"
trap 'rm -rf -- "$backup_dir"' EXIT
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_file="$backup_dir/casaviva-$timestamp.dump"
docker run --rm --user 0 --network casaviva_default -e PGDATABASE="$BACKUP_DATABASE_URL" -v "$backup_dir:/backup" postgres:18 \
  pg_dump --format=custom --no-owner --no-acl --file="/backup/$(basename "$backup_file")"
docker run --rm -i postgres:18 pg_restore --list < "$backup_file" >/dev/null
sha256sum "$backup_file" > "$backup_file.sha256"
aws s3 cp "$backup_file" "$BACKUP_S3_URI/daily/" --sse AES256
aws s3 cp "$backup_file.sha256" "$BACKUP_S3_URI/daily/" --sse AES256
day_of_week="$(date -u +%u)"; day_of_month="$(date -u +%d)"
if [[ "$day_of_week" == 7 ]]; then aws s3 cp "$backup_file" "$BACKUP_S3_URI/weekly/" --sse AES256; aws s3 cp "$backup_file.sha256" "$BACKUP_S3_URI/weekly/" --sse AES256; fi
if [[ "$day_of_month" == 01 ]]; then aws s3 cp "$backup_file" "$BACKUP_S3_URI/monthly/" --sse AES256; aws s3 cp "$backup_file.sha256" "$BACKUP_S3_URI/monthly/" --sse AES256; fi
metric 1
