#!/usr/bin/env bash
set -Eeuo pipefail
readonly ROOT="${CASAVIVA_ROOT:-/opt/casaviva}" PROJECT=casaviva
readonly REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-mx-central-1}}"
readonly IMAGE_SHA="${1:?Usage: deploy-pilot.sh IMAGE_SHA}"
[[ "$IMAGE_SHA" =~ ^[0-9a-f]{40}$ ]] || { echo "IMAGE_SHA must be a full immutable Git SHA" >&2; exit 2; }
exec 9>"$ROOT/deploy.lock"
flock -n 9 || { echo "Another deployment is running" >&2; exit 75; }
ops="$ROOT/current-ops"
[[ -d "$ops" ]] || { echo "Install the matching ops bundle first" >&2; exit 2; }
[[ "$(cat "$ops/OPS_RELEASE")" == "$IMAGE_SHA" ]] || { echo "Ops and image SHA differ" >&2; exit 2; }

account_id="$(aws sts get-caller-identity --query Account --output text --region "$REGION")"
registry="$account_id.dkr.ecr.$REGION.amazonaws.com"
release="$ROOT/releases/$IMAGE_SHA"
mkdir -p "$release/docker/postgres"
install -m 0644 "$ops/docker-compose.production.yml" "$release/docker-compose.yml"
install -m 0644 "$ops/docker-compose.bootstrap.yml" "$release/docker-compose.bootstrap.yml"
install -m 0644 "$ops/docker/Caddyfile" "$release/docker/Caddyfile"
install -m 0644 "$ops/docker/Caddyfile.bootstrap" "$release/docker/Caddyfile.bootstrap"
install -m 0755 "$ops/docker/postgres/init-roles.sh" "$release/docker/postgres/init-roles.sh"
umask 077
parameters="$release/parameters.json"
aws ssm get-parameters-by-path --region "$REGION" --path /casaviva-pilot/ --with-decryption --recursive --output json > "$parameters"
python3 "$ops/scripts/render-pilot-env.py" --images-sha "$IMAGE_SHA" --registry "$registry" < "$parameters" > "$release/.env.production"
rm -f "$parameters"
set -a
# shellcheck disable=SC1090 -- generated with shell-safe quoting.
source "$release/.env.production"
set +a
[[ "$MIGRATOR_DATABASE_URL" == postgresql://casaviva_migrator:* ]] || { echo "MIGRATOR_DATABASE_URL must use casaviva_migrator" >&2; exit 2; }
[[ "$APP_DATABASE_URL" == postgresql://casaviva_app:* ]] || { echo "APP_DATABASE_URL must use casaviva_app" >&2; exit 2; }
[[ "$BACKUP_DATABASE_URL" == postgresql://casaviva_backup:* ]] || { echo "BACKUP_DATABASE_URL must use casaviva_backup" >&2; exit 2; }
[[ "$BACKUP_S3_URI" == s3://* ]] || { echo "BACKUP_S3_URI must be an S3 URI" >&2; exit 2; }
[[ -n "${PUBLIC_DOMAIN:-}" && "$PUBLIC_DOMAIN" != *://* ]] || { echo "PUBLIC_DOMAIN must be a hostname without scheme" >&2; exit 2; }
[[ -n "${ACME_EMAIL:-}" ]] || { echo "ACME_EMAIL is required" >&2; exit 2; }
install -m 0600 /dev/null "$ROOT/shared/backup.env"
printf 'BACKUP_DATABASE_URL=%s\nBACKUP_S3_URI=%s\nAWS_REGION=%s\n' "$BACKUP_DATABASE_URL" "$BACKUP_S3_URI" "$REGION" > "$ROOT/shared/backup.env"
systemctl daemon-reload
systemctl enable --now casaviva-postgres-backup.timer
systemctl is-enabled --quiet casaviva-postgres-backup.timer
systemctl is-active --quiet casaviva-postgres-backup.timer
systemctl is-active --quiet amazon-cloudwatch-agent

compose=(docker compose -p "$PROJECT" --env-file "$release/.env.production" -f "$release/docker-compose.yml")
bootstrap_compose=(docker compose -p "$PROJECT" --env-file "$release/.env.production" -f "$release/docker-compose.yml" -f "$release/docker-compose.bootstrap.yml")
previous="$(cat "$ROOT/shared/current_release" 2>/dev/null || true)"
rollback_armed=false
recover() {
  status=$?
  trap - ERR
  if [[ "$rollback_armed" == true ]]; then
    echo "Candidate $IMAGE_SHA failed after migration; application rollback begins (database migrations are retained)." >&2
    if [[ -f "$ROOT/shared/previous_release" ]]; then
      "$ROOT/bin/rollback.sh" || echo "ROLLBACK_FAILED: manual intervention required" >&2
    elif [[ "$(cat "$ROOT/shared/bootstrap_release" 2>/dev/null || true)" == "$previous" ]]; then
      "${bootstrap_compose[@]}" up -d --remove-orphans --wait || echo "BOOTSTRAP_RECOVERY_FAILED" >&2
    else
      echo "NO_PREVIOUS_RELEASE: candidate stopped; manual intervention required" >&2
    fi
  fi
  exit "$status"
}
trap recover ERR

aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$registry"
"${compose[@]}" config --quiet
"${compose[@]}" pull
"${compose[@]}" up -d --wait postgres
"${compose[@]}" run --rm -e DATABASE_URL="$MIGRATOR_DATABASE_URL" backend python manage.py migrate --noinput
"${compose[@]}" run --rm -e DATABASE_URL="$MIGRATOR_DATABASE_URL" backend python manage.py harden_database_roles
rollback_armed=true
"${compose[@]}" run --rm -e DATABASE_URL="$APP_DATABASE_URL" backend python manage.py seed_system
"${compose[@]}" run --rm -e DATABASE_URL="$APP_DATABASE_URL" backend python manage.py check_production_readiness
actual_user="$("${compose[@]}" run --rm -e DATABASE_URL="$APP_DATABASE_URL" backend python manage.py shell -c 'from django.db import connection; connection.ensure_connection(); print(connection.connection.info.user)' | tail -1)"
[[ "$actual_user" == casaviva_app ]] || { echo "Runtime DB role is $actual_user, expected casaviva_app" >&2; false; }
"${compose[@]}" up -d --wait postgres backend frontend
"${compose[@]}" exec -T backend python -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8000/api/health/ready/", timeout=5).read()'
"${compose[@]}" exec -T frontend node -e "fetch('http://127.0.0.1:3000/').then(r=>{if(!r.ok)process.exit(1)}).catch(()=>process.exit(1))"
"${compose[@]}" run --rm --no-deps caddy caddy validate --config /etc/caddy/Caddyfile

expected_ip="${EXPECTED_PUBLIC_IP:-}"
if [[ -z "$expected_ip" ]]; then
  token="$(curl --fail --silent --show-error --max-time 2 -X PUT -H 'X-aws-ec2-metadata-token-ttl-seconds: 60' http://169.254.169.254/latest/api/token)"
  expected_ip="$(curl --fail --silent --show-error --max-time 2 -H "X-aws-ec2-metadata-token: $token" http://169.254.169.254/latest/meta-data/public-ipv4)"
fi
"$ops/scripts/wait-for-dns.sh" "$PUBLIC_DOMAIN" "$expected_ip" "${DNS_WAIT_TIMEOUT_SECONDS:-600}"
if [[ -n "$previous" && "$previous" != "$IMAGE_SHA" ]]; then printf '%s\n' "$previous" > "$ROOT/shared/previous_release"; fi
"${compose[@]}" up -d --remove-orphans --wait
curl --fail --silent --show-error --retry 12 --retry-delay 5 "https://$PUBLIC_DOMAIN/api/health/ready/" >/dev/null
curl --fail --silent --show-error "https://$PUBLIC_DOMAIN/" >/dev/null
printf '%s\n' "$IMAGE_SHA" > "$ROOT/shared/current_release"
touch "$ROOT/shared/first_install_complete"
ln -sfn "$release" "$ROOT/current"
rollback_armed=false
trap - ERR

keep_previous="$(cat "$ROOT/shared/previous_release" 2>/dev/null || true)"
for repository in casaviva-backend casaviva-frontend; do
  while read -r image_id tag; do
    [[ -n "$image_id" && "$tag" != "$IMAGE_SHA" && "$tag" != "$keep_previous" ]] && docker image rm "$registry/$repository:$tag" >/dev/null 2>&1 || true
  done < <(docker image ls "$registry/$repository" --format '{{.ID}} {{.Tag}}' | awk '$2 ~ /^[0-9a-f]{40}$/')
done
echo "Deployment $IMAGE_SHA completed"
