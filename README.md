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
cd apps/api
cp .env.example .env
# edit .env and set ADMIN_PASSWORD + SESSION_SECRET
python -m venv .venv
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
