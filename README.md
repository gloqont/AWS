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

```
API docs: http://localhost:8000/docs

### 2) Frontend (Next.js)
```bash
cd apps/web
cp .env.local.example .env.local
npm install
npm run dev


cd /Users/ommody/Desktop/GLOQONTv5/GLOQONTv4/apps/web
npm run dev -- -p 3001
```
Open: http://localhost:3000

## Login
- Go to http://localhost:3000/login
- Use ADMIN_USERNAME / ADMIN_PASSWORD from `apps/api/.env`
