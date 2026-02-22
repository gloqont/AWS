# Advisor Dashboard (Admin-only MVP)

This is a standalone project (not connected to any other dashboard).

## Features
- Admin-only login (single account configured via env vars)
- Portfolio Optimizer / Constructor
  - Add tickers + weights
  - Enforces weights sum to 100%
  - Risk budget enum: LOW / MEDIUM / HIGH
  - Backend returns a "risk object" contract for future quant services

## Requirements
- Node.js 18+ (recommended 20+)
- Python 3.10+ (recommended 3.11)

## Setup

### 1) Backend (FastAPI)
```bash
# edit .env and set ADMIN_PASSWORD + SESSION_SECRET
cd apps/api
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```
API docs: http://localhost:8000/docs

### 2) Frontend (Next.js)
```bash
cd apps/web
cp .env.local.example .env.local
npm install
npm run dev
```
Open: http://localhost:3000

## Login
- Go to http://localhost:3000/login
- Use ADMIN_USERNAME / ADMIN_PASSWORD from `apps/api/.env`

## Deploy To EC2 (t3.micro)

This repo now includes deployment assets:
- `scripts/bootstrap_ec2.sh` (first-time server setup)
- `scripts/deploy_ec2.sh` (pull/build/restart)
- `deploy/systemd/advisor-api.service`
- `deploy/systemd/advisor-web.service`
- `deploy/nginx/advisor-dashboard.conf`

### 1) Push your branch to GitHub
```bash
git add .
git commit -m "prepare ec2 deployment"
git push origin <branch>
```

### 2) SSH into EC2 and clone repo
```bash
ssh -i <your-key>.pem ubuntu@<ec2-public-ip>
git clone <your-repo-url> /opt/gloqont
cd /opt/gloqont
```

### 3) Bootstrap server (one time)
```bash
bash scripts/bootstrap_ec2.sh
```

### 4) Create production env files
```bash
cp apps/api/.env.example apps/api/.env
cp apps/web/.env.local.example apps/web/.env.local
```

Set real values in `apps/api/.env`:
- `ADMIN_PASSWORD` (strong value)
- `SESSION_SECRET` (long random value)
- `CORS_ORIGINS=https://gloqont.com,https://www.gloqont.com`
- `SESSION_COOKIE_SECURE=true`

### 5) Deploy app
```bash
DEPLOY_BRANCH=<branch> APP_DIR=/opt/gloqont bash scripts/deploy_ec2.sh
```

### 6) Verify services
```bash
sudo systemctl status gloqont-api gloqont-web nginx
curl -I http://127.0.0.1:8000/docs
curl -I http://127.0.0.1:3000
```

### 7) Optional: HTTPS
After DNS points to EC2, install TLS:
```bash
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx -d gloqont.com -d www.gloqont.com
```

## t3.micro Notes
- Keep only one API worker (default in `uvicorn` command).
- Use `npm ci` and build on-server only when needed.
- For low-memory instances, add swap if builds fail:
```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```
