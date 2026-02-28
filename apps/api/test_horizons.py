import asyncio
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime

# Import Gloqont engine
from temporal_engine import TemporalSimulationEngine, MarketParams
from main import StructuredDecision, DecisionType, InstrumentAction

def run_verifier(ticker="AAPL", target_weight=1.05, horizon_unit="days", horizon_value=30):
    # Setup parameters
    n_paths = 20000
    rf = 0.043 # matched to current temporal_engine
    annual_trading_days = 252.0
    lookback = "1y"

    jump_intensity_per_day = 0.004
    jump_mean = -0.05
    jump_std = 0.05
    portfolio_value = 10000.0
    current_weight = 1.00
    post_weight = target_weight

    # Handle hours vs days
    if horizon_unit == "hours":
        T_steps = horizon_value
        dt = 1.0 / (annual_trading_days * 6.5)
        days_equiv = horizon_value / 6.5
    else:
        T_steps = horizon_value
        dt = 1.0 / annual_trading_days
        days_equiv = horizon_value

    # Fetch data
    data = yf.download(ticker, period=lookback, interval="1d", progress=False)
    if "Adj Close" in data:
        adj = data["Adj Close"].dropna()
    else:
        adj = data["Close"].dropna()
        
    try:
        S0 = float(adj.iloc[-1].item())
    except:
        S0 = float(adj.iloc[-1])

    daily_ret = adj.pct_change().dropna()
    sigma_daily = daily_ret.std(ddof=1).item() if hasattr(daily_ret.std(ddof=1), "item") else daily_ret.std(ddof=1)
    sigma_annual = sigma_daily * np.sqrt(annual_trading_days)

    # Per-asset Sharpe lookup — must match temporal_engine.asset_sharpe_ratios
    asset_sharpe_ratios = {
        "SPY": 0.45, "QQQ": 0.40, "AGG": 0.30, "TLT": 0.20,
        "AAPL": 0.50, "MSFT": 0.55, "GOOGL": 0.35, "NVDA": 0.40,
        "TSLA": 0.15, "BTC-USD": 0.35, "GLD": 0.25,
    }
    asset_sharpe = asset_sharpe_ratios.get(ticker, 0.3)
    ERP = sigma_annual * asset_sharpe
    mu_annual = rf + ERP
    
    mu_dt = mu_annual * dt
    sigma_dt = sigma_annual * np.sqrt(dt)

    # Simulate
    Z = np.random.standard_normal(size=(n_paths, T_steps))
    jump_occurrence = np.random.poisson(lam=jump_intensity_per_day * days_equiv / T_steps, size=(n_paths, T_steps))
    jump_sizes = np.random.normal(loc=jump_mean, scale=jump_std, size=(n_paths, T_steps)) * (jump_occurrence > 0)

    S = np.empty((n_paths, T_steps + 1), dtype=float)
    S[:, 0] = S0

    drift_correction = (mu_annual - 0.5 * sigma_annual**2) * dt
    for t in range(T_steps):
        diffusion = sigma_dt * Z[:, t]
        jump_factor = 1.0 + jump_sizes[:, t]
        S[:, t + 1] = S[:, t] * np.exp(drift_correction + diffusion) * jump_factor

    # Valuations
    # Baseline: 100% ticker
    V_baseline_paths = portfolio_value * (current_weight * S[:, -1] / S0)
    
    # Post: post_weight ticker, with margin drag if > 1.0
    financing_cost = 0.0
    if post_weight > 1.0:
        margin_rate = rf + 0.015
        financing_cost = (post_weight - 1.0) * (np.exp(margin_rate * days_equiv / 252.0) - 1.0) * portfolio_value
        
    V_post_paths = portfolio_value * (post_weight * S[:, -1] / S0) + portfolio_value * (1.0 - post_weight) - financing_cost

    ret_baseline = (V_baseline_paths / portfolio_value) - 1.0
    ret_post = (V_post_paths / portfolio_value) - 1.0

    mean_base = ret_baseline.mean()
    mean_post = ret_post.mean()
    
    # CVaR 95
    var95 = np.percentile(ret_post, 5)
    cvar95 = ret_post[ret_post <= var95].mean()
    
    # Drawdown median
    running_max = np.maximum.accumulate(S, axis=1)
    drawdowns = (S - running_max) / running_max
    max_dd_path = drawdowns.min(axis=1)
    # Scaling to port weight approximately
    scaled_dd = max_dd_path * post_weight
    median_maxdd = np.median(scaled_dd)

    return {
        "mean_baseline": mean_base * 100,
        "mean_post": mean_post * 100,
        "delta_mean": (mean_post - mean_base) * 100,
        "cvar_95": cvar95 * 100,
        "median_drawdown": median_maxdd * 100
    }

async def run_gloqont(ticker="AAPL", target_weight=1.05, horizon_unit="days", horizon_value=30):
    portfolio = {
        "total_value": 10000.0,
        "positions": [{"ticker": ticker, "weight": 1.0}]
    }
    decision = StructuredDecision(
        decision_type=DecisionType.TRADE,
        actions=[
            InstrumentAction(
                symbol=ticker, 
                direction="buy", 
                size_percent=(target_weight - 1.0)*100
            )
        ]
    )
    
    engine = TemporalSimulationEngine()
    
    # Convert horizon days for engine interface backwards compat, though simulate uses unit/value
    horizon_days = int(horizon_value / 6.5) if horizon_unit == "hours" else horizon_value
    
    from temporal_engine import run_decision_intelligence
    comp, score, _, _ = run_decision_intelligence(
        portfolio=portfolio,
        decision=decision,
        horizon_days=horizon_days,
        n_paths=2000, # Fast enough but sufficient
        horizon_unit=horizon_unit,
        horizon_value=horizon_value
    )
    
    return {
        "mean_baseline": comp.baseline_expected_return,
        "mean_post": comp.scenario_expected_return,
        "delta_mean": comp.delta_return,
        "cvar_95": comp.scenario_tail_loss, # Engine returns positive perm loss, script returns negative cvar
        "median_drawdown": comp.scenario_max_drawdown
    }

async def main():
    horizons = [
        ("hours", 1),
        ("hours", 5),
        ("days", 1),
        ("days", 5),
        ("days", 30),
        ("days", 90),
        ("days", 180),
        ("days", 365),
        ("days", 730)
    ]
    
    with open("python_output.txt", "w") as f:
        f.write(f"{'Horizon':<12} | {'System':<10} | {'Mean Base':<10} | {'Mean Post':<10} | {'Delta Mean':<10} | {'CVaR 95':<10} | {'Med DD':<10}\n")
        f.write("-" * 95 + "\n")
        
        for unit, val in horizons:
            # Run verifier script
            v_res = run_verifier(horizon_unit=unit, horizon_value=val)
            # Run Gloqont
            g_res = await run_gloqont(horizon_unit=unit, horizon_value=val)
            
            lbl = f"{val} {unit}"
            
            f.write(f"{lbl:<12} | {'Verifier':<10} | {v_res['mean_baseline']:>9.4f}% | {v_res['mean_post']:>9.4f}% | {v_res['delta_mean']:>9.4f}% | {v_res['cvar_95']:>9.4f}% | {v_res['median_drawdown']:>9.4f}%\n")
            f.write(f"{'':<12} | {'Gloqont':<10} | {g_res['mean_baseline']:>9.4f}% | {g_res['mean_post']:>9.4f}% | {g_res['delta_mean']:>9.4f}% | {g_res['cvar_95']:>9.4f}% | {g_res['median_drawdown']:>9.4f}%\n")
            f.write("-" * 95 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
