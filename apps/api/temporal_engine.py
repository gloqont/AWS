"""
GLOQONT Temporal Simulation Engine — Future World Generation

This module implements the Temporal Market Simulation Engine (Section 7 of the architecture).
It generates future world states S₀ → S₁ → S₂ → ... → Sₙ and projects portfolio evolution.

Core Capabilities:
- Monte Carlo price path generation
- Regime switching simulation
- Portfolio evolution with decision execution
- Counterfactual comparison (with vs. without decision)

Philosophy: LLMs interpret. Deterministic engines decide.
All simulations are reproducible given the same seed.
"""

import math
import secrets
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

from decision_schema import (
    StructuredDecision, SimulationState, SimulationPath, 
    DecisionComparison, DecisionScore, DecisionVerdict,
    Direction, DecisionType, TimingType,
    ExecutionContext, RiskAnalysis, AssetDelta,
    MarketShock, ScenarioType
)
from asset_resolver import ASSET_RESOLVER


@dataclass
class MarketParams:
    """Market parameters for simulation."""
    risk_free_rate: float = 0.043  # 4.3% annual
    base_volatility: float = 0.20  # 20% annual
    mean_reversion_speed: float = 0.1
    jump_intensity: float = 0.004  # ~0.4% chance of jump per day (~1/year)
    jump_magnitude: float = 0.05  # 5% average jump size
    correlation_decay: float = 0.95
    default_sharpe_ratio: float = 0.3  # Fallback Sharpe


