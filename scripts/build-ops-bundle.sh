#!/usr/bin/env bash
set -Eeuo pipefail
readonly SHA="${1:?Usage: build-ops-bundle.sh GIT_SHA [OUTPUT_DIR]}"
readonly OUTPUT_DIR="${2:-dist}"
[[ "$SHA" =~ ^[0-9a-f]{40}$ ]] || { echo "GIT_SHA must be a full SHA" >&2; exit 2; }
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
stage="$(mktemp -d)"
trap 'rm -rf "$stage"' EXIT
mkdir -p "$stage/scripts" "$stage/docker/postgres"
files=(
  scripts/deploy-pilot.sh scripts/first-install-pilot.sh scripts/rollback-pilot.sh
  scripts/backup-postgres-s3.sh scripts/install-ops-bundle.sh scripts/render-pilot-env.py scripts/wait-for-dns.sh
  scripts/verify-backup-systemd.sh scripts/verify-aws-runtime-access.sh
  docker-compose.production.yml docker-compose.bootstrap.yml docker/Caddyfile
  docker/Caddyfile.bootstrap docker/cloudwatch-agent.json docker/postgres/init-roles.sh
  docker/systemd/casaviva-postgres-backup.service docker/systemd/casaviva-postgres-backup.timer
)
for file in "${files[@]}"; do
  [[ -f "$repo/$file" ]] || { echo "Missing ops file: $file" >&2; exit 1; }
  install -D -m 0644 "$repo/$file" "$stage/$file"
done
chmod 0755 "$stage"/scripts/*.sh "$stage/scripts/render-pilot-env.py" "$stage/docker/postgres/init-roles.sh"
printf '%s\n' "$SHA" > "$stage/OPS_RELEASE"
mkdir -p "$OUTPUT_DIR"
bundle="$OUTPUT_DIR/casaviva-ops-$SHA.tar.gz"
tar --sort=name --mtime='UTC 1970-01-01' --owner=0 --group=0 --numeric-owner -C "$stage" -czf "$bundle" .
(cd "$OUTPUT_DIR" && sha256sum "$(basename "$bundle")" > "$(basename "$bundle").sha256")
echo "$bundle"
