#!/bin/bash
set -euo pipefail
dnf install -y docker amazon-cloudwatch-agent
systemctl enable --now docker amazon-ssm-agent amazon-cloudwatch-agent
mkdir -p /opt/casaviva/postgres /opt/casaviva/releases
chmod 700 /opt/casaviva/postgres
