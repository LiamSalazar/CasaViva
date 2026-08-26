#!/usr/bin/env bash
set -euo pipefail
repository_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
env_file="$repository_dir/.env.demo"
[[ -f "$env_file" ]] || { echo "Falta .env.demo; ejecuta ./scripts/demo-up.sh primero." >&2; exit 2; }
docker compose --env-file "$env_file" -f "$repository_dir/docker-compose.demo.yml" exec -T backend-demo python manage.py reset_demo_data
