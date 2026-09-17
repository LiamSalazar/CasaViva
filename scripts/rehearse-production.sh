#!/usr/bin/env bash
set -Eeuo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo"

stage() {
  local name="$1"; shift
  echo "=== $name ==="
  "$@"
  echo "PASS $name"
}

for tool in docker node npm terraform; do
  command -v "$tool" >/dev/null || { echo "FAIL missing tool: $tool" >&2; exit 1; }
done

stage "production images, migrations, hardening, app role, seed, readiness transition, legal/Turnstile/UI tests" ./scripts/verify.sh
stage "PostgreSQL 18 first boot and persistence through restart/down/recreate" ./scripts/test-postgres-persistence.sh
stage "local backup checksum and isolated restore" ./scripts/test-postgres-restore.sh
stage "ops bundles A/B, checksum and version metadata" ./scripts/test-ops-bundle.sh
stage "deployment A, candidate B failure, automatic rollback, B success and manual rollback" ./scripts/rehearse-deployment-rollback.sh

echo "PASS LOCAL PRODUCTION REHEARSAL"
echo "BLOCKED — REQUIRES AWS PILOT REHEARSAL: IMDSv2/IAM, S3, systemd, KMS/EBS, SSM and public DNS/TLS"