class TemporalSimulationEngine:
    """
    The core temporal simulation engine.
    
    Generates future world states and evaluates decisions through time.
    """
    
    def __init__(self, seed: Optional[int] = None):
        """
        Initialize the simulation engine.
        
        Args:
            seed: Random seed for reproducibility
        """
        self.seed = seed if seed is not None else secrets.randbits(32)
        self.rng = np.random.default_rng(self.seed)
        self.market_params = MarketParams()
        
        # Default volatilities for common assets
        self.asset_volatilities = {
            "SPY": 0.18, "QQQ": 0.25, "IWM": 0.22, "AGG": 0.05, "TLT": 0.15,
            "AAPL": 0.28, "MSFT": 0.26, "GOOGL": 0.30, "AMZN": 0.32, "META": 0.35,
            "NVDA": 0.45, "TSLA": 0.50, "AMD": 0.45, "INTC": 0.30,
            "JPM": 0.25, "GS": 0.30, "V": 0.22, "MA": 0.22,
            "JNJ": 0.15, "PFE": 0.25, "UNH": 0.22,
            "XOM": 0.25, "CVX": 0.25,
            "GLD": 0.15, "BTC-USD": 0.60, "ETH-USD": 0.70,
        }
        
        # Default correlations (simplified)
        self.base_correlation = 0.6  # Average equity correlation
        
        # Per-asset Sharpe from long-run empirical approximations
        self.asset_sharpe_ratios = {
            "SPY": 0.45, "QQQ": 0.40, "AGG": 0.30, "TLT": 0.20,
            "AAPL": 0.50, "MSFT": 0.55, "GOOGL": 0.35, "NVDA": 0.40,
            "TSLA": 0.15, "BTC-USD": 0.35, "GLD": 0.25,
        }
    
    def _apply_market_shocks(self, initial_prices: Dict[str, float], shocks: List[MarketShock]) -> Dict[str, float]:
        """
        Apply immediate market shocks to initial prices (T=0).
        Returns a new dictionary of shocked prices.
        """
        shocked_prices = initial_prices.copy()
        
        if not shocks:
            return shocked_prices
            
        # Helper to get sector for a ticker
        def get_sector(ticker):
            # Try efficient lookups first
            if ticker in ["AAPL", "MSFT", "GOOGL", "NVDA", "AMD", "META", "CRM", "ADBE"]: return "Technology"
            if ticker in ["JPM", "BAC", "GS", "MS", "V", "MA"]: return "Financial Services"
            if ticker in ["XOM", "CVX", "COP", "SLB"]: return "Energy"
            if ticker in ["JNJ", "PFE", "UNH", "ABBV"]: return "Healthcare"
            if ticker in ["AMZN", "TSLA", "HD", "MCD"]: return "Consumer Cyclical"
            if ticker in ["WMT", "COST", "KO", "PEP"]: return "Consumer Defensive"
            if ticker in ["TLT", "AGG", "BND"]: return "Fixed Income"
            if ticker in ["GLD", "SLV"]: return "Commodities"
            if "BTC" in ticker or "ETH" in ticker: return "Crypto"
            
            # Fallback to asset resolver
            info = ASSET_RESOLVER.resolve_asset(ticker)
            return info.sector if info else "Unknown"

        for shock in shocks:
            effect_map = {} # Ticker -> Multiplier (e.g. 1.05 for +5%)
            
            # CASE 1: RATES CHANGE (e.g. +1.0%)
            # Logic: Rates UP -> Tech DOWN, Bonds DOWN, Financials UP
            if shock.shock_type == ScenarioType.RATES_CHANGE:
                rate_delta = shock.magnitude # e.g. 1.0
                
                for ticker in shocked_prices.keys():
                    sector = get_sector(ticker)
                    impact = 0.0
                    
                    if sector == "Technology" or sector == "Crypto":
                        impact = -2.0 * rate_delta # High sensitivity
                    elif sector == "Fixed Income":
                        impact = -8.0 * rate_delta # Duration risk (approx 8 years)
                    elif sector == "Financial Services":
                        impact = 0.5 * rate_delta # Net interest margin benefit
                    elif sector == "Real Estate" or sector == "Utilities":
                        impact = -1.5 * rate_delta
                    else:
                        impact = -0.5 * rate_delta # General market drag
                        
                    effect_map[ticker] = 1.0 + (impact / 100.0)

            # CASE 2: OIL/COMMODITY SHOCK
            elif shock.shock_type == ScenarioType.COMMODITY_SHOCK:
                # e.g. Oil +20%
                for ticker in shocked_prices.keys():
                    sector = get_sector(ticker)
                    impact = 0.0
                    
                    if sector == "Energy":
                        impact = 0.8 * shock.magnitude # High correlation
                    elif sector == "Industrials" or "Airlines" in sector:
                        impact = -0.2 * shock.magnitude # Higher costs
                    else:
                        impact = -0.05 * shock.magnitude # General inflation drag
                        
                    effect_map[ticker] = 1.0 + (impact / 100.0)

            # CASE 3: SECTOR SHOCK
            elif shock.shock_type == ScenarioType.SECTOR_SHOCK:
                # Target="TECH", Magnitude=-20
                target_sector = shock.target.lower()
                
                for ticker in shocked_prices.keys():
                    sector = get_sector(ticker).lower()
                    if target_sector in sector or (target_sector == "tech" and "technology" in sector):
                         effect_map[ticker] = 1.0 + (shock.magnitude / 100.0)
            
            # CASE 4: GDP/RECESSION
            elif shock.shock_type == ScenarioType.GDP_GROWTH:
                # GDP -2%
                for ticker in shocked_prices.keys():
                    sector = get_sector(ticker)
                    beta = 1.0
                    if sector in ["Consumer Cyclical", "Industrials", "Financial Services", "Energy"]:
                        beta = 1.3
                    elif sector in ["Consumer Defensive", "Healthcare", "Utilities"]:
                        beta = 0.6
                        
                    # Rule of thumb: Stock market moves ~3x GDP
                    market_move = shock.magnitude * 3.0 
                    impact = market_move * beta
                    effect_map[ticker] = 1.0 + (impact / 100.0)
            
            # Apply effects from this shock
            for ticker, multiplier in effect_map.items():
                if ticker in shocked_prices:
                    # Compound effects if multiple shocks
                    shocked_prices[ticker] *= multiplier
                    
        return shocked_prices

    def simulate(
        self,
        portfolio: Dict[str, Any],
        decision: StructuredDecision,
        horizon_days: int = 30,
        n_paths: int = 100,
        time_steps_per_day: int = 1,
        horizon_unit: str = "days",
        horizon_value: int = 30
    ) -> Tuple[List[SimulationPath], List[SimulationPath]]:
        """
        Run the full simulation comparing baseline vs. scenario.
        
        Args:
            portfolio: Current portfolio state
            decision: The structured decision to evaluate
            horizon_days: How far into the future to simulate
            n_paths: Number of Monte Carlo paths
            time_steps_per_day: Granularity of simulation
            
        Returns:
            Tuple of (baseline_paths, scenario_paths)
        """
        total_steps = horizon_days * time_steps_per_day
        dt = 1.0 / time_steps_per_day  # Time step in days
        
        # Extract portfolio info
        positions = portfolio.get("positions", [])
        total_value = portfolio.get("total_value", 100000.0)
        tickers = [p.get("ticker") for p in positions]
        weights = {p.get("ticker"): p.get("weight", 0) for p in positions}
        
        # Get initial prices (normalized to 100 for simplicity)
        initial_prices = {ticker: 100.0 for ticker in tickers}
        
        # Add decision asset if not in portfolio
        for action in decision.actions:
                if action.symbol not in initial_prices:
                    initial_prices[action.symbol] = 100.0
                    tickers.append(action.symbol)

        # 3. Create all tickers set for _generate_price_paths
        all_tickers = list(set(tickers))
        # Setup simulation parameters (Intraday support)
        if horizon_unit == "hours":
            # Scale to actual requested hours, dt becomes a fraction of a 6.5h trading day
            dt = 1.0 / (252.0 * 6.5)
            total_steps = horizon_value
        else:
            # For days, weeks, months: use standard 1-day increments
            dt = 1.0 / 252.0
            total_steps = max(1, horizon_days)
        
        # Ensure all tickers in initial_prices (defaults to 100 if not set)
        for t in all_tickers:
            if t not in initial_prices:
                initial_prices[t] = 100.0

        # Generate price paths for all relevant assets
        try:
            from risk import fetch_prices
            price_data = fetch_prices(all_tickers, lookback_days=252, cache_ttl_seconds=3600)
            empirical_corr = price_data.returns.corr().values
        except Exception:
            empirical_corr = None

        price_paths = self._generate_price_paths(all_tickers, initial_prices, total_steps, dt, n_paths, empirical_corr)
        
        # Calculate Scenario Initial Impact (if any shocks)
        scenario_impact_ratio = 1.0
        if decision.market_shocks:
             shocked_prices = self._apply_market_shocks(initial_prices, decision.market_shocks)
             
             # Calculate portfolio level impact
             # sum (weight * new_price / old_price)
             weighted_impact = 0.0
             total_w = 0.0
             for t in tickers:
                 w = weights.get(t, 0.0)
                 if w > 0:
                     p_old = initial_prices.get(t, 100.0)
                     p_new = shocked_prices.get(t, 100.0)
                     ratio = p_new / p_old
                     weighted_impact += w * ratio
                     total_w += w
             
             # If fully invested
             if total_w > 0:
                 scenario_impact_ratio = weighted_impact / total_w
        
        # USE VECTORIZED SIMULATION (OPTIMIZATION)
        return self._simulate_vectorized(price_paths, portfolio, decision, horizon_days, scenario_impact_ratio)
    
    def _generate_price_paths(
        self,
        tickers: List[str],
        initial_prices: Dict[str, float],
        total_steps: int,
        dt: float,
        n_paths: int = 1,
        empirical_corr: Optional[np.ndarray] = None
    ) -> Dict[str, np.ndarray]:
        """
        Generate correlated price paths using geometric Brownian motion with jumps.
        Returns dict of arrays with shape (n_paths, total_steps + 1).
        """
        n_assets = len(tickers)
        
        # Build correlation matrix
        if empirical_corr is not None and empirical_corr.shape == (n_assets, n_assets):
            corr_matrix = empirical_corr
        else:
            corr_matrix = np.eye(n_assets) * (1 - self.base_correlation) + self.base_correlation
        
        # Cholesky decomposition for correlated random draws
        try:
            chol = np.linalg.cholesky(corr_matrix)
        except np.linalg.LinAlgError:
            # Fallback for non-positive definite matrix (rare)
            chol = np.eye(n_assets)
        
        # Generate uncorrelated random draws (N, T, Assets)
        Z = self.rng.standard_normal((n_paths, total_steps, n_assets))
        
        # Apply correlation: (N, T, A) @ (A, A) -> (N, T, A)
        correlated_Z = Z @ chol.T
        
        # Generate price paths
        price_paths = {}
        for i, ticker in enumerate(tickers):
            vol = self.asset_volatilities.get(ticker, self.market_params.base_volatility)
            
            # REALISM FIX: Use Real-World Drift instead of Risk-Neutral Drift for Monte Carlo
            # Risk Free Rate + (Sharpe Ratio * Volatility)
            # Per-asset Sharpe from long-run empirical approximations
            asset_sharpe = self.asset_sharpe_ratios.get(ticker, self.market_params.default_sharpe_ratio)
            equity_risk_premium = vol * asset_sharpe
            
            # Real-world drift = r + ERP
            real_world_drift = self.market_params.risk_free_rate + equity_risk_premium
            
            # Fix: drift should be annualized because we multiply by dt (in years) later.
            # PREVIOUS BUG: drift = real_world_drift / 252 (daily) AND dt = 1/365 (daily). Result was drift/90000.
            drift = real_world_drift 
            
            vol_daily = vol / np.sqrt(252)  # Daily volatility
            
            # Precompute jumps matrix (N, T)
            jump_prob = self.market_params.jump_intensity * dt
            jumps = np.zeros((n_paths, total_steps))
            
            # Vectorized Jump Mask
            jump_mask = self.rng.random((n_paths, total_steps)) < jump_prob
            if np.any(jump_mask):
                # Asymmetric jump: 70% negative (crashes), 30% positive (gap-ups)
                jump_signs = np.where(self.rng.random(np.sum(jump_mask)) < 0.7, -1.0, 1.0)
                jump_abs = np.abs(self.rng.standard_t(df=4, size=np.sum(jump_mask))) * self.market_params.jump_magnitude
                jumps[jump_mask] = jump_signs * jump_abs
            
            # GBM Evolution
            # ret = (drift - 0.5 * vol^2) * dt + vol * dW + jump
            # Note: vol in standard formula is annualized. 
            # If we use annualized `vol` and `drift`, we should use `dt` (years).
            # dW = Z * sqrt(dt)
            
            # Let's standardize on Annualized Params:
            # drift (annual) = 0.09
            # vol (annual) = 0.20
            # dt (annual) = 1/252
            
            dW = correlated_Z[:, :, i] * np.sqrt(dt)
            ret = (drift - 0.5 * vol**2) * dt + vol * dW + jumps
            
            # Cumulative return -> Price
            # prices = initial * exp(cumsum(ret))
            cum_ret = np.cumsum(ret, axis=1)
            
            initial_p = initial_prices.get(ticker, 100.0)
            prices = np.zeros((n_paths, total_steps + 1))
            prices[:, 0] = initial_p
            prices[:, 1:] = initial_p * np.exp(cum_ret)
            
            price_paths[ticker] = prices
        
        return price_paths

    def _simulate_vectorized(self, price_paths: Dict[str, np.ndarray], portfolio: Dict[str, Any], decision: StructuredDecision, horizon_days: int, scenario_impact_ratio: float = 1.0) -> Tuple[List[SimulationPath], List[SimulationPath]]:
        """
        Vectorized simulation for all paths simultaneously.
        Returns (baseline_paths, scenario_paths).
        """
        # 1. Setup
        tickers = list(price_paths.keys())
        first_path = next(iter(price_paths.values()))
        n_paths, total_steps_plus_1 = first_path.shape
        total_steps = total_steps_plus_1 - 1
        
        # Prices tensor: (N_paths, T_steps+1, N_assets)
        sorted_tickers = sorted(tickers)
        prices_list = [price_paths[t] for t in sorted_tickers]
        prices_matrix = np.stack(prices_list, axis=2) 
        
        # 2. Weights extraction
        initial_value = float(portfolio["total_value"])
        portfolio_positions = {p["ticker"]: p["weight"] for p in portfolio["positions"]}
        
        # Current Weights Vector
        current_weights = np.zeros(len(sorted_tickers))
        for i, t in enumerate(sorted_tickers):
            current_weights[i] = portfolio_positions.get(t, 0.0)
            
        # Post-Decision Weights Vector
        # Execute decision logic once (deterministically)
        post_weights_dict = self._execute_decision(decision, portfolio_positions.copy(), initial_value)
        
        # Extract leverage metadata before building weight vector
        leverage_meta = post_weights_dict.pop("__leverage_meta__", None)
        margin_cost_daily = 0.0
        if leverage_meta:
            margin_cost_daily = leverage_meta["margin_cost_daily"]
            print(f"LEVERAGE: gross_exposure={leverage_meta['gross_exposure']:.4f}, "
                  f"borrowed={leverage_meta['leverage_amount']:.4f}, "
                  f"margin_cost_daily={margin_cost_daily:.8f}")
        
        post_weights = np.zeros(len(sorted_tickers))
        for i, t in enumerate(sorted_tickers):
            post_weights[i] = post_weights_dict.get(t, 0.0)
            
        # Execution Step
        exec_delay = int(decision.get_max_execution_delay())
        exec_step = min(exec_delay, total_steps)
        
        # 3. Asset Returns Matrix (N_paths, T_steps, N_assets)
        prices_matrix[prices_matrix == 0] = 1e-8
        asset_returns = prices_matrix[:, 1:, :] / prices_matrix[:, :-1, :] - 1.0
        
        # 4. Calculate Portfolio Returns
        
        # A. Baseline (Constant Mix of Current Weights)
        # Note: True Buy & Hold drifts weights. Constant Mix rebalances.
        # For simplicity and speed in vectors, we assume Constant Mix here (daily rebalance).
        returns_base_all = asset_returns @ current_weights # (N_paths, T_steps)
        
        # B. Scenario
        if exec_step > 0:
            returns_pre = asset_returns[:, :exec_step, :] @ current_weights
            returns_post = asset_returns[:, exec_step:, :] @ post_weights
            # LEVERAGE: Subtract daily margin cost from leveraged period returns
            if margin_cost_daily > 0:
                returns_post = returns_post - margin_cost_daily
            returns_scen_all = np.hstack([returns_pre, returns_post]) if exec_step < total_steps else returns_pre
        else:
            returns_scen_all = asset_returns @ post_weights
            # LEVERAGE: Subtract daily margin cost from all scenario returns
            if margin_cost_daily > 0:
                returns_scen_all = returns_scen_all - margin_cost_daily

        # 5. Helper to create paths from returns
        def create_paths_from_returns(r_matrix, prefix, impact_ratio=1.0):
            # r_matrix: (N_paths, T_steps)
            cum_ret = np.cumprod(1 + r_matrix, axis=1)
            ones = np.ones((n_paths, 1))
            dataset = np.hstack([ones, cum_ret])
            values = dataset * initial_value * impact_ratio
            
            # Metrics
            # Fix: Calculate return relative to ORIGINAL initial_value to capture shock impact
            total_rets = (values[:, -1] / initial_value) - 1.0
            
            # Drawdown
            running_max = np.maximum.accumulate(values, axis=1)
            dds = (values - running_max) / running_max
            max_dds = np.min(dds, axis=1)
            
            # Volatility (Annualized)
            vols = np.std(r_matrix, axis=1) * np.sqrt(252)
            
            res_paths = []
            for i in range(n_paths):
                p = SimulationPath(
                    path_id=f"{prefix}_{i}",
                    daily_values=values[i, :].tolist(),
                    terminal_return_pct=total_rets[i] * 100,
                    terminal_volatility_pct=vols[i] * 100,
                    max_drawdown_pct=max_dds[i] * 100,
                    probability_weight=1.0/n_paths,
                    states=[] 
                )
                res_paths.append(p)
            return res_paths

        baseline_paths = create_paths_from_returns(returns_base_all, "base", 1.0)
        scenario_paths = create_paths_from_returns(returns_scen_all, "scen", scenario_impact_ratio)
        
        return baseline_paths, scenario_paths
    
    def _simulate_path(
        self,
        portfolio: Dict[str, Any],
        decision: Optional[StructuredDecision],
        price_paths: Dict[str, np.ndarray],
        tickers: List[str],
        weights: Dict[str, float],
        initial_value: float,
        total_steps: int,
        dt: float,
        path_idx: int
    ) -> SimulationPath:
        """
        Simulate a single path with or without decision execution.
        """
        states = []
        current_weights = weights.copy()
        current_value = initial_value
        
        # Determine decision execution step
        execution_step = 0
        if decision and decision.actions:
            max_delay = decision.get_max_execution_delay()
            execution_step = int(max_delay / dt) if max_delay > 0 else 0
        
        decision_executed = False
        max_value = initial_value
        min_value = initial_value
        
        for step in range(total_steps + 1):
            day_offset = step * dt
            
            # Calculate portfolio value at this step
            portfolio_return = 0.0
            for ticker in tickers:
                if ticker in price_paths and step > 0:
                    price_return = (price_paths[ticker][step] / price_paths[ticker][step - 1]) - 1
                    weight = current_weights.get(ticker, 0)
                    portfolio_return += weight * price_return
            
            if step > 0:
                current_value = current_value * (1 + portfolio_return)
            
            # Track max/min for drawdown
            max_value = max(max_value, current_value)
            min_value = min(min_value, current_value)
            
            # Execute decision at the right time
            if decision and not decision_executed and step >= execution_step:
                current_weights = self._execute_decision(
                    decision, current_weights, current_value
                )
                current_weights.pop("__leverage_meta__", None)
                decision_executed = True
            
            # Calculate metrics for this state
            vol = self._calculate_portfolio_volatility(current_weights, tickers)
            expected_ret = self._calculate_expected_return(current_weights, tickers)
            
            state = SimulationState(
                timestamp=datetime.utcnow() + timedelta(days=day_offset),
                day_offset=day_offset,
                prices={t: float(price_paths[t][step]) for t in tickers if t in price_paths},
                portfolio_weights=current_weights.copy(),
                portfolio_value=float(current_value),
                expected_return_pct=expected_ret,
                volatility_pct=vol,
                var_95_pct=vol * 1.65,  # Simplified VaR
                max_drawdown_pct=float((max_value - current_value) / max_value * 100) if max_value > 0 else 0,
            )
            states.append(state)
        
        # Calculate terminal metrics
        terminal_return = (current_value - initial_value) / initial_value * 100
        max_drawdown = (max_value - min_value) / max_value * 100 if max_value > 0 else 0
        
        return SimulationPath(
            path_id=f"path_{path_idx}_{secrets.token_hex(4)}",
            states=states,
            terminal_return_pct=float(terminal_return),
            terminal_volatility_pct=self._calculate_portfolio_volatility(current_weights, tickers),
            max_drawdown_pct=float(max_drawdown),
            path_integrated_risk=float(np.mean([s.var_95_pct for s in states])),
        )
    
    def _execute_decision(
        self,
        decision: StructuredDecision,
        current_weights: Dict[str, float],
        current_value: float
    ) -> Dict[str, float]:
        """
        Execute the decision and return new weights.
        """
        new_weights = current_weights.copy()
        
        for action in decision.actions:
            symbol = action.symbol.upper()
            asset_info = ASSET_RESOLVER.resolve_asset(symbol)
            if asset_info and asset_info.is_valid:
                symbol = asset_info.symbol
                # Canonicalize Indian stocks: TCS → TCS.NS
                if asset_info.country == "India" and not symbol.endswith((".NS", ".BO")):
                    symbol = symbol + ".NS"
            
            # Lookup current price if calculating based on shares
            current_price = None
            if action.size_shares is not None:
                 # Check initial_prices or default to 100 if simulation normalized
                 # In full simulation, prices are normalized to 100.0 at T=0 usually?
                 # Wait, _execute_decision is called with current_weights. 
                 # We need the price relative to portfolio value.
                 # If this is inside simulation loop, we assume normalized price?
                 # Actually, TemporalEngine normalizes prices to 100. 
                 # BUT, for "Buy X shares", we need the REAL price to know how much portfolio % that is.
                 # Optimization: If using normalized simulation (prices=100), 1 share = $100 value.
                 # Limitaton: Real-world share counts don't map 1:1 to normalized simulation.
                 # Correct approach for this Architecture:
                 # Simulation handles % weights. "10 shares" must be converted to % of portfolio 
                 # BEFORE simulation or using Real-World prices if available.
                 # For now, we will use a fallback or the passed in price if available?
                 # The simulation engine uses normalized prices (100).
                 pass

            # In this engine, we might not have real prices easily. 
            # However, for "fast" mode or "rebalance", we often just use 100.
            # Let's assume normalized price of 100 IF not provided, but usually we need real price.
            # For the purpose of this engine which runs on normalized 100 basis:
            price_to_use = 100.0 
            
            size = action.get_effective_size_percent(current_value, current_price=price_to_use)
            
            # Convert size to decimal weight
            size_weight = size / 100.0
            
            if action.direction == Direction.BUY:
                new_weights[symbol] = new_weights.get(symbol, 0) + size_weight
            elif action.direction == Direction.SELL:
                new_weights[symbol] = max(0, new_weights.get(symbol, 0) - size_weight)
            elif action.direction == Direction.SHORT:
                # Short positions are negative weights
                new_weights[symbol] = new_weights.get(symbol, 0) - size_weight
            elif action.direction == Direction.COVER:
                # Cover reduces short position
                new_weights[symbol] = min(0, new_weights.get(symbol, 0) + size_weight)
        
        # Normalize only for rebalance decisions
        if decision.decision_type == DecisionType.REBALANCE:
            total_weight = sum(abs(w) for w in new_weights.values())
            if total_weight > 0:
                for symbol in new_weights:
                    new_weights[symbol] = new_weights[symbol] / total_weight
        
        # LEVERAGE CORRECTION: If TRADE causes weights > 1.0, model explicit margin cost
        total_long = sum(w for w in new_weights.values() if w > 0)
        total_short = sum(abs(w) for w in new_weights.values() if w < 0)
        gross_exposure = total_long + total_short
        
        leverage_amount = max(0.0, gross_exposure - 1.0)
        
        # Store leverage metadata (consumed by _simulate_vectorized)
        # margin_rate = risk_free_rate + 150bps spread
        margin_rate_annual = self.market_params.risk_free_rate + 0.015
        margin_cost_daily = leverage_amount * margin_rate_annual / 252.0
        
        new_weights["__leverage_meta__"] = {
            "leverage_amount": leverage_amount,
            "margin_rate_annual": margin_rate_annual,
            "margin_cost_daily": margin_cost_daily,
            "gross_exposure": gross_exposure,
        }
        
        return new_weights
    
    def _calculate_portfolio_volatility(self, weights: Dict[str, float], tickers: List[str]) -> float:
        """Calculate portfolio volatility (simplified)."""
        variance = 0.0
        for ticker in tickers:
            w = weights.get(ticker, 0)
            vol = self.asset_volatilities.get(ticker, 0.25)
            variance += (w * vol) ** 2
        
        # Add correlation contribution (simplified)
        for i, t1 in enumerate(tickers):
            for t2 in tickers[i+1:]:
                w1 = weights.get(t1, 0)
                w2 = weights.get(t2, 0)
                vol1 = self.asset_volatilities.get(t1, 0.25)
                vol2 = self.asset_volatilities.get(t2, 0.25)
                variance += 2 * w1 * w2 * vol1 * vol2 * self.base_correlation
        
        return float(np.sqrt(variance) * 100)  # As percentage
    
    def _calculate_expected_return(self, weights: Dict[str, float], tickers: List[str]) -> float:
        """Calculate expected portfolio return (simplified)."""
        # Assume risk premium proportional to volatility
        risk_premium = 0.05  # 5% equity risk premium
        expected_return = self.market_params.risk_free_rate
        
        for ticker in tickers:
            w = weights.get(ticker, 0)
            vol = self.asset_volatilities.get(ticker, 0.25)
            # Higher vol assets have higher expected returns (CAPM-like)
            expected_return += w * vol * risk_premium
        
        return float(expected_return * 100)  # As percentage
    
    def compare(
        self,
        baseline_paths: List[SimulationPath],
        scenario_paths: List[SimulationPath],
        decision: StructuredDecision
    ) -> DecisionComparison:
        """
        Compare baseline vs. scenario paths to produce counterfactual analysis.
        """
        # Aggregate baseline metrics
        baseline_returns = [p.terminal_return_pct for p in baseline_paths]
        baseline_vols = [p.terminal_volatility_pct for p in baseline_paths]
        baseline_drawdowns = [p.max_drawdown_pct for p in baseline_paths]
        
        # Aggregate scenario metrics
        scenario_returns = [p.terminal_return_pct for p in scenario_paths]
        scenario_vols = [p.terminal_volatility_pct for p in scenario_paths]
        scenario_drawdowns = [p.max_drawdown_pct for p in scenario_paths]
        
        comparison = DecisionComparison(
            decision_id=decision.decision_id,
            
            baseline_expected_return=float(np.mean(baseline_returns)),
            baseline_volatility=float(np.mean(baseline_vols)),
            baseline_var_95=float(np.percentile(baseline_returns, 5)),
            baseline_max_drawdown=float(np.median(baseline_drawdowns)),
            baseline_max_drawdown_p5=float(np.percentile(baseline_drawdowns, 5)),
            baseline_tail_loss=float(np.percentile(baseline_returns, 1)),
            
            scenario_expected_return=float(np.mean(scenario_returns)),
            scenario_volatility=float(np.mean(scenario_vols)),
            scenario_var_95=float(np.percentile(scenario_returns, 5)),
            scenario_max_drawdown=float(np.median(scenario_drawdowns)),
            scenario_max_drawdown_p5=float(np.percentile(scenario_drawdowns, 5)),
            scenario_tail_loss=float(np.percentile(scenario_returns, 1)),
        )
        
        # Calculate deltas
        comparison.delta_return = comparison.scenario_expected_return - comparison.baseline_expected_return
        comparison.delta_volatility = comparison.scenario_volatility - comparison.baseline_volatility
        comparison.delta_var_95 = comparison.scenario_var_95 - comparison.baseline_var_95
        comparison.delta_drawdown = comparison.scenario_max_drawdown - comparison.baseline_max_drawdown
        comparison.delta_tail_loss = comparison.scenario_tail_loss - comparison.baseline_tail_loss
        
        # Calculate Sharpe ratios
        rf = self.market_params.risk_free_rate * 100
        comparison.sharpe_ratio_baseline = (comparison.baseline_expected_return - rf) / max(comparison.baseline_volatility, 0.01)
        comparison.sharpe_ratio_scenario = (comparison.scenario_expected_return - rf) / max(comparison.scenario_volatility, 0.01)
        
        # Information ratio
        tracking_error = float(np.std([s - b for s, b in zip(scenario_returns, baseline_returns)]))
        raw_ir = comparison.delta_return / max(tracking_error, 0.01)
        comparison.information_ratio = max(-5.0, min(5.0, raw_ir))  # Capped at ±5
        
        return comparison
    
    def _sigmoid_score(self, delta: float, sensitivity: float = 10.0) -> float:
        """Map a delta to [0, 100] using sigmoid. 50 = neutral."""
        # delta > 0 is good, delta < 0 is bad
        # Clamp exponent to prevent math.exp overflow on extreme deltas
        exponent = max(-500, min(500, -delta * sensitivity))
        raw = 1.0 / (1.0 + math.exp(exponent))
        return raw * 100.0

    def score(
        self,
        comparison: DecisionComparison,
        decision: StructuredDecision
    ) -> DecisionScore:
        """
        Calculate the final decision dominance score.
        """
        # Calculate component scores (0-100 scale, 50 = neutral)
        return_score = self._sigmoid_score(comparison.delta_return, sensitivity=5.0)
        risk_score = self._sigmoid_score(-comparison.delta_volatility, sensitivity=3.0)  # Lower vol is better
        tail_score = self._sigmoid_score(comparison.delta_tail_loss, sensitivity=5.0)  # More positive tail return is better
        drawdown_score = self._sigmoid_score(-comparison.delta_drawdown, sensitivity=3.0)  # Lower drawdown percentage (closer to 0) is better
        
        # Information ratio score
        efficiency_score = self._sigmoid_score(comparison.information_ratio, sensitivity=1.0)
        
        # Stability score (lower tracking error is more stable)
        stability_score = 70  # Default stable
        
        # Composite score (weighted average)
        composite = (
            return_score * 0.25 +
            risk_score * 0.20 +
            tail_score * 0.15 +
            drawdown_score * 0.15 +
            efficiency_score * 0.15 +
            stability_score * 0.10
        )
        
        # Round to integer for clean display
        composite = round(composite)
        
        # Determine verdict
        if composite >= 70:
            verdict = DecisionVerdict.STRONGLY_POSITIVE
        elif composite >= 55:
            verdict = DecisionVerdict.MODERATELY_POSITIVE
        elif composite >= 45:
            verdict = DecisionVerdict.NEUTRAL
        elif composite >= 30:
            verdict = DecisionVerdict.NEGATIVE
        else:
            verdict = DecisionVerdict.DANGEROUS
        
        # Generate key factors
        key_factors = []
        if comparison.delta_return > 0.5:
            key_factors.append(f"Improves expected return by {comparison.delta_return:.2f}%")
        elif comparison.delta_return < -0.5:
            key_factors.append(f"Reduces expected return by {abs(comparison.delta_return):.2f}%")
        
        if comparison.delta_volatility > 2:
            key_factors.append(f"Increases price fluctuation by {comparison.delta_volatility:.2f}%")
        elif comparison.delta_volatility < -2:
            key_factors.append(f"Reduces price fluctuation by {abs(comparison.delta_volatility):.2f}%")
        
        if comparison.delta_drawdown > 1:
            key_factors.append(f"Increases max drop by {comparison.delta_drawdown:.2f}%")
        
        # Generate warnings
        warnings = []
        if decision.has_shorts():
            warnings.append("Short positions carry unlimited loss potential")
        
        if not decision.is_immediate():
            warnings.append(f"Delayed execution introduces timing uncertainty")
        
        # Generate summary
        if verdict in [DecisionVerdict.STRONGLY_POSITIVE, DecisionVerdict.MODERATELY_POSITIVE]:
            summary = f"This decision is {verdict.value.replace('_', ' ')}. "
            if comparison.delta_return > 0:
                summary += f"Expected to improve returns by {comparison.delta_return:.2f}%."
            else:
                summary += f"Improves risk-adjusted returns despite lower expected return."
        elif verdict == DecisionVerdict.NEUTRAL:
            summary = "This decision has minimal impact on portfolio outcomes."
        else:
            summary = f"This decision is {verdict.value.replace('_', ' ')}. "
            if comparison.delta_return < 0:
                summary += f"Expected to reduce returns by {abs(comparison.delta_return):.2f}%."
            if comparison.delta_volatility > 0:
                summary += f" Increases risk by {comparison.delta_volatility:.2f}%."
        
        return DecisionScore(
            decision_id=decision.decision_id,
            verdict=verdict,
            return_score=return_score,
            risk_score=risk_score,
            tail_risk_score=tail_score,
            drawdown_score=drawdown_score,
            capital_efficiency_score=efficiency_score,
            stability_score=stability_score,
            composite_score=composite,
            summary=summary,
            key_factors=key_factors,
            warnings=warnings,
            confidence=0.85,  # Based on simulation quality
        )


