#!/usr/bin/env bash
set -Eeuo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
root="$tmp/root"
fake="$tmp/fake-bin"
sha_a=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
sha_b=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
mkdir -p "$root"/{bin,shared,releases,ops-releases} "$fake"

for sha in "$sha_a" "$sha_b"; do
  ops="$root/ops-releases/$sha"
  mkdir -p "$ops/scripts" "$ops/docker/postgres"
  cp "$repo/docker-compose.production.yml" "$ops/docker-compose.production.yml"
  cp "$repo/docker-compose.bootstrap.yml" "$ops/docker-compose.bootstrap.yml"
  cp "$repo/docker/Caddyfile" "$ops/docker/Caddyfile"
  cp "$repo/docker/Caddyfile.bootstrap" "$ops/docker/Caddyfile.bootstrap"
  cp "$repo/docker/postgres/init-roles.sh" "$ops/docker/postgres/init-roles.sh"
  cp "$repo/scripts/render-pilot-env.py" "$ops/scripts/render-pilot-env.py"
  cp "$repo/scripts/wait-for-dns.sh" "$ops/scripts/wait-for-dns.sh"
  printf '%s\n' "$sha" > "$ops/OPS_RELEASE"
done
cp "$repo/scripts/rollback-pilot.sh" "$root/bin/rollback.sh"
chmod +x "$root/bin/rollback.sh" "$root/ops-releases/$sha_b/scripts/"*

release_a="$root/releases/$sha_a"
mkdir -p "$release_a"
printf 'services: {}\n' > "$release_a/docker-compose.yml"
printf 'PUBLIC_DOMAIN="pilot.example.test"\nFRONTEND_IMAGE="registry/casaviva-frontend:%s"\n' "$sha_a" > "$release_a/.env.production"
printf '%s\n' "$sha_a" > "$root/shared/current_release"

printf '%s\n' '#!/usr/bin/env bash' 'set -Eeuo pipefail' \
  'case "$1 $2" in' \
  '  "sts get-caller-identity") echo 123456789012 ;;' \
  '  "ecr get-login-password") echo password ;;' \
  '  "ssm get-parameters-by-path") printf '\''{"Parameters":[{"Name":"/casaviva-pilot/POSTGRES_SUPERUSER_PASSWORD","Value":"super"},{"Name":"/casaviva-pilot/APP_DATABASE_PASSWORD","Value":"app# $=:@/ password"},{"Name":"/casaviva-pilot/MIGRATOR_DATABASE_PASSWORD","Value":"migrator"},{"Name":"/casaviva-pilot/BACKUP_DATABASE_PASSWORD","Value":"backup"},{"Name":"/casaviva-pilot/READONLY_DATABASE_PASSWORD","Value":"readonly"},{"Name":"/casaviva-pilot/BACKUP_S3_URI","Value":"s3://backup/daily"},{"Name":"/casaviva-pilot/PUBLIC_DOMAIN","Value":"pilot.example.test"},{"Name":"/casaviva-pilot/ACME_EMAIL","Value":"ops@example.test"}]}'\'' ;;' \
  '  *) exit 1 ;;' \
  'esac' > "$fake/aws"
printf '%s\n' '#!/usr/bin/env bash' 'exit 0' > "$fake/systemctl"
printf '%s\n' '#!/usr/bin/env bash' \
  'set -Eeuo pipefail' \
  'if [[ "$1" == login ]]; then cat >/dev/null; exit 0; fi' \
  'env_file=""; previous=""' \
  'for arg in "$@"; do [[ "$previous" == --env-file ]] && env_file="$arg"; previous="$arg"; done' \
  '[[ "$*" == *"connection.connection.info.user"* ]] && { echo casaviva_app; exit 0; }' \
  'if [[ "${FAIL_CANDIDATE:-}" == 1 && "$*" == *"--remove-orphans"* && -n "$env_file" ]] && grep -q bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb "$env_file"; then exit 42; fi' \
  'exit 0' > "$fake/docker"
printf '%s\n' '#!/usr/bin/env bash' '[[ "$*" == *"latest/api/token"* ]] && { echo token; exit 0; }' '[[ "$*" == *"latest/meta-data/public-ipv4"* ]] && { echo 203.0.113.10; exit 0; }' 'exit 0' > "$fake/curl"
printf '%s\n' '#!/usr/bin/env bash' 'echo "203.0.113.10 STREAM pilot.example.test"' > "$fake/getent"
chmod +x "$fake"/*

ln -sfn "$root/ops-releases/$sha_b" "$root/current-ops"
printf '%s\n' "$sha_b" > "$root/shared/current_ops_release"
printf '%s\n' "$sha_a" > "$root/shared/previous_ops_release"
if PATH="$fake:$PATH" CASAVIVA_ROOT="$root" EXPECTED_PUBLIC_IP=203.0.113.10 FAIL_CANDIDATE=1 "$repo/scripts/deploy-pilot.sh" "$sha_b"; then
  echo "Expected candidate B to fail" >&2
  exit 1
fi
[[ "$(cat "$root/shared/current_release")" == "$sha_a" ]]
echo "PASS candidate B health/start failure rolled back to healthy A"

ln -sfn "$root/ops-releases/$sha_b" "$root/current-ops"
printf '%s\n' "$sha_b" > "$root/shared/current_ops_release"
printf '%s\n' "$sha_a" > "$root/shared/previous_ops_release"
PATH="$fake:$PATH" CASAVIVA_ROOT="$root" EXPECTED_PUBLIC_IP=203.0.113.10 "$repo/scripts/deploy-pilot.sh" "$sha_b" >/dev/null
[[ "$(cat "$root/shared/current_release")" == "$sha_b" ]]
grep -q 'casaviva_app:app%23%20%24%3D%3A%40%2F%20password@' "$root/releases/$sha_b/.env.production"
rendered_password="$(set -a; source "$root/releases/$sha_b/.env.production"; set +a; printf '%s' "$CASAVIVA_APP_PASSWORD")"
[[ "$rendered_password" == 'app# $=:@/ password' ]]
PATH="$fake:$PATH" CASAVIVA_ROOT="$root" "$repo/scripts/rollback-pilot.sh" >/dev/null
[[ "$(cat "$root/shared/current_release")" == "$sha_a" ]]
[[ "$(cat "$root/shared/current_ops_release")" == "$sha_a" ]]
echo "PASS release B healthy then manual application/ops rollback restored A"
