#!/usr/bin/env bash
set -euo pipefail
repository_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
env_file="$repository_dir/.env.demo"
args=(down --remove-orphans)
if [[ "${1:-}" == "--volumes" ]]; then args+=(--volumes); fi
docker compose --env-file "$env_file" -f "$repository_dir/docker-compose.demo.yml" "${args[@]}"
