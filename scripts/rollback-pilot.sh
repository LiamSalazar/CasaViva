#!/usr/bin/env bash
set -Eeuo pipefail
readonly ROOT=/opt/casaviva PROJECT=casaviva
exec 9>"$ROOT/rollback.lock"
flock -n 9 || { echo "Another rollback is running" >&2; exit 75; }
target="$(cat "$ROOT/shared/previous_release" 2>/dev/null || true)"
[[ "$target" =~ ^[0-9a-f]{40}$ ]] || { echo "No valid previous release" >&2; exit 2; }
release_dir="$ROOT/releases/$target"
[[ -f "$release_dir/docker-compose.yml" && -f "$release_dir/.env.production" ]] || { echo "Previous release files are missing" >&2; exit 2; }
compose=(docker compose -p "$PROJECT" --env-file "$release_dir/.env.production" -f "$release_dir/docker-compose.yml")
"${compose[@]}" config --quiet
"${compose[@]}" pull
"${compose[@]}" up -d --remove-orphans --wait
public_domain="$(sed -n 's/^PUBLIC_DOMAIN=//p' "$release_dir/.env.production" | tail -1)"
curl --fail --silent --show-error --retry 12 --retry-delay 5 "https://$public_domain/api/health/ready/" >/dev/null
current="$(cat "$ROOT/shared/current_release" 2>/dev/null || true)"
printf '%s\n' "$target" > "$ROOT/shared/current_release"
[[ -n "$current" ]] && printf '%s\n' "$current" > "$ROOT/shared/previous_release"
ln -sfn "$release_dir" "$ROOT/current"
echo "Rolled back application to $target; database migrations were not reversed"
