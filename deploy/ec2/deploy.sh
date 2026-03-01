#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="${APP_ROOT:-/opt/gloqont}"
API_DIR="$APP_ROOT/apps/api"
WEB_DIR="$APP_ROOT/apps/web"

if [[ ! -d "$API_DIR" || ! -d "$WEB_DIR" ]]; then
  echo "Expected app at $APP_ROOT with apps/api and apps/web"
  exit 1
fi

cd "$API_DIR"
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

cd "$WEB_DIR"
npm ci
npm run build

sudo cp "$APP_ROOT/deploy/systemd/gloqont-api.service" /etc/systemd/system/gloqont-api.service
sudo cp "$APP_ROOT/deploy/systemd/gloqont-web.service" /etc/systemd/system/gloqont-web.service
sudo cp "$APP_ROOT/deploy/nginx/gloqont.conf" /etc/nginx/sites-available/gloqont.conf
sudo ln -sf /etc/nginx/sites-available/gloqont.conf /etc/nginx/sites-enabled/gloqont.conf
sudo rm -f /etc/nginx/sites-enabled/default

sudo systemctl daemon-reload
sudo systemctl enable gloqont-api gloqont-web nginx
sudo systemctl restart gloqont-api
sudo systemctl restart gloqont-web
sudo nginx -t
sudo systemctl restart nginx

echo "Deploy complete."
echo "Check services:"
echo "  systemctl status gloqont-api"
echo "  systemctl status gloqont-web"
echo "  systemctl status nginx"
