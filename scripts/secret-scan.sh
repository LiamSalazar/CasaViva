#!/usr/bin/env bash
set -euo pipefail

repository_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repository_dir"

pattern='-----BEGIN (RSA|OPENSSH|EC) PRIVATE KEY-----|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]+'
if git grep -nE -- "$pattern" -- ':!scripts/secret-scan.sh'; then
  echo "Posible secreto real detectado en un archivo versionado." >&2
  exit 1
fi
echo "Secret scan: sin patrones de credenciales reales."
