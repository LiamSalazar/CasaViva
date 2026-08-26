#!/usr/bin/env bash
set -euo pipefail
repository_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
env_file="$repository_dir/.env.demo"
if [[ ! -f "$env_file" ]]; then
  umask 077
  demo_password="Demo-$(openssl rand -hex 12)!"
  demo_secret="$(openssl rand -hex 32)"
  demo_db_password="$(openssl rand -hex 24)"
  demo_totp="$(openssl rand -hex 20)"
  printf 'DEMO_POSTGRES_PASSWORD=%s\nDEMO_DJANGO_SECRET=%s\nDEMO_OWNER_PASSWORD=%s\nDEMO_TOTP_SECRET=%s\n' "$demo_db_password" "$demo_secret" "$demo_password" "$demo_totp" > "$env_file"
fi
docker compose --env-file "$env_file" -f "$repository_dir/docker-compose.demo.yml" up -d --build postgres-demo backend-demo
docker compose --env-file "$env_file" -f "$repository_dir/docker-compose.demo.yml" exec -T backend-demo python manage.py migrate --noinput
docker compose --env-file "$env_file" -f "$repository_dir/docker-compose.demo.yml" exec -T backend-demo python manage.py seed_system
docker compose --env-file "$env_file" -f "$repository_dir/docker-compose.demo.yml" exec -T backend-demo python manage.py seed_reference_catalog
docker compose --env-file "$env_file" -f "$repository_dir/docker-compose.demo.yml" exec -T backend-demo python manage.py seed_demo
docker compose --env-file "$env_file" -f "$repository_dir/docker-compose.demo.yml" up -d --build frontend-demo
demo_owner_password="$(sed -n 's/^DEMO_OWNER_PASSWORD=//p' "$env_file")"
printf 'CasaViva demo: http://localhost:3001\nAdmin: http://localhost:3001/administracion/acceso\nUsuario Owner: owner@example.test\nContraseña demo local: %s\n' "$demo_owner_password"
