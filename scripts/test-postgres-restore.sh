#!/usr/bin/env bash
set -Eeuo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
project=casaviva-restore-test
compose=(docker compose -p "$project" -f "$root/docker-compose.test.yml")
tmp="$(mktemp -d)"
cleanup() { "${compose[@]}" down -v --remove-orphans >/dev/null 2>&1 || true; find "$tmp" -type f -delete; rmdir "$tmp" 2>/dev/null || true; }
trap cleanup EXIT
"${compose[@]}" down -v --remove-orphans >/dev/null 2>&1 || true
"${compose[@]}" up -d --wait postgres-test
"${compose[@]}" exec -T postgres-test psql -U postgres -d casaviva_test -v ON_ERROR_STOP=1 -c "CREATE TABLE restore_probe(value text PRIMARY KEY); INSERT INTO restore_probe VALUES ('verified');"
"${compose[@]}" exec -T postgres-test pg_dump -U postgres -Fc casaviva_test > "$tmp/test.dump"
"${compose[@]}" exec -T postgres-test pg_restore --list < "$tmp/test.dump" >/dev/null
sha256sum "$tmp/test.dump" > "$tmp/test.dump.sha256"
sha256sum -c "$tmp/test.dump.sha256"
"${compose[@]}" exec -T postgres-test dropdb -U postgres casaviva_test
"${compose[@]}" exec -T postgres-test createdb -U postgres casaviva_test
"${compose[@]}" exec -T postgres-test pg_restore -U postgres -d casaviva_test --no-owner --no-acl < "$tmp/test.dump"
"${compose[@]}" exec -T postgres-test psql -U postgres -d casaviva_test -Atqc "SELECT value FROM restore_probe" | grep -qx verified
echo "PASS: isolated PostgreSQL backup checksum and restore verified"
