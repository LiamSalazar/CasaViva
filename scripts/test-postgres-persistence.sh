#!/usr/bin/env bash
set -Eeuo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
project=casaviva-persistence-test
compose=(docker compose -p "$project" -f "$root/docker-compose.test.yml")
export POSTGRES_TEST_DB=casaviva_test POSTGRES_TEST_PASSWORD=casaviva-postgres-test
cleanup() { "${compose[@]}" down -v --remove-orphans >/dev/null 2>&1 || true; }
trap cleanup EXIT
cleanup
"${compose[@]}" up -d --wait postgres-test
"${compose[@]}" exec -T postgres-test psql -U postgres -d casaviva_test -v ON_ERROR_STOP=1 -c "CREATE TABLE persistence_probe (value text PRIMARY KEY); INSERT INTO persistence_probe VALUES ('survived');"
container="$("${compose[@]}" ps -q postgres-test)"
docker restart "$container" >/dev/null
"${compose[@]}" up -d --wait postgres-test
"${compose[@]}" exec -T postgres-test psql -U postgres -d casaviva_test -Atqc "SELECT value FROM persistence_probe" | grep -qx survived
"${compose[@]}" down --remove-orphans
"${compose[@]}" up -d --wait postgres-test
"${compose[@]}" exec -T postgres-test psql -U postgres -d casaviva_test -Atqc "SELECT value FROM persistence_probe" | grep -qx survived
docker rm -f "$("${compose[@]}" ps -q postgres-test)" >/dev/null
"${compose[@]}" up -d --wait postgres-test
"${compose[@]}" exec -T postgres-test psql -U postgres -d casaviva_test -Atqc "SELECT value FROM persistence_probe" | grep -qx survived
echo "PASS: PostgreSQL 18 first boot, restart, down/up and container recreation preserved data"
