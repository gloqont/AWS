# Advisor Dashboard (Admin-only MVP)

This is a standalone project (not connected to any other dashboard).

## Features
- Admin-only login (single account configured via env vars)
- Portfolio Optimizer / Constructor
  - Add tickers + weights
  - Enforces weights sum to 100%
  - Risk budget enum: LOW / MEDIUM / HIGH

## Requirements
- Node.js 18+ (recommended 20+)
- Python 3.10+ (recommended 3.11)
- Cloudflare Tunnel (optional, for public access)

## Setup

### 1) Backend (FastAPI)
```bash
cd /Users/ommody/Desktop/GLOQONTv5/GLOQONTv4/apps/api
deactivate
rm -rf .venv
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# If you see repeated reloads from .venv changes, either:
# 1) keep the included .watchfilesignore, or
# 2) run: uvicorn main:app --reload --reload-dir . --reload-exclude ".venv/*" --port 8000

```
API docs: http://localhost:8000/docs

### 2) Frontend (Next.js)
```bash
cd /Users/ommody/Desktop/GLOQONTv5/GLOQONTv4/apps/web
npm install
npm run dev
```
Open: http://localhost:3000

Optional: run on a custom port (example `3001`)
```bash
cd /Users/ommody/Desktop/GLOQONTv5/GLOQONTv4/apps/web
npm run dev -- -p 3001
```

```bash
cd /Users/ommody/Desktop/GLOQONTv5
cloudflared tunnel run gloqont-mvp
```



## Login
- Go to http://localhost:3000/login
- Use ADMIN_USERNAME / ADMIN_PASSWORD from `apps/api/.env`
