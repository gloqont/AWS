# GLOQONT Advisor Dashboard

Monorepo with:
- `apps/api`: FastAPI backend
- `apps/web`: Next.js frontend

## Production Readiness Changes Included
- Optional Cognito JWT auth (`AUTH_REQUIRED=true`) with per-user data scoping.
- Optional DynamoDB persistence for users/portfolios/decisions when AWS env vars are configured.
- Runtime data directory is configurable (`DATA_DIR`) for local/legacy file persistence.
- EC2 deployment assets added under `deploy/` (systemd + nginx + scripts).

## Environment Setup

### API env
Copy `apps/api/.env.example` to `apps/api/.env` and set:
- `CORS_ORIGINS` to your domain(s)
- `DATA_DIR=/var/lib/gloqont/data` on EC2 (recommended)

### Web env
Copy `apps/web/.env.example` to `apps/web/.env` and set:
- `API_PROXY_TARGET=http://127.0.0.1:8000` on EC2

## Local Development

### Backend
```bash
cd apps/api
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd apps/web
npm install
npm run dev
```

Open `http://localhost:3000/dashboard/portfolio-optimizer`.

## EC2 Deployment (Ubuntu 24.04)

Assumes app lives at `/opt/gloqont`.

1. Copy project to the instance and install base packages:
```bash
cd /opt/gloqont
./deploy/ec2/bootstrap.sh
```

2. Create env files:
```bash
cp apps/api/.env.example apps/api/.env
cp apps/web/.env.example apps/web/.env
```

3. Deploy services:
```bash
APP_ROOT=/opt/gloqont ./deploy/ec2/deploy.sh
```

4. Verify:
```bash
systemctl status gloqont-api
systemctl status gloqont-web
systemctl status nginx
curl -I http://127.0.0.1:8000/docs
curl -I http://127.0.0.1
```

## Push to New GitHub Repo

```bash
git remote remove origin
git remote add origin https://github.com/gloqont/AWS.git
git add .
git commit -m "Prepare app for AWS EC2 deployment"
git push -u origin main
```

If your branch is not `main`, replace `main` with your current branch.
