#!/usr/bin/env bash
set -euo pipefail

# First-time EC2 provisioning for Ubuntu 22.04/24.04.
# Run as ubuntu user: bash scripts/bootstrap_ec2.sh

sudo apt-get update
sudo apt-get install -y \
  git \
  curl \
  nginx \
  python3.11 \
  python3.11-venv \
  python3-pip \
  build-essential

if ! command -v node >/dev/null 2>&1; then
  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
  sudo apt-get install -y nodejs
fi

sudo systemctl enable nginx
sudo systemctl start nginx

echo "Bootstrap complete. Node: $(node -v), npm: $(npm -v), python3.11: $(python3.11 --version)"
