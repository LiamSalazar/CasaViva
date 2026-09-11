#!/usr/bin/env bash
set -Eeuo pipefail
base_url="${1:-${PUBLIC_SITE_URL:-}}"
: "${base_url:?Usage: smoke-production.sh https://host}"
base_url="${base_url%/}"
paths=(
  "/"
  "/api/health/live/"
  "/api/health/ready/"
  "/propiedades"
  "/api/v1/public/privacy-notice/"
  "/api/v1/public/terms-of-use/"
  "/administracion/acceso"
)
for path in "${paths[@]}"; do
  code="$(curl --silent --show-error --location --output /dev/null --write-out '%{http_code}' "$base_url$path")"
  [[ "$code" == 200 ]] || { echo "FAIL $path HTTP $code" >&2; exit 1; }
  echo "PASS $path"
done