def run_decision_intelligence(
    portfolio: Dict[str, Any],
    decision: StructuredDecision,
    horizon_days: int = 30,
    n_paths: int = 100,
    return_paths: bool = False,
    horizon_unit: str = "days",
    horizon_value: int = 30
) -> Tuple[DecisionComparison, DecisionScore, Optional[List[SimulationPath]], Optional[List[SimulationPath]]]:
    """
    Run the full decision intelligence pipeline.
    
    Args:
        portfolio: Current portfolio state
        decision: Structured decision to evaluate
        horizon_days: Simulation horizon
        n_paths: Number of Monte Carlo paths
        return_paths: If True, also return the raw simulation paths
        
    Returns:
        Tuple of (DecisionComparison, DecisionScore, baseline_paths, scenario_paths)
        If return_paths is False, the last two elements are None.
    """
    engine = TemporalSimulationEngine()
    
    # Run simulation
    baseline_paths, scenario_paths = engine.simulate(
        portfolio, decision, horizon_days, n_paths, 1, horizon_unit, horizon_value
    )
    
    # Compare
    comparison = engine.compare(baseline_paths, scenario_paths, decision)
    
    # Score
    score = engine.score(comparison, decision)
    
    if return_paths:
        return comparison, score, baseline_paths, scenario_paths
    return comparison, score, None, None


