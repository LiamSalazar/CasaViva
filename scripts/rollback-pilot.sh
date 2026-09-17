#!/usr/bin/env bash
set -Eeuo pipefail
readonly ROOT="${CASAVIVA_ROOT:-/opt/casaviva}" PROJECT=casaviva
exec 8>"$ROOT/rollback.lock"
flock -n 8 || { echo "Another rollback is running" >&2; exit 75; }
target="$(cat "$ROOT/shared/previous_release" 2>/dev/null || true)"
[[ "$target" =~ ^[0-9a-f]{40}$ ]] || { echo "No valid previous release" >&2; exit 2; }
release="$ROOT/releases/$target"
[[ -f "$release/docker-compose.yml" && -f "$release/.env.production" ]] || { echo "Previous release files are missing" >&2; exit 2; }
compose=(docker compose -p "$PROJECT" --env-file "$release/.env.production" -f "$release/docker-compose.yml")
"${compose[@]}" config --quiet
"${compose[@]}" pull
"${compose[@]}" up -d --remove-orphans --wait
set -a
# shellcheck disable=SC1090
source "$release/.env.production"
set +a
curl --fail --silent --show-error --retry 12 --retry-delay 5 "https://$PUBLIC_DOMAIN/api/health/ready/" >/dev/null
curl --fail --silent --show-error "https://$PUBLIC_DOMAIN/" >/dev/null
current="$(cat "$ROOT/shared/current_release" 2>/dev/null || true)"
printf '%s\n' "$target" > "$ROOT/shared/current_release"
[[ -n "$current" && "$current" != "$target" ]] && printf '%s\n' "$current" > "$ROOT/shared/previous_release"
ln -sfn "$release" "$ROOT/current"
ops_target="$(cat "$ROOT/shared/previous_ops_release" 2>/dev/null || true)"
if [[ "$ops_target" =~ ^[0-9a-f]{40}$ && -d "$ROOT/ops-releases/$ops_target" ]]; then
  ops_current="$(cat "$ROOT/shared/current_ops_release" 2>/dev/null || true)"
  printf '%s\n' "$ops_target" > "$ROOT/shared/current_ops_release"
  [[ -n "$ops_current" && "$ops_current" != "$ops_target" ]] && printf '%s\n' "$ops_current" > "$ROOT/shared/previous_ops_release"
  ln -sfn "$ROOT/ops-releases/$ops_target" "$ROOT/current-ops"
fi
echo "Rolled back application and ops to $target; database migrations were not reversed"
