# Gloqont Protocol & Intelligence Engine
*(Proprietary & Confidential)*

Gloqont is a next-generation analytical platform designed specifically to provide unassailable competitive moats in the portfolio management space. Built using a React/Next.js and Python/FastAPI architecture.

## Core Features
- **Portfolio Construction & Analysis:** Build portfolios with tickers and weights, and calculate expected returns, volatility, drawdowns, and tail risk.
- **Scenario Simulation Engine:** Natural language trade parsing (e.g., "Increase tech exposure by 12%") hooked into a quantitative simulation engine.
- **Monte Carlo Risk Projections:** Realistic path generation using geometric drift models and volatility drag to simulate future best, median, and worst-case scenarios.
- **Multi-Jurisdiction Tax Engine:** Pre-execution tax analysis covering realizing gains, execution friction, and country-specific regimes (e.g., US Short/Long-Term Capital Gains, NL Box 3 Wealth Tax).
- **Macro Shock Modeling:** Simulate the impact of specific market shocks on portfolio components.

## Setup & Execution

### 1) Backend Intelligence Engine (FastAPI)
The central nervous system computing tax vectors, market shocks, and temporal predictions.
```bash
cd apps/api
python -m venv venv_win
.\venv_win\Scripts\activate
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8002
```
*API Endpoint / Docs:* http://localhost:8002/docs

### 2) Frontend Dashboard (Next.js 14)
The visualization layer for the intelligence engine.
```bash
cd apps/web
npm install
npm run dev -- -p 3002
```
*Dashboard Access:* http://localhost:3002


## License
Copyright © 2024-Present Gloqont. All Rights Reserved.
This software is strictly confidential and proprietary. See `LICENSE` for details.