def run_decision_intelligence_fast(
    portfolio: Dict[str, Any],
    decision: StructuredDecision,
    horizon_days: int = 30,
    horizon_unit: str = "days",
    horizon_value: int = 30
) -> Tuple[DecisionComparison, DecisionScore]:
    """
    TIER 1: Fast approximation without Monte Carlo (~50ms).
    
    Uses mean-field approximation for instant results.
    Good for immediate UX feedback before deep simulation.
    
    Args:
        portfolio: Current portfolio state
        decision: Structured decision to evaluate
        horizon_days: Simulation horizon
        
    Returns:
        Tuple of (DecisionComparison, DecisionScore)
    """
    engine = TemporalSimulationEngine()
    
    # Helper: Normalize ticker to canonical form (India: TCS → TCS.NS)
    def _canon(t):
        t = t.strip().upper() if t else ""
        info = ASSET_RESOLVER.resolve_asset(t)
        if info and info.is_valid and info.country == "India" and not t.endswith((".NS", ".BO")):
            return t + ".NS"
        return t
    
    # Extract portfolio info
    positions = portfolio.get("positions", [])
    total_value = portfolio.get("total_value", 100000.0)
    tickers = [_canon(p.get("ticker")) for p in positions]
    weights = {_canon(p.get("ticker")): p.get("weight", 0) for p in positions}
    
    # Add decision assets
    for action in decision.actions:
        sym = _canon(action.symbol)
        if sym not in weights:
            tickers.append(sym)
            weights[sym] = 0.0
    
    # Calculate baseline metrics (current portfolio)
    baseline_vol = engine._calculate_portfolio_volatility(weights, tickers)
    baseline_ret = engine._calculate_expected_return(weights, tickers)
    
    # Execute decision (deterministically)
    scenario_weights = engine._execute_decision(decision, weights.copy(), total_value)
    scenario_weights.pop("__leverage_meta__", None)
    
    # Calculate scenario metrics
    scenario_vol = engine._calculate_portfolio_volatility(scenario_weights, tickers)
    scenario_ret = engine._calculate_expected_return(scenario_weights, tickers)
    
    # Determine equivalent trading days for scaling (6.5 hours = 1 day)
    if horizon_unit == "hours":
        equiv_days = horizon_value / 6.5
    else:
        equiv_days = max(1, horizon_days)
        
    time_scalar = (equiv_days / 252.0) ** 0.5
    
    # Estimate drawdown using volatility (rough approximation)
    # Max drawdown ~ 2.5 * volatility for normal markets
    baseline_drawdown = baseline_vol * 2.5 * time_scalar
    scenario_drawdown = scenario_vol * 2.5 * time_scalar
    
    # VaR approximation
    baseline_var = baseline_ret - 1.65 * baseline_vol * time_scalar
    scenario_var = scenario_ret - 1.65 * scenario_vol * time_scalar
    
    # Tail loss approximation (5th percentile)
    baseline_tail = baseline_ret - 2.33 * baseline_vol * time_scalar
    scenario_tail = scenario_ret - 2.33 * scenario_vol * time_scalar
    
    # Build comparison
    comparison = DecisionComparison(
        decision_id=decision.decision_id,
        
        baseline_expected_return=float(baseline_ret),
        baseline_volatility=float(baseline_vol),
        baseline_var_95=float(baseline_var),
        baseline_max_drawdown=float(baseline_drawdown),
        baseline_tail_loss=float(baseline_tail),
        
        scenario_expected_return=float(scenario_ret),
        scenario_volatility=float(scenario_vol),
        scenario_var_95=float(scenario_var),
        scenario_max_drawdown=float(scenario_drawdown),
        scenario_tail_loss=float(scenario_tail),
        
        delta_return=float(scenario_ret - baseline_ret),
        delta_volatility=float(scenario_vol - baseline_vol),
        delta_var_95=float(scenario_var - baseline_var),
        delta_drawdown=float(scenario_drawdown - baseline_drawdown),
        delta_tail_loss=float(scenario_tail - baseline_tail),
    )
    
    # Calculate Sharpe ratios
    rf = engine.market_params.risk_free_rate * 100
    comparison.sharpe_ratio_baseline = (baseline_ret - rf) / max(baseline_vol, 0.01)
    comparison.sharpe_ratio_scenario = (scenario_ret - rf) / max(scenario_vol, 0.01)
    raw_ir = comparison.delta_return / max(abs(comparison.delta_volatility), 0.01)
    comparison.information_ratio = max(-5.0, min(5.0, raw_ir))
    
    # Score the decision
    score = engine.score(comparison, decision)
    
    # Mark as fast approximation
    score.confidence = 0.6  # Lower confidence than full Monte Carlo
    score.warnings.append("Fast approximation - run full simulation for higher confidence")
    
    return comparison, score


