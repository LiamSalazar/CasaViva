#!/usr/bin/env bash
set -euo pipefail
: "${1:?Usage: deploy-pilot.sh IMAGE_SHA}"
image_sha="$1"
: "${AWS_ACCOUNT_ID:?Set AWS_ACCOUNT_ID}"
registry="${AWS_ACCOUNT_ID}.dkr.ecr.mx-central-1.amazonaws.com"
release_dir="/opt/casaviva/releases/${image_sha}"
previous="$(readlink -f /opt/casaviva/current 2>/dev/null || true)"
mkdir -p "$release_dir"
cp /opt/casaviva/source/docker-compose.production.yml "$release_dir/docker-compose.yml"
cp -R /opt/casaviva/source/docker "$release_dir/docker"
aws ssm get-parameters-by-path --path /casaviva-pilot/ --with-decryption --recursive --query 'Parameters[*].[Name,Value]' --output text | awk -F '\t' '{name=$1; sub(".*/", "", name); print name "=" $2}' > "$release_dir/.env.production"
chmod 600 "$release_dir/.env.production"
printf 'FRONTEND_IMAGE=%s/casaviva-frontend:%s\nBACKEND_IMAGE=%s/casaviva-backend:%s\n' "$registry" "$image_sha" "$registry" "$image_sha" >> "$release_dir/.env.production"
aws ecr get-login-password --region mx-central-1 | docker login --username AWS --password-stdin "$registry"
docker compose --env-file "$release_dir/.env.production" -f "$release_dir/docker-compose.yml" pull
docker compose --env-file "$release_dir/.env.production" -f "$release_dir/docker-compose.yml" run --rm --user root backend python manage.py migrate
docker compose --env-file "$release_dir/.env.production" -f "$release_dir/docker-compose.yml" run --rm --user root backend python manage.py harden_database_roles
docker compose --env-file "$release_dir/.env.production" -f "$release_dir/docker-compose.yml" run --rm --user root backend python manage.py seed_system
docker compose --env-file "$release_dir/.env.production" -f "$release_dir/docker-compose.yml" run --rm backend python manage.py check_production_readiness
ln -sfn "$release_dir" /opt/casaviva/current
public_domain="$(sed -n 's/^PUBLIC_DOMAIN=//p' "$release_dir/.env.production" | tail -n 1)"
test -n "$public_domain"
if ! docker compose --env-file "$release_dir/.env.production" -f "$release_dir/docker-compose.yml" up -d --remove-orphans || ! curl --fail --retry 12 --retry-delay 5 "https://${public_domain}/api/health/ready/" || ! curl --fail "https://${public_domain}/"; then
  if [[ -n "$previous" ]]; then ln -sfn "$previous" /opt/casaviva/current; docker compose --env-file "$previous/.env.production" -f "$previous/docker-compose.yml" up -d; fi
  exit 1
fi
