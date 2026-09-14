#!/usr/bin/env bash
set -Eeuo pipefail
readonly ROOT=/opt/casaviva PROJECT=casaviva
readonly REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-mx-central-1}}"
readonly IMAGE_SHA="${1:?Usage: deploy-pilot.sh IMAGE_SHA}"
[[ "$IMAGE_SHA" =~ ^[0-9a-f]{40}$ ]] || { echo "IMAGE_SHA must be a full immutable Git SHA" >&2; exit 2; }
exec 9>"$ROOT/deploy.lock"
flock -n 9 || { echo "Another deployment is running" >&2; exit 75; }

account_id="$(aws sts get-caller-identity --query Account --output text --region "$REGION")"
registry="$account_id.dkr.ecr.$REGION.amazonaws.com"
release_dir="$ROOT/releases/$IMAGE_SHA"
mkdir -p "$release_dir/docker"
install -m 0644 "$ROOT/config/docker-compose.production.yml" "$release_dir/docker-compose.yml"
install -m 0644 "$ROOT/config/Caddyfile" "$release_dir/docker/Caddyfile"
install -m 0644 "$ROOT/config/init-roles.sh" "$release_dir/docker/init-roles.sh"
install -m 0644 "$ROOT/config/cloudwatch-agent.json" "$release_dir/docker/cloudwatch-agent.json"

umask 077
aws ssm get-parameters-by-path --region "$REGION" --path /casaviva-pilot/ --with-decryption --recursive --output json |
  python3 -c 'import json,sys; data=json.load(sys.stdin); [print(f"{p[\"Name\"].rsplit(\"/\",1)[-1]}={p[\"Value\"]}") for p in data["Parameters"] if "\n" not in p["Value"]]' > "$release_dir/.env.production"
printf 'FRONTEND_IMAGE=%s/casaviva-frontend:%s\nBACKEND_IMAGE=%s/casaviva-backend:%s\n' "$registry" "$IMAGE_SHA" "$registry" "$IMAGE_SHA" >> "$release_dir/.env.production"

# The timer is installed during first boot, but its least-privilege environment
# only becomes available after the first deployment has fetched Parameter Store.
backup_url="$(sed -n 's/^BACKUP_DATABASE_URL=//p' "$release_dir/.env.production" | tail -1)"
backup_s3_uri="$(sed -n 's/^BACKUP_S3_URI=//p' "$release_dir/.env.production" | tail -1)"
[[ "$backup_url" == postgresql://casaviva_backup:* ]] || { echo "BACKUP_DATABASE_URL must use casaviva_backup" >&2; exit 2; }
[[ "$backup_s3_uri" == s3://* ]] || { echo "BACKUP_S3_URI must be an S3 URI" >&2; exit 2; }
install -m 0600 /dev/null "$ROOT/shared/backup.env"
printf 'BACKUP_DATABASE_URL=%s\nBACKUP_S3_URI=%s\nAWS_REGION=%s\n' "$backup_url" "$backup_s3_uri" "$REGION" > "$ROOT/shared/backup.env"
compose=(docker compose -p "$PROJECT" --env-file "$release_dir/.env.production" -f "$release_dir/docker-compose.yml")
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$registry"
"${compose[@]}" config --quiet
"${compose[@]}" pull
"${compose[@]}" up -d --wait postgres
migrator_url="$(sed -n 's/^MIGRATOR_DATABASE_URL=//p' "$release_dir/.env.production" | tail -1)"
app_url="$(sed -n 's/^APP_DATABASE_URL=//p' "$release_dir/.env.production" | tail -1)"
[[ "$migrator_url" == postgresql://casaviva_migrator:* ]] || { echo "MIGRATOR_DATABASE_URL must use casaviva_migrator" >&2; exit 2; }
[[ "$app_url" == postgresql://casaviva_app:* ]] || { echo "APP_DATABASE_URL must use casaviva_app" >&2; exit 2; }
"${compose[@]}" run --rm -e DATABASE_URL="$migrator_url" backend python manage.py migrate --noinput
"${compose[@]}" run --rm -e DATABASE_URL="$migrator_url" backend python manage.py harden_database_roles
"${compose[@]}" run --rm -e DATABASE_URL="$app_url" backend python manage.py seed_system
"${compose[@]}" run --rm -e DATABASE_URL="$app_url" backend python manage.py check_production_readiness
actual_user="$("${compose[@]}" run --rm -e DATABASE_URL="$app_url" backend python manage.py shell -c 'from django.db import connection; connection.ensure_connection(); print(connection.connection.info.user)' | tail -1)"
[[ "$actual_user" == casaviva_app ]] || { echo "Runtime DB role is $actual_user, expected casaviva_app" >&2; exit 1; }
previous="$(cat "$ROOT/shared/current_release" 2>/dev/null || true)"
if [[ -n "$previous" && "$previous" != "$IMAGE_SHA" ]]; then printf '%s\n' "$previous" > "$ROOT/shared/previous_release"; fi
if ! "${compose[@]}" up -d --remove-orphans --wait; then
  echo "New release failed while starting containers; invoking application rollback" >&2
  "$ROOT/bin/rollback.sh" || echo "Automatic rollback was unavailable or failed; manual intervention required" >&2
  exit 1
fi
public_domain="$(sed -n 's/^PUBLIC_DOMAIN=//p' "$release_dir/.env.production" | tail -1)"
if ! curl --fail --silent --show-error --retry 12 --retry-delay 5 "https://$public_domain/api/health/ready/" >/dev/null || ! curl --fail --silent --show-error "https://$public_domain/" >/dev/null; then
  echo "New release failed health checks; invoking application rollback" >&2
  "$ROOT/bin/rollback.sh"
  exit 1
fi
printf '%s\n' "$IMAGE_SHA" > "$ROOT/shared/current_release"
ln -sfn "$release_dir" "$ROOT/current"
echo "Deployment $IMAGE_SHA completed"