def calculate_execution_context(
    portfolio: Dict[str, Any],
    decision: StructuredDecision
) -> ExecutionContext:
    """
    Calculate before/after exposure metrics for Section 2 of Universal Output Blueprint.
    """
    total_value = portfolio.get("total_value", 0.0)
    positions = portfolio.get("positions", [])
    
    # Before: Calculate current exposures
    long_exposure = sum(pos.get("weight", 0) for pos in positions if pos.get("weight", 0) > 0)
    short_exposure = sum(abs(pos.get("weight", 0)) for pos in positions if pos.get("weight", 0) < 0)
    
    gross_before = (long_exposure + short_exposure) * 100
    net_before = (long_exposure - short_exposure) * 100
    leverage_before = gross_before / 100 if gross_before > 0 else 1.0
    margin_before = short_exposure * 100  # Shorts require margin
    
    # After: Apply decision to calculate new exposures
    engine = TemporalSimulationEngine()
    
    # Helper: Normalize ticker to canonical form
    # e.g., "TCS" and "TCS.NS" should be treated as the same asset
    def _canonical_ticker(raw_ticker: str) -> str:
        t = raw_ticker.strip().upper()
        asset_info = ASSET_RESOLVER.resolve_asset(t)
        if asset_info and asset_info.is_valid:
            resolved = asset_info.symbol
            # If portfolio stored "TCS" but it's an Indian stock, canonicalize to "TCS.NS"
            if asset_info.country == "India" and not resolved.endswith((".NS", ".BO")):
                resolved = resolved + ".NS"
            return resolved
        return t
    
    weights = {}
    for p in positions:
        ticker = _canonical_ticker(str(p.get("ticker", "")))
        if not ticker: continue
        weights[ticker] = weights.get(ticker, 0.0) + p.get("weight", 0.0)
    
    # Add decision assets
    for action in decision.actions:
        symbol = _canonical_ticker(action.symbol)
        if symbol not in weights:
            weights[symbol] = 0.0
    
    new_weights = engine._execute_decision(decision, weights.copy(), total_value)
    new_weights.pop("__leverage_meta__", None)
    
    long_after = sum(w for w in new_weights.values() if w > 0)
    short_after = sum(abs(w) for w in new_weights.values() if w < 0)
    
    gross_after = (long_after + short_after) * 100
    net_after = (long_after - short_after) * 100
    leverage_after = gross_after / 100 if gross_after > 0 else 1.0
    margin_after = short_after * 100
    
    # Generate interpretation
    interpretation = ""
    if short_after > short_exposure:
        interpretation = "This trade introduces leverage, short exposure, and margin risk into your portfolio."
    elif gross_after > gross_before:
        interpretation = "This decision increases overall portfolio exposure."
    elif gross_after < gross_before:
        interpretation = "This decision reduces overall portfolio exposure."
    else:
        interpretation = "Minimal change to portfolio leverage structure."
    
    # Calculate asset deltas
    asset_deltas = []
    all_tickers = set(weights.keys()) | set(new_weights.keys())
    for t in all_tickers:
        w_before = weights.get(t, 0.0)
        w_after = new_weights.get(t, 0.0)
        delta = w_after - w_before
        if abs(delta) > 0.0001:  # Filter noise
            asset_deltas.append(AssetDelta(
                symbol=t, 
                weight_before=w_before, 
                weight_after=w_after, 
                weight_delta=delta
            ))
    
    # Sort by absolute delta descending (biggest changes first)
    asset_deltas.sort(key=lambda x: abs(x.weight_delta), reverse=True)

    return ExecutionContext(
        total_value_usd=total_value,
        gross_exposure_before=round(gross_before, 1),
        net_exposure_before=round(net_before, 1),
        leverage_before=round(leverage_before, 2),
        margin_usage_before=round(margin_before, 1),
        gross_exposure_after=round(gross_after, 1),
        net_exposure_after=round(net_after, 1),
        leverage_after=round(leverage_after, 2),
        margin_usage_after=round(margin_after, 1),
        interpretation=interpretation,
        asset_deltas=asset_deltas
    )


