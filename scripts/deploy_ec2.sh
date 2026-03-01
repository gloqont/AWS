#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   DEPLOY_BRANCH=DhyeyCode APP_DIR=/opt/gloqont bash scripts/deploy_ec2.sh

APP_DIR="${APP_DIR:-/opt/gloqont}"
DEPLOY_BRANCH="${DEPLOY_BRANCH:-main}"

cd "$APP_DIR"

echo "[1/7] Updating code"
git fetch origin "$DEPLOY_BRANCH"
git checkout "$DEPLOY_BRANCH"
git pull --ff-only origin "$DEPLOY_BRANCH"

echo "[2/7] Preparing API virtualenv"
cd "$APP_DIR/apps/api"
if [ ! -d .venv ]; then
  python3.11 -m venv --copies .venv
fi
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created apps/api/.env from example. Fill real secrets before exposing app publicly."
fi

echo "[3/7] Installing web deps"
cd "$APP_DIR/apps/web"
npm ci

if [ ! -f .env.local ]; then
  cp .env.local.example .env.local
  echo "Created apps/web/.env.local from example."
fi

echo "[4/7] Building Next.js app"
npm run build

echo "[5/7] Installing systemd units"
sudo cp "$APP_DIR/deploy/systemd/advisor-api.service" /etc/systemd/system/gloqont-api.service
sudo cp "$APP_DIR/deploy/systemd/advisor-web.service" /etc/systemd/system/gloqont-web.service
sudo systemctl daemon-reload


echo "[6/7] Enabling and restarting services"
sudo systemctl enable gloqont-api gloqont-web
sudo systemctl restart gloqont-api gloqont-web


echo "[7/7] Installing Nginx config"
sudo cp "$APP_DIR/deploy/nginx/advisor-dashboard.conf" /etc/nginx/sites-available/advisor-dashboard
sudo ln -sf /etc/nginx/sites-available/advisor-dashboard /etc/nginx/sites-enabled/advisor-dashboard
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx


echo "Deploy complete"
sudo systemctl --no-pager --full status gloqont-api gloqont-web | sed -n '1,80p'
