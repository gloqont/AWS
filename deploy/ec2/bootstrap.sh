#!/usr/bin/env bash
set -euo pipefail

sudo apt update
sudo apt install -y python3-venv python3-pip nodejs npm nginx

sudo mkdir -p /opt/gloqont
sudo mkdir -p /var/lib/gloqont/data
sudo chown -R "$USER":"$USER" /opt/gloqont /var/lib/gloqont

echo "Bootstrap complete."
echo "Next:"
echo "1) Copy project into /opt/gloqont"
echo "2) Configure apps/api/.env and apps/web/.env"
echo "3) Run deploy/ec2/deploy.sh"