def calculate_risk_analysis(
    portfolio: Dict[str, Any],
    decision: StructuredDecision,
    comparison: DecisionComparison,
    scenario_paths: Optional[List[SimulationPath]] = None,
    horizon_days: int = 30
) -> RiskAnalysis:
    """
    Calculate advanced risk metrics for Sections 6-10 of Universal Output Blueprint.
    """
    total_value = portfolio.get("total_value", 100000.0)
    
    # Section 6: Primary Risk Drivers
    risk_drivers = []
    for action in decision.actions:
        symbol = action.symbol
        if action.direction == Direction.SHORT:
            risk_drivers.append(f"Short-position convexity under volatility spikes ({symbol})")
            risk_drivers.append(f"Earnings event gap risk ({symbol})")
        elif action.direction == Direction.BUY:
            # Determine sector
            tech_symbols = {"AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "AMD", "INTC", "TSLA"}
            if symbol in tech_symbols:
                risk_drivers.append("Tech-sector correlation clustering")
        
        if action.timing.type.value == "delay" and action.timing.delay_days:
            risk_drivers.append("Timing execution uncertainty from delayed entry")
    
    if not risk_drivers:
        risk_drivers = ["Market correlation risk", "Volatility regime shifts"]
    
    # Section 7: Time-to-Risk Realization
    # Use scenario paths if available, otherwise estimate from volatility
    if scenario_paths and len(scenario_paths) > 0:
        # Find average step where 5% drawdown is first breached
        breach_steps = []
        for path in scenario_paths:
            # OPTIMIZATION: Use daily_values
            if path.daily_values:
                peak = path.daily_values[0]
                for i, val in enumerate(path.daily_values):
                    if val > peak:
                        peak = val
                    # Avoid div by zero
                    if peak > 0:
                        dd = (val - peak) / peak
                        if dd <= -0.05: # 5% drop
                            breach_steps.append(i)
                            break
                continue

            # Fallback: states
            for i, state in enumerate(path.states):
                if state.max_drawdown_pct >= 5.0:
                    breach_steps.append(i)
                    break
        
        if breach_steps:
            avg_breach_step = sum(breach_steps) / len(breach_steps)
            time_to_risk = avg_breach_step  # In days
        else:
            time_to_risk = horizon_days * 0.3  # Estimate 30% into horizon
    else:
        # Estimate: Higher volatility = faster time to risk
        vol = comparison.scenario_volatility
        time_to_risk = max(1, min(horizon_days, 30 / (vol / 10 + 1)))
    
    time_to_risk_interp = ""
    if time_to_risk < 5:
        time_to_risk_interp = "If this trade goes wrong, significant losses are likely to appear quickly, not gradually."
    elif time_to_risk < 15:
        time_to_risk_interp = "Material losses could manifest within a couple of weeks under adverse conditions."
    else:
        time_to_risk_interp = "Risk realization would be gradual, allowing time for adjustment."
    
    # Section 8: Irreversibility Analysis
    # Permanent Loss Risk = CVaR-95 (Expected Shortfall) of scenario paths
    if scenario_paths and len(scenario_paths) > 0:
        terminal_returns = [p.terminal_return_pct / 100.0 for p in scenario_paths]
        var_95 = np.percentile(terminal_returns, 5)  # 5th percentile = VaR at 95% confidence
        # Expected Shortfall: mean of returns worse than or equal to VaR-95
        tail_returns = [r for r in terminal_returns if r <= var_95]
        cvar_95 = np.mean(tail_returns) if tail_returns else var_95
        worst_case_pct = min(abs(cvar_95) * 100, 100) # Cap at 100% loss
    else:
        # Fallback if no paths (e.g. fast approximation)
        tail_loss_pct = abs(comparison.scenario_tail_loss) if comparison.scenario_tail_loss < 0 else comparison.scenario_volatility * 2.5
        worst_case_pct = min(tail_loss_pct * 1.5, 100)  # Cap at 100%
        
    worst_case_usd = total_value * (worst_case_pct / 100)
    
    # Recovery time: Assuming 8% annual return to recover
    annual_return = 0.08
    if worst_case_pct > 0:
        # Compound recovery formula: time = ln(1/(1-loss%)) / ln(1+r)
        recovery_years = worst_case_pct / (annual_return * 100)
        recovery_months = recovery_years * 12
    else:
        recovery_months = 0
    
    irreversibility_interp = "Panic-exit during adverse conditions could lock in long-term capital damage." if worst_case_pct > 3 else "Downside risk is manageable."
    
    # Section 9: Regime Sensitivity
    sensitive_regimes = []
    for action in decision.actions:
        symbol = action.symbol
        tech_symbols = {"AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "AMD", "INTC", "TSLA"}
        energy_symbols = {"XOM", "CVX", "COP", "SLB"}
        finance_symbols = {"JPM", "GS", "BAC", "V", "MA"}
        
        if symbol in tech_symbols:
            if "Tech sell-off regimes" not in sensitive_regimes:
                sensitive_regimes.append("Tech sell-off regimes")
        if symbol in energy_symbols:
            if "Energy sector volatility" not in sensitive_regimes:
                sensitive_regimes.append("Energy sector volatility")
        if symbol in finance_symbols:
            if "Financial sector stress" not in sensitive_regimes:
                sensitive_regimes.append("Financial sector stress")
        
        if action.direction == Direction.SHORT:
            if "High-volatility macro transitions" not in sensitive_regimes:
                sensitive_regimes.append("High-volatility macro transitions")
            if "Risk-off market sentiment" not in sensitive_regimes:
                sensitive_regimes.append("Risk-off market sentiment")
    
    if not sensitive_regimes:
        sensitive_regimes = ["Broad market corrections", "Interest rate shocks"]
    
    # Section 10: Exposure Summary
    # Decision-attributed downside = Scenario tail loss - Baseline tail loss incremental
    delta_tail = comparison.delta_tail_loss if comparison.delta_tail_loss else 0
    downside_pct = max(0, abs(delta_tail) if delta_tail < 0 else comparison.scenario_max_drawdown - comparison.baseline_max_drawdown)
    downside_usd = total_value * (downside_pct / 100)
    
    # Upside from delta return
    upside_pct = max(0, comparison.delta_return)
    upside_usd = total_value * (upside_pct / 100)
    
    # Risk/Reward ratio
    if upside_usd > 0 and downside_usd > 0:
        ratio_val = downside_usd / upside_usd
        risk_reward = f"1 : {1/ratio_val:.2f}" if ratio_val > 0 else "1 : 0"
        if ratio_val > 1:
            risk_reward = f"1 : {1/ratio_val:.2f} (unfavorable)"
        else:
            risk_reward = f"1 : {1/ratio_val:.2f} (favorable)"
    else:
        risk_reward = "N/A"
    
    return RiskAnalysis(
        primary_risk_drivers=risk_drivers[:3],  # Limit to top 3
        time_to_risk_days=round(time_to_risk, 1),
        time_to_risk_interpretation=time_to_risk_interp,
        worst_case_permanent_loss_usd=round(worst_case_usd, 0),
        worst_case_permanent_loss_pct=round(worst_case_pct, 1),
        recovery_time_months=round(recovery_months, 0),
        irreversibility_interpretation=irreversibility_interp,
        sensitive_regimes=sensitive_regimes[:3],  # Limit to top 3
        decision_attributed_downside_usd=round(downside_usd, 0),
        decision_attributed_downside_pct=round(downside_pct, 1),
        decision_attributed_upside_usd=round(upside_usd, 0),
        decision_attributed_upside_pct=round(upside_pct, 2),
        risk_reward_ratio=risk_reward
    )


# Example usage
if __name__ == "__main__":
    from intent_parser import parse_decision
    
    # Sample portfolio
    portfolio = {
        "id": "prt_test",
        "total_value": 100000.0,
        "positions": [
            {"ticker": "SPY", "weight": 0.50},
            {"ticker": "AGG", "weight": 0.30},
            {"ticker": "AAPL", "weight": 0.20},
        ]
    }
    
    # Test decisions
    test_decisions = [
        "Short Apple 4% after 3 days",
        "Buy NVDA 10%",
        "Reduce AAPL 5%",
    ]
    
    print("=" * 70)
    print("TEMPORAL SIMULATION ENGINE TEST")
    print("=" * 70)
    
    for text in test_decisions:
        print(f"\n{'='*70}")
        print(f"Decision: {text}")
        print("=" * 70)
        
        decision = parse_decision(text, portfolio)
        comparison, score = run_decision_intelligence(portfolio, decision, n_paths=50)
        
        print(f"\n📊 Comparison:")
        print(f"  Baseline Return: {comparison.baseline_expected_return:.2f}%")
        print(f"  Scenario Return: {comparison.scenario_expected_return:.2f}%")
        print(f"  Delta Return: {comparison.delta_return:+.2f}%")
        print(f"  Delta Volatility: {comparison.delta_volatility:+.2f}%")
        print(f"  Delta Drawdown: {comparison.delta_drawdown:+.2f}%")
        
        print(f"\n🎯 Decision Score:")
        print(f"  Verdict: {score.verdict.value.upper()}")
        print(f"  Composite Score: {score.composite_score:.1f}/100")
        print(f"  Summary: {score.summary}")
        
        if score.key_factors:
            print(f"  Key Factors:")
            for factor in score.key_factors:
                print(f"    • {factor}")
        
        if score.warnings:
            print(f"  ⚠️  Warnings:")
            for warning in score.warnings:
                print(f"    • {warning}")


def calculate_projections(paths: List[SimulationPath]) -> Dict[str, float]:
    """
    Calculate average returns at specific time horizons from simulation paths.
    """
    if not paths:
        return {}
    
    # Target days
    horizons = {30: "1M", 90: "3M", 180: "6M", 365: "1Y"}
    projections = {}
    
    for days, label in horizons.items():
        # Collect returns for this horizon across all paths
        returns = []
        for path in paths:
            # OPTIMIZATION: Use vectorized daily_values if available
            if path.daily_values:
                # daily_values[0] is T=0
                # index k corresponds to T=k * (horizon/steps)?
                # Usually daily_values matches steps. Assuming 1 step per day.
                idx = min(days, len(path.daily_values) - 1)
                initial_val = path.daily_values[0]
                current_val = path.daily_values[idx]
                ret = (current_val - initial_val) / initial_val
                returns.append(ret)
                continue

            # Fallback to slow states iter
            target_state = None
            for state in path.states:
                if state.day_offset >= days:
                    target_state = state
                    break
            
            # If path ended before horizon, take last state
            if not target_state and path.states:
                target_state = path.states[-1]
                
            if target_state:
                # Calculate return from initial value (index 0)
                initial_val = path.states[0].portfolio_value
                current_val = target_state.portfolio_value
                ret = (current_val - initial_val) / initial_val
                returns.append(ret)
            
        # Average return
        avg_return = sum(returns) / len(returns) if returns else 0.0
        projections[label] = avg_return
        
    return projections
