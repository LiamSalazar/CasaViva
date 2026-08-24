#!/usr/bin/env bash
set -euo pipefail

repository_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
test_compose="$repository_dir/docker-compose.test.yml"
backend_python="$repository_dir/backend/.venv/bin/python"
backend_pytest="$repository_dir/backend/.venv/bin/pytest"
backend_image="casaviva-backend-verify:local"
frontend_image="casaviva-frontend-verify:local"
test_media_dir="${TMPDIR:-/tmp}/casaviva-postgres-test-media"

export POSTGRES_TEST_DB="${POSTGRES_TEST_DB:-casaviva_test}"
if [[ "${POSTGRES_TEST_DB,,}" != *test* ]]; then
  echo "ABORTADO: POSTGRES_TEST_DB debe contener 'test' y nunca puede apuntar a la base de desarrollo/producción." >&2
  exit 2
fi
if [[ "$POSTGRES_TEST_DB" != "casaviva_test" ]]; then
  echo "ABORTADO: este Compose aislado sólo admite casaviva_test." >&2
  exit 2
fi

export DJANGO_SETTINGS_MODULE=config.settings.postgres_test
export POSTGRES_TEST_HOST=127.0.0.1
export POSTGRES_TEST_PORT=55432
export POSTGRES_TEST_PASSWORD=casaviva-postgres-test
export E2E_ADMIN_PASSWORD='CasaViva-E2E-only-2026!'
export E2E_TOTP_SECRET='3132333435363738393031323334353637383930'
export CASAVIVA_E2E=1

cleanup() {
  docker compose -f "$test_compose" down -v --remove-orphans >/dev/null 2>&1 || true
  docker image rm "$backend_image" "$frontend_image" >/dev/null 2>&1 || true
  if [[ -d "$test_media_dir" ]]; then
    find "$test_media_dir" -depth -mindepth 1 -delete
    rmdir "$test_media_dir" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

cd "$repository_dir"
cleanup
docker compose -f "$test_compose" up -d --wait postgres-test

export POSTGRES_TEST_USER=casaviva_migrator
export POSTGRES_TEST_PASSWORD=casaviva-migrator-test
"$backend_python" backend/manage.py migrate --noinput
"$backend_python" backend/manage.py harden_database_roles
"$backend_python" backend/manage.py seed_system
"$backend_python" backend/manage.py seed_system
"$backend_python" backend/manage.py seed_reference_catalog
"$backend_python" backend/manage.py seed_reference_catalog
"$backend_python" backend/manage.py makemigrations --check --dry-run

cd "$repository_dir/backend"
DJANGO_SETTINGS_MODULE=config.settings.test "$backend_pytest" \
  --cov=apps --cov-branch --cov-fail-under=85 \
  --cov-report=term --cov-report=json:coverage.json

export POSTGRES_TEST_USER=postgres
export POSTGRES_TEST_PASSWORD=casaviva-postgres-test
DJANGO_SETTINGS_MODULE=config.settings.postgres_test "$backend_pytest" --create-db

DJANGO_SETTINGS_MODULE=config.settings.test "$backend_python" manage.py check
DJANGO_SETTINGS_MODULE=config.settings.test "$backend_python" manage.py spectacular \
  --file /tmp/casaviva-openapi.yml --validate

DJANGO_SETTINGS_MODULE=config.settings.production \
DJANGO_SECRET_KEY='verify-only-not-a-real-secret-5d377ab8dd7c90b3bd83112d5375fa57' \
DATABASE_URL='postgresql://casaviva_app:casaviva-app-test@127.0.0.1:55432/casaviva_test' \
ALLOWED_HOSTS='example.test' \
CSRF_TRUSTED_ORIGINS='https://example.test' \
"$backend_python" manage.py check --deploy

cd "$repository_dir"
POSTGRES_SUPERUSER_PASSWORD=verify-only \
CASAVIVA_APP_PASSWORD=verify-only \
CASAVIVA_MIGRATOR_PASSWORD=verify-only \
CASAVIVA_READONLY_PASSWORD=verify-only \
CASAVIVA_BACKUP_PASSWORD=verify-only \
docker compose config --quiet
docker compose -f "$test_compose" config --quiet
docker build --file docker/backend.Dockerfile --tag "$backend_image" .
docker build --file docker/frontend.Dockerfile --build-arg MEDIA_REMOTE_HOSTNAME=media.example.test --tag "$frontend_image" .

npm run lint
npm run typecheck
npm run build
npm audit --omit=dev
"$backend_python" -m pip_audit -r backend/requirements/production.txt
./scripts/secret-scan.sh

export POSTGRES_TEST_USER=casaviva_app
export POSTGRES_TEST_PASSWORD=casaviva-app-test
"$backend_python" backend/manage.py setup_e2e
npm run test:e2e
