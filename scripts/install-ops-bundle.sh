#!/usr/bin/env bash
set -Eeuo pipefail
readonly SHA="${1:?Usage: install-ops-bundle.sh GIT_SHA S3_OR_FILE_URI [ROOT]}"
readonly SOURCE="${2:?Usage: install-ops-bundle.sh GIT_SHA S3_OR_FILE_URI [ROOT]}"
readonly ROOT="${3:-/opt/casaviva}"
[[ "$SHA" =~ ^[0-9a-f]{40}$ ]] || { echo "GIT_SHA must be a full SHA" >&2; exit 2; }
exec 8>"$ROOT/ops-install.lock"
flock -n 8 || { echo "Another ops installation is running" >&2; exit 75; }
tmp="$(mktemp -d "$ROOT/.ops-install.XXXXXX")"
trap 'rm -rf "$tmp"' EXIT
bundle="$tmp/casaviva-ops-$SHA.tar.gz"
if [[ "$SOURCE" == s3://* ]]; then
  aws s3 cp "$SOURCE/casaviva-ops-$SHA.tar.gz" "$bundle" --only-show-errors
  aws s3 cp "$SOURCE/casaviva-ops-$SHA.tar.gz.sha256" "$bundle.sha256" --only-show-errors
else
  source_path="${SOURCE#file://}"
  install -m 0600 "$source_path/casaviva-ops-$SHA.tar.gz" "$bundle"
  install -m 0600 "$source_path/casaviva-ops-$SHA.tar.gz.sha256" "$bundle.sha256"
fi
(cd "$tmp" && sha256sum --check "$(basename "$bundle").sha256")
release="$ROOT/ops-releases/$SHA"
mkdir -p "$ROOT/ops-releases" "$ROOT/shared" "$ROOT/bin"
rm -rf "$tmp/extracted"
mkdir "$tmp/extracted"
tar -xzf "$bundle" -C "$tmp/extracted"
[[ "$(cat "$tmp/extracted/OPS_RELEASE")" == "$SHA" ]] || { echo "Bundle release mismatch" >&2; exit 1; }
[[ -x "$tmp/extracted/scripts/deploy-pilot.sh" && -f "$tmp/extracted/docker-compose.production.yml" ]] || { echo "Incomplete ops bundle" >&2; exit 1; }
if [[ -d "$release" ]]; then
  [[ "$(cat "$release/OPS_RELEASE")" == "$SHA" ]] || { echo "Existing ops release mismatch" >&2; exit 1; }
else
  mv "$tmp/extracted" "$release"
fi
previous="$(cat "$ROOT/shared/current_ops_release" 2>/dev/null || true)"
if [[ -n "$previous" && "$previous" != "$SHA" ]]; then printf '%s\n' "$previous" > "$ROOT/shared/previous_ops_release"; fi
printf '%s\n' "$SHA" > "$ROOT/shared/current_ops_release"
ln -sfn "$release" "$ROOT/current-ops"
for script in deploy-pilot first-install-pilot rollback-pilot backup-postgres-s3 verify-backup-systemd verify-aws-runtime-access; do
  ln -sfn "$ROOT/current-ops/scripts/$script.sh" "$ROOT/bin/${script%-pilot}.sh"
done
ln -sfn "$ROOT/current-ops/scripts/deploy-pilot.sh" "$ROOT/bin/deploy.sh"
ln -sfn "$ROOT/current-ops/scripts/rollback-pilot.sh" "$ROOT/bin/rollback.sh"
ln -sfn "$ROOT/current-ops/scripts/install-ops-bundle.sh" "$ROOT/bin/install-ops-bundle.sh"
if [[ "$ROOT" == /opt/casaviva ]]; then
  install -m 0644 "$release/docker/systemd/casaviva-postgres-backup.service" /etc/systemd/system/casaviva-postgres-backup.service
  install -m 0644 "$release/docker/systemd/casaviva-postgres-backup.timer" /etc/systemd/system/casaviva-postgres-backup.timer
  install -m 0644 "$release/docker/cloudwatch-agent.json" "$ROOT/config/cloudwatch-agent.json"
  systemctl daemon-reload
  /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
    -a fetch-config -m ec2 -c file:/opt/casaviva/config/cloudwatch-agent.json -s
fi
echo "Installed ops release $SHA"
