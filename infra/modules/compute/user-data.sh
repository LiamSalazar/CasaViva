#!/bin/bash
set -Eeuo pipefail
dnf install -y docker amazon-cloudwatch-agent jq
systemctl enable --now docker amazon-ssm-agent
install -d -m 0755 /opt/casaviva/{bin,config,releases,shared,logs}
install -d -m 0700 /opt/casaviva/postgres

volume_id='${postgres_volume_id}'
serial="$${volume_id//-/}"
device=""
for _ in $$(seq 1 60); do
  device="$$(lsblk -ndo PATH,SERIAL | awk -v id="$$serial" '$2 == id {print $1; exit}')"
  [[ -n "$$device" ]] && break
  sleep 2
done
[[ -b "$$device" ]] || { echo "PostgreSQL EBS volume was not attached" >&2; exit 1; }
if ! blkid "$$device" >/dev/null 2>&1; then mkfs.xfs "$$device"; fi
uuid="$$(blkid -s UUID -o value "$$device")"
grep -q "UUID=$$uuid " /etc/fstab || printf 'UUID=%s /opt/casaviva/postgres xfs defaults,nofail 0 2\n' "$$uuid" >> /etc/fstab
mountpoint -q /opt/casaviva/postgres || mount /opt/casaviva/postgres
chown 999:999 /opt/casaviva/postgres
chmod 700 /opt/casaviva/postgres

printf '%s' '${deploy_script}' | base64 -d > /opt/casaviva/bin/deploy.sh
printf '%s' '${rollback_script}' | base64 -d > /opt/casaviva/bin/rollback.sh
printf '%s' '${backup_script}' | base64 -d > /opt/casaviva/bin/backup-postgres-s3.sh
printf '%s' '${compose_file}' | base64 -d > /opt/casaviva/config/docker-compose.production.yml
printf '%s' '${caddy_file}' | base64 -d > /opt/casaviva/config/Caddyfile
printf '%s' '${init_roles}' | base64 -d > /opt/casaviva/config/init-roles.sh
printf '%s' '${cloudwatch_config}' | base64 -d > /opt/casaviva/config/cloudwatch-agent.json
chmod 0755 /opt/casaviva/bin/*.sh
chmod 0644 /opt/casaviva/config/*

cat >/etc/systemd/system/casaviva-postgres-backup.service <<'UNIT'
[Unit]
Description=CasaViva PostgreSQL backup to S3
After=docker.service network-online.target
Wants=network-online.target
[Service]
Type=oneshot
EnvironmentFile=/opt/casaviva/shared/backup.env
ExecStart=/opt/casaviva/bin/backup-postgres-s3.sh
User=root
UNIT
cat >/etc/systemd/system/casaviva-postgres-backup.timer <<'UNIT'
[Unit]
Description=Daily CasaViva PostgreSQL backup
[Timer]
OnCalendar=*-*-* 03:15:00 UTC
Persistent=true
RandomizedDelaySec=15m
[Install]
WantedBy=timers.target
UNIT
systemctl daemon-reload
systemctl enable --now casaviva-postgres-backup.timer
systemctl enable --now amazon-cloudwatch-agent
