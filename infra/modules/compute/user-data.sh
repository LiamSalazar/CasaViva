#!/bin/bash
set -Eeuo pipefail

# Keep user-data limited to host bootstrap. The versioned ops bundle is
# installed later through SSM; no application code or secrets belong here.
dnf install -y docker amazon-cloudwatch-agent
systemctl enable --now docker amazon-ssm-agent

install -d -m 0755 /opt/casaviva/{bin,config,releases,ops-releases,shared,logs}
install -d -m 0700 /opt/casaviva/postgres

volume_id='${postgres_volume_id}'
serial="vol$(printf '%s' "$volume_id" | tr -d '-')"
device=""
for _ in $(seq 1 60); do
  device="$(lsblk -ndo PATH,SERIAL | awk -v id="$serial" '$2 == id {print $1; exit}')"
  [[ -n "$device" ]] && break
  sleep 2
done
[[ -b "$device" ]] || { echo "PostgreSQL EBS volume was not attached" >&2; exit 1; }
if ! blkid "$device" >/dev/null 2>&1; then mkfs.xfs "$device"; fi
uuid="$(blkid -s UUID -o value "$device")"
grep -q "UUID=$uuid " /etc/fstab || printf 'UUID=%s /opt/casaviva/postgres xfs defaults,nofail 0 2\n' "$uuid" >> /etc/fstab
mountpoint -q /opt/casaviva/postgres || mount /opt/casaviva/postgres
chown 999:999 /opt/casaviva/postgres
chmod 700 /opt/casaviva/postgres
