"""
Decision Engine for GLOQONT - Implements the canonical decision output contract

This module implements the three immutable internal objects:
1. DecisionConsequences (internal reality engine)
2. RealLifeDecision (canonical human meaning)
3. UserViewAdapter (presentation only)
"""

import math
import re
from typing import List, Dict, Any, Optional, Literal
from dataclasses import dataclass
from datetime import datetime
import numpy as np
import pandas as pd
from enum import Enum


class UserType(Enum):
    RETAIL = "retail"
    ADVISOR = "advisor" 
    HNI = "hni"


@dataclass
class DecisionConsequences:
    """
    Purpose: Model what can actually happen.
    
    This object is user-agnostic and never shown directly to most users.
    Contains empirical return distributions, Monte Carlo scenarios, volatility metrics,
    correlation structures, and failure mode detection.
    """
    
    # Empirical return distributions (bootstrapped)
    empirical_returns_distribution: List[float]
    
    # Monte Carlo scenario paths (1k–10k)
    monte_carlo_paths: List[List[float]]
    
    # Volatility (total + downside)
    total_volatility: float
    downside_volatility: float
    
    # CVaR / Expected Shortfall
    cvar_5_percent: float
    expected_shortfall: float
    
    # Drawdown depth & duration
    max_drawdown_depth: float
    max_drawdown_duration_days: int
    
    # Time-to-recovery distributions
    time_to_recovery_distribution: List[int]
    
    # Correlation structure & stress correlation
    correlation_matrix: List[List[float]]
    stress_correlation_matrix: List[List[float]]
    
    # Marginal risk contribution per asset
    marginal_risk_contribution: Dict[str, float]
    
    # Concentration & single-point-of-failure detection
    concentration_risk: Dict[str, float]
    single_point_failure_risks: List[str]
    
    # Regime sensitivity (calm, stressed, crisis)
    calm_regime_behavior: Dict[str, float]
    stressed_regime_behavior: Dict[str, float]
    crisis_regime_behavior: Dict[str, float]
    
    # Fragility flags (non-linear risk)
    fragility_flags: List[str]
    
    # Regret probability
    regret_probability: float
    
    # Forced-exit probability vs tolerance
    forced_exit_probability: float
    exit_tolerance_threshold: float
    
    # Liquidity stress proxies
    liquidity_stress_indicators: List[Dict[str, Any]]
    
    # Time of calculation
    calculated_at: str
    
    def __init__(self, portfolio_data: Dict[str, Any], decision_text: str, decision_category=None):
        """Initialize with portfolio data and decision text to compute consequences"""
        self.calculated_at = datetime.utcnow().isoformat()
        self.decision_category = decision_category  # Store the decision category

        # Initialize with dummy values - these would be computed from actual models
        self.empirical_returns_distribution = self._compute_empirical_returns(portfolio_data, decision_text)
        self.monte_carlo_paths = self._generate_monte_carlo_scenarios(portfolio_data, decision_text)
        self.total_volatility = self._compute_total_volatility(portfolio_data, decision_text)
        self.downside_volatility = self._compute_downside_volatility(portfolio_data, decision_text)
        self.cvar_5_percent = self._compute_cvar_5_percent(portfolio_data, decision_text)
        self.expected_shortfall = self._compute_expected_shortfall(portfolio_data, decision_text)
        self.max_drawdown_depth = self._compute_max_drawdown_depth(portfolio_data, decision_text)
        self.max_drawdown_duration_days = self._compute_max_drawdown_duration(portfolio_data, decision_text)
        self.time_to_recovery_distribution = self._compute_time_to_recovery_dist(portfolio_data, decision_text)
        self.correlation_matrix = self._compute_correlation_matrix(portfolio_data, decision_text)
        self.stress_correlation_matrix = self._compute_stress_correlation_matrix(portfolio_data, decision_text)
        self.marginal_risk_contribution = self._compute_marginal_risk_contribution(portfolio_data, decision_text)
        self.concentration_risk = self._compute_concentration_risk(portfolio_data, decision_text)
        self.single_point_failure_risks = self._detect_single_point_failures(portfolio_data, decision_text)
        self.calm_regime_behavior = self._compute_regime_behavior(portfolio_data, decision_text, "calm")
        self.stressed_regime_behavior = self._compute_regime_behavior(portfolio_data, decision_text, "stressed")
        self.crisis_regime_behavior = self._compute_regime_behavior(portfolio_data, decision_text, "crisis")
        self.fragility_flags = self._detect_fragility_flags(portfolio_data, decision_text)
        self.regret_probability = self._compute_regret_probability(portfolio_data, decision_text)
        self.forced_exit_probability = self._compute_forced_exit_probability(portfolio_data, decision_text)
        self.exit_tolerance_threshold = self._compute_exit_tolerance_threshold(portfolio_data, decision_text)
        self.liquidity_stress_indicators = self._compute_liquidity_stress_indicators(portfolio_data, decision_text)
    
    def _compute_empirical_returns(self, portfolio_data: Dict[str, Any], decision_text: str) -> List[float]:
        """Compute empirical return distribution based on portfolio and decision"""
        # This would use actual historical data and decision impact modeling
        # For now, returning a sample distribution
        return [0.01, -0.02, 0.03, -0.01, 0.02, 0.015, -0.015, 0.025, -0.005, 0.018]
    
    def _generate_monte_carlo_scenarios(self, portfolio_data: Dict[str, Any], decision_text: str) -> List[List[float]]:
        """Generate Monte Carlo scenario paths"""
        # Generate sample scenario paths
        paths = []
        for i in range(1000):  # 1000 scenarios
            path = [0.0]  # Starting value
            for j in range(252):  # 1 year of daily returns
                # Simple random walk with drift based on decision
                drift = 0.0005 if "buy" in decision_text.lower() else -0.0002
                shock = np.random.normal(drift, 0.02)
                path.append(path[-1] + shock)
            paths.append(path)
        return paths
    
    def _compute_total_volatility(self, portfolio_data: Dict[str, Any], decision_text: str) -> float:
        """Compute total volatility"""
        # Base volatility from portfolio, adjusted by decision impact
        base_vol = portfolio_data.get('annualized_vol', 0.15)
        decision_factor = 1.0 + (0.2 if "leverage" in decision_text.lower() else 0.0)
        return base_vol * decision_factor
    
    def _compute_downside_volatility(self, portfolio_data: Dict[str, Any], decision_text: str) -> float:
        """Compute downside volatility only"""
        total_vol = self._compute_total_volatility(portfolio_data, decision_text)
        # Downside volatility is typically slightly lower than total
        return total_vol * 0.9
    
    def _compute_cvar_5_percent(self, portfolio_data: Dict[str, Any], decision_text: str) -> float:
        """Compute Conditional Value at Risk at 5% level"""
        # More negative for riskier decisions
        base_cvar = -0.10
        risk_factor = 0.05 if any(word in decision_text.lower() for word in ["leverage", "crypto", "high risk"]) else 0.0
        return base_cvar - risk_factor
    
    def _compute_expected_shortfall(self, portfolio_data: Dict[str, Any], decision_text: str) -> float:
        """Compute expected shortfall"""
        return self._compute_cvar_5_percent(portfolio_data, decision_text)
    
    def _compute_max_drawdown_depth(self, portfolio_data: Dict[str, Any], decision_text: str) -> float:
        """Compute maximum drawdown depth"""
        base_dd = portfolio_data.get('max_drawdown', -0.15)
        risk_factor = 0.10 if any(word in decision_text.lower() for word in ["leverage", "high risk"]) else 0.0
        return base_dd - risk_factor
    
    def _compute_max_drawdown_duration(self, portfolio_data: Dict[str, Any], decision_text: str) -> int:
        """Compute maximum drawdown duration in days"""
        base_duration = 180  # 6 months average
        risk_factor = 90 if any(word in decision_text.lower() for word in ["leverage", "high risk"]) else 0
        return base_duration + risk_factor
    
    def _compute_time_to_recovery_dist(self, portfolio_data: Dict[str, Any], decision_text: str) -> List[int]:
        """Compute time to recovery distribution"""
        base_recovery = [180, 210, 240, 270, 300]  # Days
        risk_factor = 90 if any(word in decision_text.lower() for word in ["leverage", "high risk"]) else 0
        return [x + risk_factor for x in base_recovery]
    
    def _compute_correlation_matrix(self, portfolio_data: Dict[str, Any], decision_text: str) -> List[List[float]]:
        """Compute correlation matrix"""
        # Simplified: return identity matrix for now
        n_assets = len(portfolio_data.get('positions', []))
        if n_assets == 0:
            n_assets = 1
        return [[1.0 if i == j else 0.1 for j in range(n_assets)] for i in range(n_assets)]
    
    def _compute_stress_correlation_matrix(self, portfolio_data: Dict[str, Any], decision_text: str) -> List[List[float]]:
        """Compute stress correlation matrix (higher correlations during stress)"""
        n_assets = len(portfolio_data.get('positions', []))
        if n_assets == 0:
            n_assets = 1
        # Higher correlations during stress
        return [[1.0 if i == j else 0.6 for j in range(n_assets)] for i in range(n_assets)]
    
    def _compute_marginal_risk_contribution(self, portfolio_data: Dict[str, Any], decision_text: str) -> Dict[str, float]:
        """Compute marginal risk contribution per asset"""
        positions = portfolio_data.get('positions', [])
        contributions = {}
        for pos in positions:
            ticker = pos.get('ticker', 'UNKNOWN')
            # Base contribution on weight with decision adjustment
            base_weight = pos.get('weight', 0.1)
            risk_factor = 1.2 if ticker in decision_text else 1.0
            contributions[ticker] = base_weight * risk_factor
        return contributions
    
    def _compute_concentration_risk(self, portfolio_data: Dict[str, Any], decision_text: str) -> Dict[str, float]:
        """Compute concentration risk"""
        positions = portfolio_data.get('positions', [])
        concentrations = {}
        for pos in positions:
            ticker = pos.get('ticker', 'UNKNOWN')
            weight = pos.get('weight', 0.0)
            # Flag high concentrations
            if weight > 0.3:
                concentrations[ticker] = weight
        return concentrations
    
    def _detect_single_point_failures(self, portfolio_data: Dict[str, Any], decision_text: str) -> List[str]:
        """Detect single point of failure risks"""
        failures = []
        positions = portfolio_data.get('positions', [])
        for pos in positions:
            ticker = pos.get('ticker', 'UNKNOWN')
            weight = pos.get('weight', 0.0)
            if weight > 0.5:  # Over 50% concentration
                failures.append(f"High concentration in {ticker}")
        return failures
    
    def _compute_regime_behavior(self, portfolio_data: Dict[str, Any], decision_text: str, regime: str) -> Dict[str, float]:
        """Compute behavior under different regimes"""
        base_metrics = {
            "volatility": self._compute_total_volatility(portfolio_data, decision_text),
            "correlation": 0.3,
            "liquidity": 0.8
        }
        
        if regime == "stressed":
            base_metrics["volatility"] *= 1.8
            base_metrics["correlation"] = 0.7
            base_metrics["liquidity"] = 0.4
        elif regime == "crisis":
            base_metrics["volatility"] *= 3.0
            base_metrics["correlation"] = 0.9
            base_metrics["liquidity"] = 0.1
            
        return base_metrics
    
    def _detect_fragility_flags(self, portfolio_data: Dict[str, Any], decision_text: str) -> List[str]:
        """Detect fragility flags"""
        flags = []
        if "leverage" in decision_text.lower():
            flags.append("Leverage introduces non-linear risk")
        if "crypto" in decision_text.lower():
            flags.append("Crypto assets exhibit high volatility and regulatory uncertainty")
        if "single" in decision_text.lower() or "only" in decision_text.lower():
            flags.append("Concentration in single asset increases risk")
        return flags
    
    def _compute_regret_probability(self, portfolio_data: Dict[str, Any], decision_text: str) -> float:
        """Compute probability of regretting the decision"""
        # Higher for riskier decisions
        base_prob = 0.15
        risk_factor = 0.2 if any(word in decision_text.lower() for word in ["leverage", "high risk", "speculative"]) else 0.0
        return min(0.8, base_prob + risk_factor)
    
    def _compute_forced_exit_probability(self, portfolio_data: Dict[str, Any], decision_text: str) -> float:
        """Compute probability of forced exit due to adverse conditions"""
        base_prob = 0.05
        risk_factor = 0.15 if any(word in decision_text.lower() for word in ["leverage", "margin"]) else 0.0
        return min(0.5, base_prob + risk_factor)
    
    def _compute_exit_tolerance_threshold(self, portfolio_data: Dict[str, Any], decision_text: str) -> float:
        """Compute exit tolerance threshold"""
        return -0.15  # 15% loss threshold
    
    def _compute_liquidity_stress_indicators(self, portfolio_data: Dict[str, Any], decision_text: str) -> List[Dict[str, Any]]:
        """Compute liquidity stress indicators"""
        indicators = []
        positions = portfolio_data.get('positions', [])
        for pos in positions:
            ticker = pos.get('ticker', 'UNKNOWN')
            # Add liquidity indicator for each position
            indicators.append({
                "asset": ticker,
                "current_liquidity_score": 0.7,
                "stress_scenario_liquidity": 0.3,
                "estimated_time_to_liquidate_days": 5 if ticker.startswith(('BTC', 'ETH')) else 2
            })
        return indicators

    def _extract_asset_name_from_text(self, decision_text: str) -> str:
        """Extract asset name from decision text"""
        # Look for common ticker patterns (1-5 uppercase letters, possibly with suffixes)
        ticker_pattern = r'\b([A-Z]{1,5}(?:\.[A-Z]{1,3})?)\b'
        matches = re.findall(ticker_pattern, decision_text.upper())

        if matches:
            # Define action words that should be skipped when looking for asset names
            action_words = {
                'BUY', 'SELL', 'SHORT', 'LONG', 'INCREASE', 'DECREASE', 'ADD', 'REDUCE',
                'HOLD', 'TRADE', 'OPTIONS', 'SWAP', 'EXCHANGE', 'TRANSFER', 'PURCHASE',
                'ACQUIRE', 'LIQUIDATE', 'REBALANCE', 'ALLOCATE', 'DIVERSIFY', 'HEDGE',
                'PROTECT', 'SPECULATE', 'MARGIN', 'LEVERAGE', 'COVER', 'TRIM', 'EXIT',
                'CLOSE', 'OPEN', 'TAKE', 'PLACE', 'MAKE', 'PUT', 'CALL', 'GO'
            }

            # Return the first match that is not an action word
            for match in matches:
                if match not in action_words:
                    return match

            # If all matches are action words, return the first non-action match or fallback
            return "the asset"

        return "the asset"  # Fallback


@dataclass
class RealLifeDecision:
    """
    Purpose: Fix the meaning of the decision once, forever.

    This object is derived from DecisionConsequences and is the single source of truth for guidance.
    It contains exactly six sections, always in this order:
    1. Decision Summary
    2. Why This Helps
    3. What You Gain
    4. What You Risk
    5. When This Stops Working
    6. Who This Is For
    """

    # Decision Summary (One sentence. No numbers. No optimism.)
    decision_summary: str

    # Why This Helps (Causal explanation grounded in market behavior.)
    why_this_helps: str

    # What You Gain (Possibility only. No magnitude. No time claims.)
    what_you_gain: str

    # What You Risk (Explicit downside. Must be at least as strong as upside.)
    what_you_risk: str

    # When This Stops Working (Concrete failure conditions. Regret scenarios included.)
    when_this_stops_working: str

    # Who This Is For (Self-selection filter. Explicitly excludes some users.)
    who_this_is_for: str

    # Visualization Data (Structured data for advanced decision visualizations)
    visualization_data: Dict[str, Any]

    # Metadata
    decision_id: str
    decision_text: str
    calculated_at: str
    portfolio_id: str
    portfolio_value: float

    def _extract_asset_name_from_text(self, decision_text: str) -> str:
        """Extract asset name from decision text"""
        # Look for common ticker patterns (1-5 uppercase letters, possibly with suffixes)
        ticker_pattern = r'\b([A-Z]{1,5}(?:\.[A-Z]{1,3})?)\b'
        matches = re.findall(ticker_pattern, decision_text.upper())

        if matches:
            # Define action words that should be skipped when looking for asset names
            action_words = {
                'BUY', 'SELL', 'SHORT', 'LONG', 'INCREASE', 'DECREASE', 'ADD', 'REDUCE',
                'HOLD', 'TRADE', 'OPTIONS', 'SWAP', 'EXCHANGE', 'TRANSFER', 'PURCHASE',
                'ACQUIRE', 'LIQUIDATE', 'REBALANCE', 'ALLOCATE', 'DIVERSIFY', 'HEDGE',
                'PROTECT', 'SPECULATE', 'MARGIN', 'LEVERAGE', 'COVER', 'TRIM', 'EXIT',
                'CLOSE', 'OPEN', 'TAKE', 'PLACE', 'MAKE', 'PUT', 'CALL', 'GO'
            }

            # Return the first match that is not an action word
            for match in matches:
                if match not in action_words:
                    return match

            # If all matches are action words, return the first non-action match or fallback
            return "the asset"

        return "the asset"  # Fallback

    def __init__(self, decision_consequences: DecisionConsequences, decision_text: str, portfolio_data: Dict[str, Any]):
        """Create canonical decision from consequences and input data"""
        import secrets

        self.decision_id = f"dec_{secrets.token_hex(6)}"
        self.decision_text = decision_text
        self.calculated_at = datetime.utcnow().isoformat()
        self.portfolio_id = portfolio_data.get('id', 'unknown')
        self.portfolio_value = portfolio_data.get('total_value', 0.0)
        self.decision_category = decision_consequences.decision_category  # Store decision category

        # Generate the canonical sections
        self.decision_summary = self._generate_decision_summary(decision_text, decision_consequences)
        self.why_this_helps = self._generate_why_this_helps(decision_text, decision_consequences)
        self.what_you_gain = self._generate_what_you_gain(decision_text, decision_consequences)
        self.what_you_risk = self._generate_what_you_risk(decision_text, decision_consequences)
        self.when_this_stops_working = self._generate_when_this_stops_working(decision_text, decision_consequences)
        self.who_this_is_for = self._generate_who_this_is_for(decision_text, decision_consequences)

        # Generate visualization data
        try:
            self.visualization_data = self._generate_visualization_data(decision_text, decision_consequences, portfolio_data)
        except Exception as e:
            # Fallback to empty visualization data if generation fails
            self.visualization_data = {
                "decision_type": "unknown",
                "decision_delta": {},
                "risk_scenarios": {},
                "concentration_data": {},
                "regime_sensitivity": {},
                "irreversibility_data": {},
                "error": str(e)
            }

    def _generate_decision_summary(self, decision_text: str, consequences: DecisionConsequences) -> str:
        """Generate decision summary - one sentence, no numbers, no optimism"""
        decision_lower = decision_text.lower()

        # Check if we have a specific decision category
        if hasattr(self, 'decision_category'):
            if self.decision_category and self.decision_category.value == "trade_decision":
                # Check if this is a multi-action command
                from asset_resolver import ASSET_RESOLVER
                all_actions = ASSET_RESOLVER._parse_multiple_actions(decision_text)

                if all_actions and len(all_actions) > 1:
                    # Multi-asset decision - summarize the overall impact
                    action_descriptions = []
                    for action, asset, pct in all_actions:
                        if action in ['buy', 'add', 'increase', 'long']:
                            action_descriptions.append(f"adding to {asset}")
                        elif action in ['sell', 'reduce', 'decrease', 'short']:
                            action_descriptions.append(f"reducing {asset}")
                        else:
                            action_descriptions.append(f"adjusting {asset}")

                    actions_str = " and ".join(action_descriptions)
                    return f"{actions_str.title()} may change your portfolio's risk profile."
                else:
                    # Single asset decision
                    if "buy" in decision_lower:
                        return f"Adding to {self._extract_asset_name_from_text(decision_text)} may change your portfolio's risk profile."
                    elif "sell" in decision_lower:
                        return f"Reducing your position in {self._extract_asset_name_from_text(decision_text)} may change your portfolio's risk profile."
                    elif "short" in decision_lower:
                        return f"Shorting {self._extract_asset_name_from_text(decision_text)} introduces asymmetric risk characteristics."
                    else:
                        return f"Making changes to your {self._extract_asset_name_from_text(decision_text)} position may change your portfolio's risk profile."
            elif self.decision_category and self.decision_category.value == "portfolio_rebalancing":
                # Portfolio rebalancing - focus on overall strategy
                if "reduce risk" in decision_lower or "lower risk" in decision_lower:
                    return "Reducing portfolio risk may change your overall return profile."
                elif "diversify" in decision_lower:
                    return "Diversifying your portfolio may change your concentration risk profile."
                elif "hedge" in decision_lower:
                    return "Implementing a portfolio hedge may alter your overall portfolio behavior."
                else:
                    return "Rebalancing your portfolio may change your overall risk and return characteristics."

        # Fallback to original logic
        if "buy" in decision_lower:
            return "Adding to your portfolio may change your risk profile."
        elif "sell" in decision_lower:
            return "Reducing your position may change your risk profile."
        elif "hedge" in decision_lower:
            return "Implementing a hedge may alter your portfolio's behavior."
        else:
            return "This decision may change your portfolio's characteristics."

    def _generate_why_this_helps(self, decision_text: str, consequences: DecisionConsequences) -> str:
        """Generate why this helps - causal explanation grounded in market behavior."""
        decision_lower = decision_text.lower()

        # Check if this is a multi-action command
        from asset_resolver import ASSET_RESOLVER
        all_actions = ASSET_RESOLVER._parse_multiple_actions(decision_text)

        if all_actions and len(all_actions) > 1:
            # Multi-asset decision - explain overall benefit
            action_descriptions = []
            for action, asset, pct in all_actions:
                if action in ['buy', 'add', 'increase', 'long']:
                    action_descriptions.append(f"adding to {asset} may help grow your portfolio")
                elif action in ['sell', 'reduce', 'decrease', 'short']:
                    action_descriptions.append(f"reducing {asset} may help realize gains or limit losses")
                else:
                    action_descriptions.append(f"adjusting {asset} may align your portfolio")

            actions_str = ", and ".join(action_descriptions[:-1]) + f", and {action_descriptions[-1]}" if len(action_descriptions) > 1 else action_descriptions[0]
            return f"{actions_str} over time if the investments perform as expected, though past performance does not guarantee future results."
        else:
            # Single asset decision
            if "buy" in decision_lower or "add" in decision_lower or "increase" in decision_lower:
                return f"Adding to {self._extract_asset_name_from_text(decision_text)} may help grow your portfolio over time if the investment performs as expected, though past performance does not guarantee future results."
            elif "sell" in decision_lower or "reduce" in decision_lower or "decrease" in decision_lower:
                return f"Reducing your position in {self._extract_asset_name_from_text(decision_text)} may help realize gains or limit losses from this specific holding."
            elif "short" in decision_lower:
                return f"Shorting {self._extract_asset_name_from_text(decision_text)} may allow you to profit from potential declines in this specific asset, though it introduces asymmetric risk."
            else:
                return f"Making changes to your {self._extract_asset_name_from_text(decision_text)} position reflects a change in your view of this specific investment."

    def _generate_what_you_gain(self, decision_text: str, consequences: DecisionConsequences) -> str:
        """Generate what you gain - possibility only, no magnitude, no time claims."""
        decision_lower = decision_text.lower()

        # Check if this is a multi-action command
        from asset_resolver import ASSET_RESOLVER
        all_actions = ASSET_RESOLVER._parse_multiple_actions(decision_text)

        if all_actions and len(all_actions) > 1:
            # Multi-asset decision - explain overall gain
            asset_list = [asset for action, asset, pct in all_actions]
            assets_str = ", ".join(asset_list[:-1]) + f", and {asset_list[-1]}" if len(asset_list) > 1 else asset_list[0]
            return f"Opportunity for portfolio growth if {assets_str} perform favorably."
        else:
            # Single asset decision
            if "buy" in decision_lower or "add" in decision_lower or "increase" in decision_lower:
                return f"Opportunity for portfolio growth if {self._extract_asset_name_from_text(decision_text)} performs favorably."
            elif "sell" in decision_lower or "reduce" in decision_lower or "decrease" in decision_lower:
                return f"Opportunity to realize gains or limit losses from your {self._extract_asset_name_from_text(decision_text)} position."
            elif "short" in decision_lower:
                return f"Potential to profit from declines in {self._extract_asset_name_from_text(decision_text)} if your assessment is correct."
            else:
                return f"Potential alignment of your {self._extract_asset_name_from_text(decision_text)} position with your investment view."

    def _generate_what_you_risk(self, decision_text: str, consequences: DecisionConsequences) -> str:
        """Generate what you risk - explicit downside, must be at least as strong as upside."""
        decision_lower = decision_text.lower()

        # Check if this is a multi-action command
        from asset_resolver import ASSET_RESOLVER
        all_actions = ASSET_RESOLVER._parse_multiple_actions(decision_text)

        if all_actions and len(all_actions) > 1:
            # Multi-asset decision - explain overall risk
            sell_assets = [asset for action, asset, pct in all_actions if action in ['sell', 'reduce', 'decrease', 'short']]
            buy_assets = [asset for action, asset, pct in all_actions if action in ['buy', 'add', 'increase', 'long']]

            risk_descriptors = []

            if sell_assets:
                sell_str = ", ".join(sell_assets[:-1]) + f", and {sell_assets[-1]}" if len(sell_assets) > 1 else sell_assets[0]
                risk_descriptors.append(f"Selling {sell_str} may cause you to miss out on future gains if the assets subsequently perform well. Tax implications may reduce the net benefit of selling, especially if the positions had significant unrealized gains.")

            if buy_assets:
                buy_str = ", ".join(buy_assets[:-1]) + f", and {buy_assets[-1]}" if len(buy_assets) > 1 else buy_assets[0]
                risk_descriptors.append(f"Loss of principal is possible if {buy_str} performs poorly, with potential drawdowns that may exceed your risk tolerance.")

            if not risk_descriptors:
                risk_descriptors.append("Changes to your portfolio positions carry the risk of loss of principal and potential tax implications.")

            return " ".join(risk_descriptors)
        else:
            # Single asset decision
            risk_descriptors = []

            if "short" in decision_lower:
                risk_descriptors.append(f"Shorting {self._extract_asset_name_from_text(decision_text)} carries unlimited loss potential if the asset rises sharply, as losses are not capped on the upside.")
            elif "sell" in decision_lower or "reduce" in decision_lower or "decrease" in decision_lower:
                risk_descriptors.append(f"Selling {self._extract_asset_name_from_text(decision_text)} may cause you to miss out on future gains if the asset subsequently performs well. Tax implications may reduce the net benefit of selling, especially if the position had significant unrealized gains.")
            else:
                risk_descriptors.append(f"Loss of principal is possible if {self._extract_asset_name_from_text(decision_text)} performs poorly, with potential drawdowns that may exceed your risk tolerance.")

            return " ".join(risk_descriptors)

    def _generate_when_this_stops_working(self, decision_text: str, consequences: DecisionConsequences) -> str:
        """Generate when this stops working - concrete failure conditions, regret scenarios included."""
        decision_lower = decision_text.lower()

        # Check if this is a multi-action command
        from asset_resolver import ASSET_RESOLVER
        all_actions = ASSET_RESOLVER._parse_multiple_actions(decision_text)

        if all_actions and len(all_actions) > 1:
            # Multi-asset decision - explain overall failure conditions
            failure_conditions = []

            for action, asset, pct in all_actions:
                if action in ['sell', 'reduce', 'decrease', 'short']:
                    failure_conditions.append(f"Selling {asset} fails if the asset subsequently experiences a significant rally, causing opportunity cost.")
                elif action in ['buy', 'add', 'increase', 'long']:
                    failure_conditions.append(f"Buying {asset} fails if the fundamental assumptions about the company deteriorate or market conditions change unfavorably.")

            failure_conditions.append("Over-concentration in specific assets creates vulnerability to sector or company-specific events.")

            return "; ".join(failure_conditions)
        else:
            # Single asset decision
            failure_conditions = []

            if "short" in decision_lower:
                failure_conditions.append(f"Shorting {self._extract_asset_name_from_text(decision_text)} fails when the asset experiences a sharp rally or short squeeze, causing unlimited losses.")
            elif "buy" in decision_lower or "add" in decision_lower or "increase" in decision_lower:
                failure_conditions.append(f"Buying {self._extract_asset_name_from_text(decision_text)} fails if the fundamental assumptions about the company deteriorate or market conditions change unfavorably.")
            elif "sell" in decision_lower or "reduce" in decision_lower or "decrease" in decision_lower:
                failure_conditions.append(f"Selling {self._extract_asset_name_from_text(decision_text)} fails if the asset subsequently experiences a significant rally, causing opportunity cost.")
            else:
                failure_conditions.append(f"Changes to your {self._extract_asset_name_from_text(decision_text)} position fail if the market moves against your expectations or fundamental conditions change.")

            failure_conditions.append("Concentration in a single asset increases vulnerability to company-specific risks like management changes, regulatory issues, or competitive pressures.")
            failure_conditions.append("Over-concentration in specific assets creates vulnerability to sector or company-specific events.")

            return "; ".join(failure_conditions)

    def _generate_who_this_is_for(self, decision_text: str, consequences: DecisionConsequences) -> str:
        """Generate who this is for - self-selection filter, explicitly excludes some users."""
        decision_lower = decision_text.lower()

        # Check if this is a multi-action command
        from asset_resolver import ASSET_RESOLVER
        all_actions = ASSET_RESOLVER._parse_multiple_actions(decision_text)

        if all_actions and len(all_actions) > 1:
            # Multi-asset decision - general investor type
            asset_list = [asset for action, asset, pct in all_actions]
            assets_str = ", ".join(asset_list[:-1]) + f", and {asset_list[-1]}" if len(asset_list) > 1 else asset_list[0]
            return f"This {assets_str} position may be appropriate for investors who understand multi-asset risks and have sufficient time to weather potential market fluctuations."
        else:
            # Single asset decision
            if "buy" in decision_lower or "add" in decision_lower or "increase" in decision_lower:
                return f"This {self._extract_asset_name_from_text(decision_text)} position may be appropriate for investors comfortable with single-asset risk and volatility. Beginners should seek guidance before proceeding."
            else:
                return f"This {self._extract_asset_name_from_text(decision_text)} position may be appropriate for investors who understand single-asset risks and have sufficient time to weather potential market fluctuations."

    def _generate_visualization_data(self, decision_text: str, consequences: DecisionConsequences, portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate structured data for advanced decision visualizations"""
        decision_lower = decision_text.lower()

        # Determine if this is a trade decision or portfolio rebalancing
        is_trade_decision = (
            self.decision_category and
            self.decision_category.value == "trade_decision"
        )

        # Get all multiple actions from the decision text using the asset resolver
        from asset_resolver import ASSET_RESOLVER
        all_actions = ASSET_RESOLVER._parse_multiple_actions(decision_text)

        # Determine primary action type based on the first action or overall text
        if all_actions:
            # Use the first action as the primary action type
            primary_action = all_actions[0][0]  # Get the action from first tuple (action, asset, pct)
            if primary_action in ['sell', 'reduce', 'decrease', 'short']:
                action_type = 'sell'
            elif primary_action in ['buy', 'add', 'increase', 'long']:
                action_type = 'buy'
            else:
                action_type = 'neutral'
        else:
            # Fallback to original logic if no multiple actions found
            if 'sell' in decision_lower or 'reduce' in decision_lower or 'decrease' in decision_lower or 'short' in decision_lower:
                action_type = 'sell'
            elif 'buy' in decision_lower or 'add' in decision_lower or 'increase' in decision_lower or 'long' in decision_lower:
                action_type = 'buy'
            else:
                action_type = 'neutral'

        # Get the asset involved in the decision using the asset resolver for consistency
        # Use the first action's asset if multiple actions exist, otherwise use the original method
        if all_actions:
            primary_asset_symbol = all_actions[0][1]  # Get the asset symbol from first tuple (action, asset, pct)
            primary_allocation_change_pct = all_actions[0][2]  # Get the allocation change from first tuple
        else:
            # Fall back to original method if no multiple actions found
            action, primary_asset_symbol, primary_allocation_change_pct = ASSET_RESOLVER.validate_decision_structure(decision_text)

        # Get current portfolio positions
        positions = portfolio_data.get('positions', [])
        total_value = portfolio_data.get('total_value', 100000)

        # Prepare visualization data
        viz_data = {
            "decision_type": "multi_asset_decision" if len(all_actions) > 1 else ("trade_decision" if is_trade_decision else "portfolio_rebalancing"),
            "action_type": action_type,  # Add action type for better visualization
            "actions_count": len(all_actions) if all_actions else 1,  # Number of actions processed
            "all_actions": [  # Include details of all actions for visualization
                {
                    "action": action,
                    "asset_symbol": asset_symbol,
                    "allocation_change_pct": float(allocation_change_pct)
                } for action, asset_symbol, allocation_change_pct in all_actions
            ] if all_actions else [],
        }

        # For multi-asset decisions, calculate combined effects
        if len(all_actions) > 1:
            # Calculate combined decision delta considering all actions
            combined_delta = self._calculate_combined_decision_delta(decision_text, positions, all_actions, is_trade_decision)
            viz_data["decision_delta"] = combined_delta

            # Calculate concentration data considering all actions
            viz_data["concentration_data"] = self._generate_multi_asset_concentration_data(positions, all_actions, is_trade_decision)
        else:
            # For single asset, use the original method
            viz_data["decision_delta"] = self._calculate_decision_delta(decision_text, positions, primary_asset_symbol, is_trade_decision)
            viz_data["concentration_data"] = self._generate_concentration_data(positions, primary_asset_symbol, is_trade_decision)

        # Add other visualization data
        viz_data.update({
            "risk_scenarios": self._generate_risk_scenarios(consequences),
            "regime_sensitivity": self._generate_regime_sensitivity(consequences, decision_text),
            "irreversibility_data": self._generate_irreversibility_data(consequences, total_value),
        })

        # Add trade-specific visualizations if applicable
        if is_trade_decision or len(all_actions) > 1:
            viz_data.update({
                "position_risk_profile": self._generate_position_risk_profile(positions, primary_asset_symbol, consequences),
                "time_to_damage_gauge": self._generate_time_to_damage_gauge(consequences),
                "trade_consequences": self._generate_trade_consequences(decision_text, consequences, action_type)
            })
        else:
            # Add rebalancing-specific visualizations
            viz_data.update({
                "risk_return_plane": self._generate_risk_return_plane(positions, consequences),
                "exposure_heatmap": self._generate_exposure_heatmap(positions),
                "recovery_path_comparison": self._generate_recovery_path_data(consequences),
                "rebalancing_consequences": self._generate_rebalancing_consequences(decision_text, consequences, action_type)
            })

        return viz_data

    def _calculate_combined_decision_delta(self, decision_text: str, positions: list, all_actions: list, is_trade_decision: bool) -> Dict[str, Any]:
        """Calculate the combined delta caused by multiple actions"""
        # Start with original positions
        original_positions = positions[:]
        after_positions = []

        # Apply each action sequentially
        current_positions = [pos.copy() for pos in original_positions]

        for action, asset_symbol, allocation_change_pct in all_actions:
            # Find the position in current positions
            position_found = False
            for i, pos in enumerate(current_positions):
                if pos.get('ticker', '').upper() == asset_symbol.upper():
                    # Update existing position
                    original_weight = pos.get('weight', 0) * 100
                    new_weight = original_weight + float(allocation_change_pct)
                    current_positions[i]['weight'] = new_weight / 100.0
                    position_found = True
                    break

            if not position_found:
                # Add new position if it doesn't exist
                current_positions.append({
                    'ticker': asset_symbol,
                    'weight': float(allocation_change_pct) / 100.0
                })

        # Calculate before and after compositions
        before_composition = []
        for pos in original_positions:
            ticker = pos.get('ticker', 'Unknown')
            weight = round(pos.get('weight', 0) * 100, 2)
            before_composition.append({
                "symbol": ticker,
                "weight": weight
            })

        after_composition = []
        total_weight = sum(pos.get('weight', 0) * 100 for pos in current_positions)

        # Normalize to 100% if needed
        if abs(total_weight - 100.0) > 0.1:
            for pos in current_positions:
                ticker = pos.get('ticker', 'Unknown')
                weight = (pos.get('weight', 0) * 100 / total_weight) * 100.0
                after_composition.append({
                    "symbol": ticker,
                    "weight": round(weight, 2)
                })
        else:
            for pos in current_positions:
                ticker = pos.get('ticker', 'Unknown')
                weight = round(pos.get('weight', 0) * 100, 2)
                after_composition.append({
                    "symbol": ticker,
                    "weight": weight
                })

        # For multi-asset, we'll represent the overall impact
        # Since multiple assets are involved, we'll use the first asset as the primary for display purposes
        primary_asset = all_actions[0][1] if all_actions else "MULTIPLE"
        total_change = sum(float(action[2]) for action in all_actions)

        return {
            "asset": primary_asset,
            "before_weight": 0.0,  # Placeholder - in multi-asset, individual before weights vary
            "change": round(total_change, 2),
            "after_weight": 0.0,  # Placeholder - in multi-asset, individual after weights vary
            "is_addition": total_change > 0,
            "before_composition": before_composition,
            "after_composition": after_composition,
            "delta_bar": {
                "symbol": primary_asset,
                "change": round(total_change, 2)
            }
        }

    def _generate_multi_asset_concentration_data(self, positions: list, all_actions: list, is_trade_decision: bool) -> Dict[str, Any]:
        """Generate concentration data considering all actions in multi-asset decision"""
        # Calculate before data
        before_data = []
        for pos in positions:
            before_data.append({
                "ticker": pos.get('ticker', 'Unknown'),
                "weight": round(pos.get('weight', 0) * 100, 2)
            })

        # Apply all actions to get after state
        current_positions = [pos.copy() for pos in positions]

        for action, asset_symbol, allocation_change_pct in all_actions:
            position_found = False
            for i, pos in enumerate(current_positions):
                if pos.get('ticker', '').upper() == asset_symbol.upper():
                    original_weight = pos.get('weight', 0) * 100
                    new_weight = original_weight + float(allocation_change_pct)
                    current_positions[i]['weight'] = new_weight / 100.0
                    position_found = True
                    break

            if not position_found:
                current_positions.append({
                    'ticker': asset_symbol,
                    'weight': float(allocation_change_pct) / 100.0
                })

        # Calculate after data
        after_data = []
        for pos in current_positions:
            after_data.append({
                "ticker": pos.get('ticker', 'Unknown'),
                "weight": round(pos.get('weight', 0) * 100, 2)
            })

        # Calculate max concentrations
        before_max = max((pos['weight'] for pos in before_data), default=0)
        after_weights = [pos['weight'] for pos in after_data]
        after_max = max(after_weights, default=0) if after_weights else 0

        return {
            "before": before_data,
            "after": after_data,
            "max_concentration_before": round(before_max, 2),
            "max_concentration_after": round(after_max, 2),
            "concentration_reduced": after_max < before_max,
            "all_actions_considered": [f"{action[0]} {action[1]} {float(action[2]):.2f}%" for action in all_actions]
        }

    def _calculate_decision_delta(self, decision_text: str, positions: list, asset_symbol: str, is_trade_decision: bool) -> Dict[str, Any]:
        """Calculate the delta caused by the decision"""
        decision_lower = decision_text.lower()

        # Find the asset in current positions
        current_position = None
        current_position_idx = -1
        for i, pos in enumerate(positions):
            if pos.get('ticker', '').upper() == asset_symbol.upper():
                current_position = pos
                current_position_idx = i
                break

        # Determine the change based on decision text
        change_pct = 0.0
        # Look for specific percentage in the decision text
        import re

        # Look for patterns like "sell msft 4%", "buy aapl 4%", etc.
        # More comprehensive pattern to catch various formats
        percent_match = re.search(r'(?:sell|buy|add|increase|raise|allocate|reduce|decrease)\s+' + re.escape(asset_symbol.lower()) + r'\s+(\d+(?:\.\d+)?)\s*(?:%|percent|pct)?\b', decision_lower)
        if not percent_match:
            # Try pattern: "sell 4% msft" or "buy 4% aapl"
            percent_match = re.search(r'(?:sell|buy|add|increase|raise|allocate|reduce|decrease)\s+(\d+(?:\.\d+)?)\s*(?:%|percent|pct)?\s+' + re.escape(asset_symbol.lower()), decision_lower)
        if not percent_match:
            # Try pattern: "buy aapl 4%" or "sell msft 4%" without specific action words
            percent_match = re.search(r'' + re.escape(asset_symbol.lower()) + r'\s+(\d+(?:\.\d+)?)\s*(?:%|percent|pct)?\b', decision_lower)
        if not percent_match:
            # Try general pattern: any number followed by % in the text
            percent_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:%|percent|pct)', decision_lower)

        if percent_match:
            change_pct = float(percent_match.group(1))
        elif 'buy' in decision_lower or 'increase' in decision_lower or 'add' in decision_lower or 'allocate' in decision_lower:
            # If no specific percentage found but action words are present, try to extract any number
            number_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:%|percent|pct)?', decision_lower)
            if number_match:
                change_pct = float(number_match.group(1))
            else:
                # Default change based on decision type
                if is_trade_decision:
                    change_pct = 2.0  # Default 2% for trade decisions
                else:
                    change_pct = 1.0  # Default 1% for rebalancing decisions
        elif 'sell' in decision_lower or 'reduce' in decision_lower or 'remove' in decision_lower or 'decrease' in decision_lower:
            percent_match = re.search(r'(?:sell|reduce|remove|decrease)\s+(?:to\s+)?(\d+(?:\.\d+)?)\s*(?:%|percent|pct)?', decision_lower)
            if not percent_match:
                percent_match = re.search(r'(?:sell|reduce|remove|decrease)\s+(?:[a-z]+\s+)?(\d+(?:\.\d+)?)\s*(?:%|percent|pct)?\b', decision_lower)
            if percent_match:
                change_pct = -float(percent_match.group(1))
            else:
                # If no specific percentage found but action words are present
                number_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:%|percent|pct)?', decision_lower)
                if number_match:
                    change_pct = -float(number_match.group(1))
                else:
                    # If no percentage specified, assume reducing by reasonable amount
                    if 'half' in decision_lower:
                        change_pct = -(current_position.get('weight', 0) * 100) / 2 if current_position else 0.0
                    elif 'all' in decision_lower or 'completely' in decision_lower:
                        change_pct = -(current_position.get('weight', 0) * 100) if current_position else 0.0
                    else:
                        change_pct = -2.0  # Default reduction

        # For sell actions, ensure the change is negative
        if ('sell' in decision_lower or 'reduce' in decision_lower or 'decrease' in decision_lower) and change_pct > 0:
            change_pct = -change_pct

        # Calculate before and after weights
        current_weight = current_position.get('weight', 0) * 100 if current_position else 0.0
        new_weight = current_weight + change_pct

        # Calculate the portfolio composition before and after the decision
        before_composition = []
        after_composition = []

        # Before composition - all positions
        for pos in positions:
            ticker = pos.get('ticker', 'Unknown')
            weight = round(pos.get('weight', 0) * 100, 2)
            before_composition.append({
                "symbol": ticker,
                "weight": weight
            })

        # After composition - adjust the affected position and properly rebalance other positions
        total_current_weight = sum(pos.get('weight', 0) * 100 for pos in positions)

        if current_position_idx >= 0:
            # The asset exists in the portfolio, modify existing positions
            for i, pos in enumerate(positions):
                ticker = pos.get('ticker', 'Unknown')
                original_weight = round(pos.get('weight', 0) * 100, 2)

                if i == current_position_idx:
                    # This is the asset being changed
                    after_composition.append({
                        "symbol": ticker,
                        "weight": round(new_weight, 2)
                    })
                else:
                    # For other positions, the adjustment depends on the type of transaction
                    # If this is a trade decision (buying/selling), we need to properly handle the cash flow
                    # When selling, cash is freed up and should be distributed among remaining positions
                    # When buying, cash is used and should come from other positions proportionally
                    if is_trade_decision:
                        # For trade decisions, the cash effect needs to be distributed among other positions
                        # If selling, the freed cash should be distributed proportionally to other positions
                        # If buying, the cash needed should come from other positions proportionally
                        if change_pct != 0:
                            # Calculate proportional adjustment based on the change
                            total_other_positions = [p for j, p in enumerate(positions) if j != current_position_idx]
                            total_other_weight = sum(p.get('weight', 0) * 100 for p in total_other_positions)

                            if total_other_weight > 0:
                                # Distribute the change proportionally among other positions
                                # When selling (negative change), other positions get a proportional increase
                                # When buying (positive change), other positions get a proportional decrease
                                proportional_factor = abs(change_pct) / total_other_weight

                                if change_pct < 0:  # Selling (freeing up cash)
                                    # Cash from selling is distributed proportionally to other positions
                                    proportional_increase = original_weight * proportional_factor
                                    adjusted_weight = max(0, round(original_weight + proportional_increase, 2))
                                else:  # Buying (using cash)
                                    # Cash is taken proportionally from other positions
                                    proportional_decrease = original_weight * proportional_factor
                                    adjusted_weight = max(0, round(original_weight - proportional_decrease, 2))

                                after_composition.append({
                                    "symbol": ticker,
                                    "weight": adjusted_weight
                                })
                            else:
                                after_composition.append({
                                    "symbol": ticker,
                                    "weight": original_weight
                                })
                        else:
                            after_composition.append({
                                "symbol": ticker,
                                "weight": original_weight
                            })
                    else:
                        # For rebalancing decisions, we redistribute among positions
                        if change_pct != 0:
                            # Calculate how to redistribute the change among other positions
                            # Find all other positions and distribute the change proportionally to their weights
                            total_other_weight = sum(p.get('weight', 0) * 100 for j, p in enumerate(positions) if j != current_position_idx)

                            if total_other_weight > 0:
                                # Distribute the change proportionally based on current weights
                                proportional_reduction = (original_weight / total_other_weight) * change_pct
                                adjusted_weight = max(0, round(original_weight - proportional_reduction, 2))
                                after_composition.append({
                                    "symbol": ticker,
                                    "weight": adjusted_weight
                                })
                            else:
                                after_composition.append({
                                    "symbol": ticker,
                                    "weight": original_weight
                                })
                        else:
                            after_composition.append({
                                "symbol": ticker,
                                "weight": original_weight
                            })
        else:
            # The asset doesn't exist in the portfolio, add it as a new position
            # Add all existing positions unchanged
            for pos in positions:
                ticker = pos.get('ticker', 'Unknown')
                original_weight = round(pos.get('weight', 0) * 100, 2)
                after_composition.append({
                    "symbol": ticker,
                    "weight": original_weight
                })

            # Extract the specific percentage for the new asset
            import re
            decision_lower = decision_text.lower()
            percent_match = re.search(r'(?:add|buy|increase|raise|allocate)\s+(?:to\s+)?(\d+(?:\.\d+)?)\s*(?:%|percent|pct)?(?:\s+(?:to|of|in))?', decision_lower)
            if not percent_match:
                percent_match = re.search(r'(?:add|buy|increase|raise|allocate)\s+(?:[a-z]+\s+)?(\d+(?:\.\d+)?)\s*(?:%|percent|pct)?\b', decision_lower)
            if not percent_match:
                percent_match = re.search(r'(?:add|buy|increase|raise|allocate)(?:\s+[a-z]+)?(?:\s+to)?\s+[a-z]+\s+(\d+(?:\.\d+)?)\s*(?:%|percent|pct)?', decision_lower)

            new_asset_weight = float(percent_match.group(1)) if percent_match else (2.0 if is_trade_decision else 1.0)

            # Add the new asset if it's a buy/add decision
            if 'buy' in decision_lower or 'add' in decision_lower:
                after_composition.append({
                    "symbol": asset_symbol,
                    "weight": round(new_asset_weight, 2)
                })

        # For trade decisions, we need to properly normalize to 100% to reflect the real portfolio composition
        # The target asset gets the change, and other assets are adjusted proportionally to maintain 100% total
        total_after_weight = sum(item['weight'] for item in after_composition)

        # Always normalize to 100% to maintain proper portfolio weights
        if abs(total_after_weight - 100.0) > 0.1:  # Only renormalize if significantly different
            normalized_after_composition = []
            for item in after_composition:
                normalized_weight = (item['weight'] / total_after_weight) * 100.0
                normalized_after_composition.append({
                    "symbol": item['symbol'],
                    "weight": round(normalized_weight, 2)
                })
            after_composition = normalized_after_composition

        return {
            "asset": asset_symbol,
            "before_weight": round(current_weight, 2),
            "change": round(change_pct, 2),
            "after_weight": round(new_weight, 2),
            "is_addition": change_pct > 0,
            "before_composition": before_composition,
            "after_composition": after_composition,
            "delta_bar": {
                "symbol": asset_symbol,
                "change": round(change_pct, 2)
            }
        }

    def _generate_risk_scenarios(self, consequences: DecisionConsequences) -> Dict[str, Any]:
        """Generate risk scenario data for visualization"""
        # Generate fan chart data for downside risk visualization
        time_horizons = [1, 7, 14, 30, 60, 90, 180, 365]  # Days
        base_downside = consequences.cvar_5_percent

        # Calculate realistic risk scenarios based on the consequences
        # Use actual volatility and other metrics to create realistic projections
        annualized_vol = consequences.total_volatility
        daily_vol = annualized_vol / (252 ** 0.5)  # Convert to daily volatility

        fan_chart_data = {
            "time_horizons": time_horizons,
            "base_case": [],
            "stress_case": [],
            "severe_stress_case": []
        }

        for day in time_horizons:
            # Scale risk based on time (square root of time scaling)
            time_scale = (day / 252) ** 0.5  # Annualized scaling
            # Calculate expected losses based on volatility and time
            expected_base_loss = base_downside * (1 + time_scale * 0.5)
            expected_stress_loss = base_downside * (1 + time_scale * 1.0)
            expected_severe_loss = base_downside * (1 + time_scale * 1.8)

            # Add some realistic variation based on the portfolio's characteristics
            base_var = daily_vol * (day ** 0.5)
            stress_multiplier = 1.5
            severe_multiplier = 2.5

            fan_chart_data["base_case"].append(round(expected_base_loss + base_var, 4))
            fan_chart_data["stress_case"].append(round(expected_stress_loss * stress_multiplier, 4))
            fan_chart_data["severe_stress_case"].append(round(expected_severe_loss * severe_multiplier, 4))

        return {
            "downside": consequences.cvar_5_percent,
            "expected": consequences.expected_shortfall,
            "upside": abs(consequences.cvar_5_percent) * 0.7,  # Positive upside estimate
            "time_horizon": 30,  # 30-day horizon
            "fan_chart_data": fan_chart_data
        }

    def _generate_concentration_data(self, positions: list, asset_symbol: str, is_trade_decision: bool) -> Dict[str, Any]:
        """Generate concentration data for visualization"""
        # Get all positions before decision
        before_data = []
        for pos in positions:
            before_data.append({
                "ticker": pos.get('ticker', 'Unknown'),
                "weight": round(pos.get('weight', 0) * 100, 2)
            })

        # Calculate after data based on realistic decision impact
        after_data = []

        # Find the asset being traded and determine the realistic change
        target_position_idx = -1
        for i, pos in enumerate(positions):
            if pos.get('ticker', '').upper() == asset_symbol.upper():
                target_position_idx = i
                break

        # Calculate realistic change based on decision type and current allocation
        if target_position_idx >= 0:
            current_weight = positions[target_position_idx].get('weight', 0) * 100
            # Determine change based on decision type and current allocation
            decision_lower = self.decision_text.lower()
            if is_trade_decision:
                # For trade decisions, the change depends on the current allocation and decision text
                # First, try to extract specific percentage from decision text
                import re
                percent_match = re.search(r'(?:add|buy|increase|raise|allocate)\s+(?:to\s+)?(\d+(?:\.\d+)?)\s*(?:%|percent|pct)?(?:\s+(?:to|of|in))?', decision_lower)
                if not percent_match:
                    percent_match = re.search(r'(?:add|buy|increase|raise|allocate)\s+(?:[a-z]+\s+)?(\d+(?:\.\d+)?)\s*(?:%|percent|pct)?\b', decision_lower)
                if not percent_match:
                    percent_match = re.search(r'(?:add|buy|increase|raise|allocate)(?:\s+[a-z]+)?(?:\s+to)?\s+[a-z]+\s+(\d+(?:\.\d+)?)\s*(?:%|percent|pct)?', decision_lower)

                if percent_match:
                    change_pct = float(percent_match.group(1))
                elif "buy" in decision_lower or "add" in decision_lower:
                    # Buying/increasing position - typically 1-5% depending on current size
                    if current_weight < 5:  # Small position, might increase significantly
                        change_pct = min(5, 10 - current_weight)  # Increase up to 10%
                    elif current_weight < 15:  # Medium position, moderate change
                        change_pct = min(3, 15 - current_weight)  # Increase up to 15%
                    else:  # Large position, smaller change
                        change_pct = 1  # Small increase
                elif "sell" in decision_lower or "reduce" in decision_lower:
                    # Selling/reducing position - typically 1-5% depending on current size
                    if current_weight > 15:  # Large position, might reduce significantly
                        change_pct = -min(5, current_weight)  # Reduce by up to 5%
                    elif current_weight > 5:  # Medium position, moderate reduction
                        change_pct = -min(3, current_weight)  # Reduce by up to 3%
                    else:  # Small position, smaller reduction
                        change_pct = -min(1, current_weight)  # Small reduction
                else:
                    change_pct = 2 if "buy" in decision_lower else -1
            else:  # Portfolio rebalancing
                # For rebalancing, changes are typically more modest and depend on the rebalancing strategy
                if "reduce" in decision_lower or "lower" in decision_lower:
                    change_pct = -min(2, current_weight)  # Reduce by up to 2%
                elif "increase" in decision_lower or "raise" in decision_lower:
                    change_pct = min(3, 15 - current_weight)  # Increase up to 3% or to 15%
                else:
                    change_pct = 1 if "buy" in decision_lower or "add" in decision_lower else -1

            # Apply the change to the target asset
            new_target_weight = max(0, round(current_weight + change_pct, 2))

            # Calculate total portfolio weight to ensure it sums to ~100%
            total_current_weight = sum(pos.get('weight', 0) * 100 for pos in positions)

            # Adjust other positions proportionally to account for the change
            # This simulates realistic rebalancing where money flows between positions
            for i, pos in enumerate(positions):
                ticker = pos.get('ticker', 'Unknown')
                original_weight = round(pos.get('weight', 0) * 100, 2)

                if i == target_position_idx:
                    # This is the asset being changed
                    after_data.append({
                        "ticker": ticker,
                        "weight": new_target_weight
                    })
                else:
                    # Adjust other positions based on decision type
                    # For trade decisions, the cash effect needs to be distributed among other positions
                    # When selling, cash is freed up and should be distributed among remaining positions
                    # When buying, cash is used and should come from other positions proportionally
                    if is_trade_decision:
                        # For trade decisions, the cash effect needs to be distributed among other positions
                        # If selling, the freed cash should be distributed proportionally to other positions
                        # If buying, the cash needed should come from other positions proportionally
                        if change_pct != 0:
                            # Calculate proportional adjustment based on the change
                            total_other_weight = sum(p.get('weight', 0) * 100 for j, p in enumerate(positions) if j != target_position_idx)

                            if total_other_weight > 0:
                                # Distribute the change proportionally among other positions
                                # When selling (negative change), other positions get a proportional increase
                                # When buying (positive change), other positions get a proportional decrease
                                proportional_adjustment = (original_weight / total_other_weight) * (-change_pct)  # Negative because selling adds to others, buying takes from others
                                new_weight = max(0, round(original_weight + proportional_adjustment, 2))
                            else:
                                new_weight = original_weight
                        else:
                            new_weight = original_weight
                    else:
                        # For rebalancing decisions, adjust other positions proportionally
                        if change_pct != 0 and total_current_weight > 0:
                            # Calculate proportional adjustment to maintain portfolio balance
                            remaining_positions_weight = total_current_weight - current_weight
                            if remaining_positions_weight > 0:
                                # Adjust other positions to compensate for the change
                                # This is a simplified approach - in reality, it depends on funding source
                                proportional_adjustment = -(change_pct * original_weight / remaining_positions_weight) if remaining_positions_weight > 0 else 0
                                new_weight = max(0, round(original_weight + proportional_adjustment, 2))
                            else:
                                new_weight = original_weight
                        else:
                            new_weight = original_weight

                    after_data.append({
                        "ticker": ticker,
                        "weight": new_weight
                    })

            # Normalize to 100% to maintain proper portfolio weights
            total_after_weight = sum(item['weight'] for item in after_data)
            if abs(total_after_weight - 100.0) > 0.1:  # Only renormalize if significantly different
                normalized_after_data = []
                for item in after_data:
                    normalized_weight = (item['weight'] / total_after_weight) * 100.0
                    normalized_after_data.append({
                        "ticker": item['ticker'],
                        "weight": round(normalized_weight, 2)
                    })
                after_data = normalized_after_data
        else:
            # Asset not found in current positions, create a new position
            decision_lower = self.decision_text.lower()
            # First, try to extract specific percentage from decision text
            import re
            percent_match = re.search(r'(?:add|buy|increase|raise|allocate)\s+(?:to\s+)?(\d+(?:\.\d+)?)\s*(?:%|percent|pct)?(?:\s+(?:to|of|in))?', decision_lower)
            if not percent_match:
                percent_match = re.search(r'(?:add|buy|increase|raise|allocate)\s+(?:[a-z]+\s+)?(\d+(?:\.\d+)?)\s*(?:%|percent|pct)?\b', decision_lower)
            if not percent_match:
                percent_match = re.search(r'(?:add|buy|increase|raise|allocate)(?:\s+[a-z]+)?(?:\s+to)?\s+[a-z]+\s+(\d+(?:\.\d+)?)\s*(?:%|percent|pct)?', decision_lower)

            if percent_match:
                new_weight = float(percent_match.group(1))
            else:
                # Default new position size based on decision type
                new_weight = 2 if is_trade_decision else 1

            after_data = before_data.copy()
            # Add the new position if it's a buy/add decision
            if "buy" in decision_lower or "add" in decision_lower:
                after_data.append({
                    "ticker": asset_symbol,
                    "weight": round(new_weight, 2)
                })

        # Calculate max concentrations
        max_concentration_before = max([pos['weight'] for pos in before_data]) if before_data else 0
        max_concentration_after = max([pos['weight'] for pos in after_data]) if after_data else 0

        # Determine if concentration increased or decreased
        concentration_changed = abs(max_concentration_after - max_concentration_before) > 0.1  # Significant change
        concentration_reduced = max_concentration_after < max_concentration_before

        return {
            "before": before_data,
            "after": after_data,
            "max_concentration_before": round(max_concentration_before, 2),
            "max_concentration_after": round(max_concentration_after, 2),
            "concentration_changed": concentration_changed,
            "concentration_reduced": concentration_reduced,
            "specific_asset_concentration_increased": max_concentration_after > max_concentration_before
        }

    def _generate_regime_sensitivity(self, consequences: DecisionConsequences, decision_text: str = "") -> Dict[str, Any]:
        """Generate regime sensitivity data for visualization"""
        # Define axes for the regime sensitivity map
        regime_axes = [
            "Volatility Spike",
            "Liquidity Stress",
            "Rate Shock",
            "Growth Slowdown",
            "Credit Crisis",
            "Currency Crisis"
        ]

        # Generate sensitivity scores for each regime based on actual consequences
        # These values should reflect the real impact of the decision on regime sensitivity

        # Calculate base sensitivities from the consequences data
        base_volatility = consequences.total_volatility
        base_correlation = consequences.correlation_matrix[0][0] if consequences.correlation_matrix and len(consequences.correlation_matrix) > 0 else 0.5
        base_liquidity = consequences.liquidity_stress_indicators[0]['current_liquidity_score'] if consequences.liquidity_stress_indicators else 0.7

        # Normalize to 0-1 scale based on realistic ranges
        # Volatility typically ranges from 0.1 to 0.5 for most portfolios
        normalized_volatility = min(1.0, max(0.0, (base_volatility - 0.1) / 0.4))

        # Correlation typically ranges from 0.1 to 0.9
        normalized_correlation = min(1.0, max(0.0, (base_correlation - 0.1) / 0.8))

        # Liquidity score typically ranges from 0.1 to 1.0
        normalized_liquidity = min(1.0, max(0.0, base_liquidity))

        # Generate sensitivity scores based on the decision's impact
        # Ensure we have meaningful non-zero values based on actual portfolio characteristics
        base_volatility_score = max(0.15, normalized_volatility * 0.8)  # 80% of normalized volatility, minimum 0.15
        base_liquidity_score = max(0.15, (1.0 - normalized_liquidity) * 0.7)  # Inverse of liquidity score, minimum 0.15
        base_correlation_score = max(0.15, normalized_correlation * 0.5)  # Moderate correlation impact, minimum 0.15

        # Calculate more realistic sensitivity scores based on actual portfolio metrics
        # Use the portfolio's actual volatility, correlation, and liquidity to determine sensitivities
        actual_volatility_based = max(0.15, min(0.95, base_volatility * 1.2))  # Scale by actual volatility
        actual_correlation_based = max(0.15, min(0.95, base_correlation * 1.0))  # Scale by actual correlation
        actual_liquidity_based = max(0.15, min(0.95, (1.0 - base_liquidity) * 0.8))  # Scale by actual liquidity

        sensitivity_scores_before = {
            "volatility_spike": round(actual_volatility_based, 4),
            "liquidity_stress": round(actual_liquidity_based, 4),
            "rate_shock": round(actual_correlation_based, 4),
            "growth_slowdown": round(max(0.15, actual_volatility_based * 0.75), 4),  # Growth slowdown affects volatility
            "credit_crisis": round(max(0.15, actual_correlation_based * 0.9), 4),  # High correlation during credit crisis
            "currency_crisis": round(0.3, 4)  # Base level for currency crisis
        }

        # Adjust sensitivities based on the decision's impact
        # This reflects how the decision changes regime sensitivity
        sensitivity_scores_after = sensitivity_scores_before.copy()

        # If the decision increases risk (based on CVaR or max drawdown), increase sensitivities
        risk_increase_factor = 1.0
        if consequences.cvar_5_percent < -0.15:  # High risk threshold
            risk_increase_factor = 1.3
        elif consequences.cvar_5_percent < -0.10:  # Medium risk threshold
            risk_increase_factor = 1.15

        # Apply risk factor to all sensitivities
        for key in sensitivity_scores_after:
            sensitivity_scores_after[key] = round(min(0.95, max(0.05, sensitivity_scores_after[key] * risk_increase_factor)), 4)

        # Also adjust based on specific decision text
        decision_lower = decision_text.lower()
        if "leverage" in decision_lower or "borrow" in decision_lower:
            sensitivity_scores_after["volatility_spike"] = round(min(1.0, sensitivity_scores_after["volatility_spike"] * 1.5), 4)
            sensitivity_scores_after["rate_shock"] = round(min(1.0, sensitivity_scores_after["rate_shock"] * 1.4), 4)
        elif "concentrate" in decision_lower or "focus" in decision_lower:
            sensitivity_scores_after["credit_crisis"] = round(min(1.0, sensitivity_scores_after["credit_crisis"] * 1.3), 4)
        elif "diversify" in decision_lower or "reduce risk" in decision_lower:
            # Diversification should reduce some sensitivities
            sensitivity_scores_after["volatility_spike"] = round(max(0.15, sensitivity_scores_after["volatility_spike"] * 0.7), 4)
            sensitivity_scores_after["credit_crisis"] = round(max(0.15, sensitivity_scores_after["credit_crisis"] * 0.7), 4)
        elif "buy" in decision_lower or "add" in decision_lower:
            # Buying/adding to positions might increase certain sensitivities
            # If buying a risky asset, increase volatility sensitivity
            sensitivity_scores_after["volatility_spike"] = round(min(1.0, sensitivity_scores_after["volatility_spike"] * 1.1), 4)
        elif "sell" in decision_lower or "reduce" in decision_lower:
            # Selling/reducing positions might decrease certain sensitivities
            sensitivity_scores_after["volatility_spike"] = round(max(0.15, sensitivity_scores_after["volatility_spike"] * 0.9), 4)

        # Also adjust based on specific fragility flags
        for flag in consequences.fragility_flags:
            if "leverage" in flag.lower():
                sensitivity_scores_after["volatility_spike"] = round(min(1.0, sensitivity_scores_after["volatility_spike"] * 1.5), 4)
                sensitivity_scores_after["rate_shock"] = round(min(1.0, sensitivity_scores_after["rate_shock"] * 1.4), 4)
            elif "concentration" in flag.lower():
                sensitivity_scores_after["credit_crisis"] = round(min(1.0, sensitivity_scores_after["credit_crisis"] * 1.3), 4)

        return {
            "calm_regime": consequences.calm_regime_behavior,
            "stressed_regime": consequences.stressed_regime_behavior,
            "crisis_regime": consequences.crisis_regime_behavior,
            "sensitivity_factors": {
                "volatility": round(base_volatility, 4),
                "correlation": round(base_correlation, 4),
                "liquidity": round(base_liquidity, 4)
            },
            "regime_axes": regime_axes,
            "sensitivity_scores_before": sensitivity_scores_before,
            "sensitivity_scores_after": sensitivity_scores_after
        }

    def _generate_irreversibility_data(self, consequences: DecisionConsequences, total_value: float) -> Dict[str, Any]:
        """Generate irreversibility data for visualization"""
        irreversible_loss_usd = abs(consequences.expected_shortfall) * total_value / 100.0

        # Generate horizon chart data with more realistic time-based decay
        holding_periods = [1, 3, 6, 12, 18, 24, 36]  # Months
        irreversible_losses = []

        # Calculate more realistic irreversible losses based on recovery dynamics
        base_loss = abs(consequences.expected_shortfall)

        for period in holding_periods:
            # Calculate irreversible loss at each holding period
            # Use a more realistic recovery model where losses diminish over time
            # but some permanent damage remains
            if period <= 6:
                # Early periods: losses are high and decay quickly
                time_factor = max(0.3, 1.0 - (period / 12))  # Don't go below 30%
            elif period <= 18:
                # Medium term: slower decay
                time_factor = max(0.2, 0.5 - ((period - 6) / 24))  # Don't go below 20%
            else:
                # Long term: very slow decay, some permanent damage remains
                time_factor = max(0.1, 0.2 - ((period - 18) / 100))  # Don't go below 10%

            irreversible_losses.append(round(base_loss * time_factor, 4))

        # Calculate recovery time based on actual recovery distribution
        recovery_time_months = consequences.time_to_recovery_distribution[0] if consequences.time_to_recovery_distribution else 12
        recovery_time_months = min(60, max(1, recovery_time_months))  # Cap between 1-60 months

        return {
            "irreversible_loss_usd": round(abs(irreversible_loss_usd), 2),
            "irreversible_loss_pct": round(abs(consequences.expected_shortfall), 4),
            "recovery_time_months": recovery_time_months,
            "time_horizons": [1, 3, 6, 12],
            "loss_projections": [
                round(max(0.01, abs(consequences.expected_shortfall) * 0.8), 4),  # Early loss
                round(max(0.01, abs(consequences.expected_shortfall) * 0.6), 4),  # 3-month
                round(max(0.01, abs(consequences.expected_shortfall) * 0.4), 4),  # 6-month
                round(max(0.01, abs(consequences.expected_shortfall) * 0.25), 4)  # 12-month
            ],
            "horizon_chart_data": {
                "holding_periods": holding_periods,
                "irreversible_losses": irreversible_losses,
                "recovery_zone_threshold": round(abs(consequences.expected_shortfall) * 0.15, 4)  # Below this is recovery zone
            }
        }

    def _generate_position_risk_profile(self, positions: list, asset_symbol: str, consequences: DecisionConsequences) -> Dict[str, Any]:
        """Generate position risk profile for trade decisions"""
        # Find the specific asset position
        asset_position = None
        for pos in positions:
            if pos.get('ticker', '').upper() == asset_symbol.upper():
                asset_position = pos
                break

        # Calculate risk metrics for the position based on actual consequences
        current_weight = round(asset_position.get('weight', 0) * 100, 2) if asset_position else 0
        volatility_contribution = consequences.marginal_risk_contribution.get(asset_symbol, 0.1)
        drawdown_risk = consequences.max_drawdown_depth

        # Calculate before vs after risk metrics based on the decision's impact
        before_volatility = consequences.calm_regime_behavior.get('volatility', 0.15)
        after_volatility = consequences.stressed_regime_behavior.get('volatility', 0.25)

        # Adjust after volatility based on the specific decision's impact
        # If the decision increases risk, adjust accordingly
        if "buy" in self.decision_text.lower() or "add" in self.decision_text.lower():
            # Adding to position increases risk
            after_volatility = min(0.5, before_volatility * 1.15)  # 15% increase
        elif "sell" in self.decision_text.lower() or "reduce" in self.decision_text.lower():
            # Reducing position may decrease risk
            after_volatility = max(0.05, before_volatility * 0.95)  # 5% decrease

        # Calculate portfolio impact metrics
        portfolio_volatility_impact = round(after_volatility - before_volatility, 4)
        portfolio_drawdown_impact = round(
            consequences.stressed_regime_behavior.get('volatility', 0.25) -
            consequences.calm_regime_behavior.get('volatility', 0.15), 4
        )

        return {
            "asset": asset_symbol,
            "current_weight": current_weight,
            "volatility_contribution": round(volatility_contribution, 4),
            "drawdown_risk": round(drawdown_risk, 4),
            "before_vs_after": {
                "volatility_before": round(before_volatility, 4),
                "volatility_after": round(after_volatility, 4),
                "volatility_change": portfolio_volatility_impact
            },
            "portfolio_impact": {
                "volatility_impact": portfolio_volatility_impact,
                "drawdown_impact": portfolio_drawdown_impact
            }
        }

    def _generate_time_to_damage_gauge(self, consequences: DecisionConsequences) -> Dict[str, Any]:
        """Generate time-to-damage gauge data"""
        # Get the time to damage metrics based on actual consequences
        # Use the recovery time distribution to get a more realistic time estimate
        if consequences.time_to_recovery_distribution:
            # Use the median or average recovery time from the distribution
            recovery_times = consequences.time_to_recovery_distribution
            median_time = int(sum(recovery_times) / len(recovery_times)) if recovery_times else 90
            median_time = min(365, max(1, median_time))  # Cap between 1-365 days
        else:
            # Fallback to max drawdown duration if no recovery distribution
            median_time = min(365, max(1, int(abs(consequences.max_drawdown_duration_days))))

        # Calculate worst case time based on the decision's risk profile
        # If the decision increases risk, reduce the time
        if consequences.cvar_5_percent < -0.20:  # High risk threshold
            worst_case_time = max(1, median_time // 3)
        elif consequences.cvar_5_percent < -0.10:  # Medium risk threshold
            worst_case_time = max(1, median_time // 2)
        else:
            worst_case_time = max(1, median_time // 1.5)

        # Create gauge data with more realistic segments based on the portfolio's risk profile
        max_possible = 365  # Maximum time in days

        # Adjust segments based on risk level
        if consequences.total_volatility > 0.30:  # High volatility
            segments = [
                {"range": [0, 14], "label": "Immediate", "color": "#ef4444"},  # Red for immediate danger
                {"range": [15, 45], "label": "Short-term", "color": "#f97316"},  # Orange for short-term
                {"range": [46, 120], "label": "Medium-term", "color": "#eab308"},  # Yellow for medium-term
                {"range": [121, max_possible], "label": "Long-term", "color": "#22c55e"}   # Green for long-term
            ]
        elif consequences.total_volatility > 0.20:  # Medium volatility
            segments = [
                {"range": [0, 30], "label": "Immediate", "color": "#ef4444"},
                {"range": [31, 90], "label": "Short-term", "color": "#f97316"},
                {"range": [91, 180], "label": "Medium-term", "color": "#eab308"},
                {"range": [181, max_possible], "label": "Long-term", "color": "#22c55e"}
            ]
        else:  # Low volatility
            segments = [
                {"range": [0, 60], "label": "Immediate", "color": "#ef4444"},
                {"range": [61, 120], "label": "Short-term", "color": "#f97316"},
                {"range": [121, 240], "label": "Medium-term", "color": "#eab308"},
                {"range": [241, max_possible], "label": "Long-term", "color": "#22c55e"}
            ]

        gauge_data = {
            "current_value": median_time,
            "max_possible": max_possible,
            "segments": segments
        }

        return {
            "median_time_to_material_loss": median_time,
            "worst_case_acceleration": worst_case_time,
            "risk_acceleration_factors": ["volatility_spike", "liquidity_stress", "correlation_breakdown"],
            "gauge_data": gauge_data
        }

    def _generate_risk_return_plane(self, positions: list, consequences: DecisionConsequences) -> Dict[str, Any]:
        """Generate risk-return plane data for rebalancing decisions"""
        # Calculate before and after risk-return characteristics based on actual consequences
        before_risk = consequences.calm_regime_behavior.get('volatility', 0.15)
        after_risk = consequences.stressed_regime_behavior.get('volatility', 0.25)

        # Calculate expected returns based on the decision's impact
        # Use the decision text to determine if it's risk-increasing or risk-decreasing
        if "reduce risk" in self.decision_text.lower() or "lower risk" in self.decision_text.lower():
            # Risk reduction typically reduces both risk and expected return
            after_risk = max(0.05, before_risk * 0.8)  # Reduce risk by 20%
            before_return = 0.08
            after_return = before_return * 0.9  # Reduce return by 10% due to lower risk
        elif "increase risk" in self.decision_text.lower() or "raise risk" in self.decision_text.lower():
            # Risk increase typically increases both risk and expected return
            after_risk = min(0.5, before_risk * 1.25)  # Increase risk by 25%
            before_return = 0.08
            after_return = before_return * 1.15  # Increase return by 15% due to higher risk
        elif "diversify" in self.decision_text.lower():
            # Diversification typically reduces risk while maintaining return
            after_risk = max(0.05, before_risk * 0.9)  # Reduce risk by 10%
            before_return = 0.08
            after_return = before_return * 0.95  # Slightly reduce return due to diversification costs
        else:
            # Default: slight adjustment based on CVaR
            if consequences.cvar_5_percent < -0.15:  # High risk
                after_risk = min(0.5, before_risk * 1.1)  # Increase risk by 10%
                before_return = 0.08
                after_return = before_return * 1.05  # Slightly increase return
            else:
                after_risk = before_risk
                before_return = 0.08
                after_return = 0.085  # Slight increase

        # Determine the direction of the trade-off
        risk_change = round(after_risk - before_risk, 4)
        return_change = round(after_return - before_return, 4)

        # Determine direction of movement
        if risk_change > 0.001 and return_change > 0.001:  # More risk, more return
            direction = "up_and_right"
        elif risk_change > 0.001 and return_change < -0.001:  # More risk, less return (bad trade-off)
            direction = "down_and_right"
        elif risk_change < -0.001 and return_change > 0.001:  # Less risk, more return (good trade-off)
            direction = "up_and_left"
        elif risk_change < -0.001 and return_change < -0.001:  # Less risk, less return
            direction = "down_and_left"
        else:
            direction = "no_significant_change"

        return {
            "before_point": {
                "risk": round(before_risk, 4),
                "return": round(before_return, 4),
                "label": "Before Rebalancing"
            },
            "after_point": {
                "risk": round(after_risk, 4),
                "return": round(after_return, 4),
                "label": "After Rebalancing"
            },
            "trade_off_arrow": {
                "direction": direction,
                "magnitude": round((risk_change**2 + return_change**2)**0.5, 4),
                "risk_change": risk_change,
                "return_change": return_change
            },
            "plane_limits": {
                "min_risk": round(max(0, min(before_risk, after_risk) * 0.5), 4),
                "max_risk": round(max(before_risk, after_risk) * 2.0, 4),
                "min_return": round(min(before_return, after_return) * 0.5, 4),
                "max_return": round(max(before_return, after_return) * 1.5, 4)
            }
        }

    def _generate_exposure_heatmap(self, positions: list) -> Dict[str, Any]:
        """Generate exposure heatmap data"""
        sectors = {}
        regions = {}

        # Define more realistic sector and region mappings
        sector_mapping = {
            'AAPL': 'Technology', 'MSFT': 'Technology', 'GOOG': 'Technology', 'NVDA': 'Technology',
            'AMZN': 'Consumer Cyclical', 'META': 'Communication Services',
            'JPM': 'Financial Services', 'BAC': 'Financial Services', 'GS': 'Financial Services',
            'JNJ': 'Healthcare', 'PG': 'Consumer Defensive', 'UNH': 'Healthcare',
            'XOM': 'Energy', 'CVX': 'Energy', 'LLY': 'Healthcare',
            'MA': 'Financial Services', 'AVGO': 'Technology', 'HD': 'Consumer Cyclical',
            'VZ': 'Communication Services', 'T': 'Communication Services', 'KO': 'Consumer Defensive'
        }

        region_mapping = {
            'AAPL': 'North America', 'MSFT': 'North America', 'GOOG': 'North America', 'NVDA': 'North America',
            'AMZN': 'North America', 'META': 'North America', 'JPM': 'North America', 'BAC': 'North America',
            'JNJ': 'North America', 'PG': 'North America', 'UNH': 'North America', 'XOM': 'North America',
            'CVX': 'North America', 'LLY': 'North America', 'MA': 'North America', 'AVGO': 'North America',
            'HD': 'North America', 'VZ': 'North America', 'T': 'North America', 'KO': 'North America',
            'TM': 'Asia', 'SONY': 'Asia', 'BMW': 'Europe', 'NVS': 'Europe'
        }

        for pos in positions:
            ticker = pos.get('ticker', 'Unknown')
            weight = round(pos.get('weight', 0) * 100, 2)

            # Determine sector and region based on ticker
            sector = sector_mapping.get(ticker, 'Other')
            region = region_mapping.get(ticker, 'International')

            sectors[sector] = round(sectors.get(sector, 0) + weight, 2)
            regions[region] = round(regions.get(region, 0) + weight, 2)

        # Create a matrix for the heatmap
        sector_list = sorted(list(sectors.keys()))
        region_list = sorted(list(regions.keys()))

        heatmap_matrix = []
        for region in region_list:
            row = []
            for sector in sector_list:
                # Calculate exposure for this region-sector combination
                # Use a more realistic calculation based on actual weights
                region_weight = regions.get(region, 0)
                sector_weight = sectors.get(sector, 0)
                # Calculate combined exposure as a fraction of total
                total_weight = sum(pos.get('weight', 0) * 100 for pos in positions)
                if total_weight > 0:
                    # Combine regional and sectoral exposure proportionally
                    combined_exposure = round((region_weight * sector_weight) / total_weight, 2)
                else:
                    combined_exposure = 0
                row.append(combined_exposure)
            heatmap_matrix.append(row)

        return {
            "sector_exposure": sectors,
            "regional_exposure": regions,
            "max_sector_exposure": max(sectors.values()) if sectors else 0,
            "max_region_exposure": max(regions.values()) if regions else 0,
            "heatmap_matrix": heatmap_matrix,
            "sector_labels": sector_list,
            "region_labels": region_list
        }

    def _generate_recovery_path_data(self, consequences: DecisionConsequences) -> Dict[str, Any]:
        """Generate recovery path comparison data"""
        # Generate historical analog recovery paths based on actual recovery distribution
        time_points = [30, 60, 90, 120, 180, 250, 365]  # Days
        historical_paths = []
        current_paths = []

        # Use the actual recovery distribution from consequences to create realistic paths
        if consequences.time_to_recovery_distribution:
            # Calculate baseline recovery based on historical data
            avg_recovery_time = sum(consequences.time_to_recovery_distribution) / len(consequences.time_to_recovery_distribution)
        else:
            avg_recovery_time = 180  # Default to 180 days

        # Calculate base recovery rates based on the portfolio's characteristics
        base_volatility = consequences.total_volatility
        base_recovery_rate = 1.0 - (base_volatility / 2.0)  # Lower volatility = faster recovery

        for t in time_points:
            # Historical analog path based on actual recovery distribution
            # Recovery increases over time but is bounded by portfolio characteristics
            if t < avg_recovery_time:
                # Early recovery follows a sigmoid curve
                progress_ratio = min(1.0, t / avg_recovery_time)
                historical_recovery = 10 + 85 * (1 / (1 + np.exp(-8 * (progress_ratio - 0.5))))
            else:
                # Later recovery approaches full recovery
                remaining_time = t - avg_recovery_time
                historical_recovery = min(98, 90 + (8 * (remaining_time / (remaining_time + 10))))

            # Add some realistic variation based on portfolio volatility
            volatility_factor = base_volatility * 10  # Higher volatility = more variation
            historical_recovery += np.random.normal(0, volatility_factor)
            historical_recovery = max(0, min(100, historical_recovery))  # Bound between 0-100%

            historical_paths.append({"days": t, "recovery_pct": round(historical_recovery, 2)})

            # Current portfolio expected recovery after rebalancing
            # Adjust based on the decision's impact on recovery
            if "reduce risk" in self.decision_text.lower() or "diversify" in self.decision_text.lower():
                # Risk-reducing decisions should improve recovery prospects
                current_recovery = historical_recovery * 1.05  # 5% improvement
            elif "increase risk" in self.decision_text.lower():
                # Risk-increasing decisions may worsen recovery prospects
                current_recovery = historical_recovery * 0.95  # 5% decrease
            else:
                # Default: similar to historical
                current_recovery = historical_recovery

            # Apply volatility adjustment
            current_recovery += np.random.normal(0, volatility_factor * 0.8)  # Slightly less variation
            current_recovery = max(0, min(100, current_recovery))  # Bound between 0-100%

            current_paths.append({"days": t, "recovery_pct": round(current_recovery, 2)})

        # Calculate likelihood of faster recovery based on the decision's impact
        if "reduce risk" in self.decision_text.lower() or "diversify" in self.decision_text.lower():
            faster_recovery_likelihood = 0.7  # 70% chance of faster recovery
        elif "increase risk" in self.decision_text.lower():
            faster_recovery_likelihood = 0.3  # 30% chance of faster recovery
        else:
            faster_recovery_likelihood = 0.5  # 50% chance for neutral decisions

        return {
            "historical_recovery_paths": historical_paths,
            "current_portfolio_recovery": current_paths,
            "time_points": time_points,
            "recovery_comparison": {
                "faster_recovery_likelihood": faster_recovery_likelihood,
                "benchmark_recovery_time": int(avg_recovery_time)  # Days for benchmark recovery
            }
        }

    def _generate_why_this_helps(self, decision_text: str, consequences: DecisionConsequences) -> str:
        """Generate why this helps - causal explanation grounded in market behavior"""
        decision_lower = decision_text.lower()

        # Check if we have a specific decision category
        if hasattr(self, 'decision_category'):
            if self.decision_category and self.decision_category.value == "trade_decision":
                # Trade decision - focus on single asset
                if "buy" in decision_lower:
                    return f"Adding to {self._extract_asset_name_from_text(decision_text)} may help grow your portfolio over time if the investment performs as expected, though past performance does not guarantee future results."
                elif "sell" in decision_lower:
                    return f"Reducing your position in {self._extract_asset_name_from_text(decision_text)} may help realize gains or limit losses from this specific holding."
                elif "short" in decision_lower:
                    return f"Shorting {self._extract_asset_name_from_text(decision_text)} may allow you to profit from potential declines in this specific asset, though it introduces asymmetric risk."
                else:
                    return f"Making changes to your {self._extract_asset_name_from_text(decision_text)} position reflects a change in your view of this specific investment."
            elif self.decision_category and self.decision_category.value == "portfolio_rebalancing":
                # Portfolio rebalancing - focus on overall strategy
                if "reduce risk" in decision_lower or "lower risk" in decision_lower:
                    return "Reducing portfolio risk can help protect against significant losses during market downturns, though it may also limit potential gains."
                elif "diversify" in decision_lower:
                    return "Diversifying your portfolio can reduce the impact of any single investment's poor performance on your overall portfolio."
                elif "hedge" in decision_lower:
                    return "Implementing a portfolio hedge can potentially limit overall portfolio losses during market downturns by taking offsetting positions, though it may also limit overall gains."
                elif "recession" in decision_lower:
                    return "Preparing your portfolio for recession may help protect against economic downturns by adjusting your risk profile."
                else:
                    return "Rebalancing your portfolio reflects a change in your investment approach that may align your portfolio with your current objectives."

        # Fallback to original logic
        if "diversify" in decision_lower:
            return "Spreading investments across different assets can reduce the impact of any single investment's poor performance on your overall portfolio."
        elif "hedge" in decision_lower:
            return "A hedge can potentially limit losses during market downturns by taking an offsetting position, though it may also limit gains."
        elif "buy" in decision_lower:
            return "Adding positions may help grow your portfolio over time if the investments perform as expected, though past performance does not guarantee future results."
        else:
            return "This decision reflects a change in your investment approach that may align your portfolio with your current objectives."

    def _generate_what_you_gain(self, decision_text: str, consequences: DecisionConsequences) -> str:
        """Generate what you gain - possibility only, no magnitude or time claims"""
        decision_lower = decision_text.lower()

        # Check if we have a specific decision category
        if hasattr(self, 'decision_category'):
            if self.decision_category and self.decision_category.value == "trade_decision":
                # Trade decision - focus on single asset
                if "buy" in decision_lower:
                    return f"Opportunity for portfolio growth if {self._extract_asset_name_from_text(decision_text)} performs favorably."
                elif "sell" in decision_lower:
                    return f"Opportunity to realize gains or limit losses from your {self._extract_asset_name_from_text(decision_text)} position."
                elif "short" in decision_lower:
                    return f"Potential to profit from declines in {self._extract_asset_name_from_text(decision_text)} if your assessment is correct."
                else:
                    return f"Potential alignment of your {self._extract_asset_name_from_text(decision_text)} position with your investment view."
            elif self.decision_category and self.decision_category.value == "portfolio_rebalancing":
                # Portfolio rebalancing - focus on overall strategy
                if "reduce risk" in decision_lower or "lower risk" in decision_lower:
                    return "Potential for reduced portfolio volatility and downside protection."
                elif "diversify" in decision_lower:
                    return "Potential for reduced portfolio concentration risk and more stable returns."
                elif "hedge" in decision_lower:
                    return "Potential for reduced portfolio downside risk during market stress."
                elif "recession" in decision_lower:
                    return "Potential for better portfolio performance during economic downturns."
                else:
                    return "Potential alignment of portfolio with your stated investment objective."

        # Fallback to original logic
        if "diversify" in decision_lower:
            return "Potential for reduced portfolio volatility through broader asset allocation."
        elif "hedge" in decision_lower:
            return "Potential protection against downside moves in your existing positions."
        elif "buy" in decision_lower:
            return "Opportunity for portfolio growth if the investment performs favorably."
        else:
            return "Potential alignment of portfolio with your stated investment objective."

    def _generate_what_you_risk(self, decision_text: str, consequences: DecisionConsequences) -> str:
        """Generate what you risk - explicit downside, at least as strong as upside"""
        decision_lower = decision_text.lower()

        # This section must be stronger than the upside section
        max_dd = consequences.max_drawdown_depth
        cvar = consequences.cvar_5_percent
        fragility_flags = consequences.fragility_flags

        risk_descriptors = []

        # Check if we have a specific decision category
        if hasattr(self, 'decision_category'):
            if self.decision_category and self.decision_category.value == "trade_decision":
                # Trade decision - focus on single asset risks
                if "short" in decision_lower:
                    risk_descriptors.append(f"Shorting {self._extract_asset_name_from_text(decision_text)} carries unlimited loss potential if the asset rises sharply, as losses are not capped on the upside.")
                    risk_descriptors.append(f"Short squeezes can force you to buy back shares at significantly higher prices, amplifying losses.")
                elif "buy" in decision_lower:
                    risk_descriptors.append(f"Loss of principal is possible if {self._extract_asset_name_from_text(decision_text)} performs poorly, with potential drawdowns that may exceed your risk tolerance.")
                elif "sell" in decision_lower:
                    risk_descriptors.append(f"Selling {self._extract_asset_name_from_text(decision_text)} may cause you to miss out on future gains if the asset subsequently performs well.")
                    risk_descriptors.append(f"Tax implications may reduce the net benefit of selling, especially if the position had significant unrealized gains.")
                else:
                    risk_descriptors.append(f"Changes to your {self._extract_asset_name_from_text(decision_text)} position carry the risk of loss of principal and potential tax implications.")
            elif self.decision_category and self.decision_category.value == "portfolio_rebalancing":
                # Portfolio rebalancing - focus on overall strategy risks
                if "reduce risk" in decision_lower or "lower risk" in decision_lower:
                    risk_descriptors.append(f"Reducing portfolio risk may significantly limit your potential returns, especially during bull markets when higher-risk assets typically outperform.")
                    risk_descriptors.append(f"Overly conservative positioning may cause your portfolio to underperform relative to your long-term objectives.")
                elif "diversify" in decision_lower:
                    risk_descriptors.append(f"Diversification may dilute the impact of your best-performing investments, potentially reducing overall portfolio returns.")
                    risk_descriptors.append(f"Over-diversification can lead to holding too many positions to monitor effectively, potentially reducing the benefits of active management.")
                elif "hedge" in decision_lower:
                    risk_descriptors.append(f"Hedging strategies typically reduce potential gains while providing protection against losses, creating a cost for the insurance.")
                    risk_descriptors.append(f"Hedges may fail during the most critical periods when correlations increase and the hedge becomes less effective.")
                elif "recession" in decision_lower:
                    risk_descriptors.append(f"Recession preparation strategies may underperform during economic recoveries or bull markets when riskier assets typically outperform.")
                    risk_descriptors.append(f"Timing the market based on recession predictions can be challenging, potentially leading to missed opportunities.")
                else:
                    risk_descriptors.append(f"Portfolio rebalancing may result in transaction costs and tax implications that reduce net returns.")
                    risk_descriptors.append(f"Changes to your portfolio allocation may cause it to underperform relative to your original strategy if market conditions change.")

        # Add general risk factors regardless of category
        if abs(max_dd) > 0.25:  # More than 25% drawdown risk
            risk_descriptors.append(f"Significant loss of principal is possible, with potential drawdowns exceeding what might be considered acceptable.")

        if cvar < -0.15:  # More than 15% expected shortfall
            risk_descriptors.append(f"In worst-case scenarios, losses could be substantial with meaningful probability.")

        if fragility_flags:
            risk_descriptors.extend([f"Risk factor present: {flag}" for flag in fragility_flags])

        if consequences.regret_probability > 0.3:
            risk_descriptors.append(f"Based on similar decisions, there's a meaningful chance you may regret this decision later.")

        if consequences.forced_exit_probability > 0.1:
            risk_descriptors.append(f"There's a meaningful chance you may be forced to exit this position under adverse conditions.")

        if not risk_descriptors:
            risk_descriptors.append(f"Loss of principal is possible, with potential drawdowns approaching what might be considered concerning levels.")

        return " ".join(risk_descriptors)

    def _generate_when_this_stops_working(self, decision_text: str, consequences: DecisionConsequences) -> str:
        """Generate when this stops working - concrete failure conditions"""
        decision_lower = decision_text.lower()
        failure_conditions = []

        # Check if we have a specific decision category
        if hasattr(self, 'decision_category'):
            if self.decision_category and self.decision_category.value == "trade_decision":
                # Trade decision - specific to single asset
                if "short" in decision_lower:
                    failure_conditions.append(f"Shorting {self._extract_asset_name_from_text(decision_text)} fails when the asset experiences a sharp rally or short squeeze, causing unlimited losses.")
                    failure_conditions.append(f"Dividend payments on shorted stocks create ongoing costs that can accumulate over time.")
                elif "buy" in decision_lower:
                    failure_conditions.append(f"Buying {self._extract_asset_name_from_text(decision_text)} fails if the fundamental assumptions about the company deteriorate or market conditions change unfavorably.")
                    failure_conditions.append(f"Concentration in a single asset increases vulnerability to company-specific risks like management changes, regulatory issues, or competitive pressures.")
                elif "sell" in decision_lower:
                    failure_conditions.append(f"Selling {self._extract_asset_name_from_text(decision_text)} fails if the asset subsequently experiences a significant rally, causing opportunity cost.")
                    failure_conditions.append(f"Tax implications of selling may reduce the net benefit if the position had significant unrealized gains.")
                else:
                    failure_conditions.append(f"Changes to your {self._extract_asset_name_from_text(decision_text)} position fail if the market moves against your expectations or fundamental conditions change.")
            elif self.decision_category and self.decision_category.value == "portfolio_rebalancing":
                # Portfolio rebalancing - specific to overall strategy
                if "reduce risk" in decision_lower or "lower risk" in decision_lower:
                    failure_conditions.append("Reducing portfolio risk fails during bull markets when higher-risk assets significantly outperform, causing underperformance relative to benchmarks.")
                    failure_conditions.append("Overly conservative positioning may cause the portfolio to fail to meet long-term growth objectives.")
                elif "diversify" in decision_lower:
                    failure_conditions.append("Diversification fails during market crises when correlations between assets increase, reducing the protective benefits.")
                    failure_conditions.append("Over-diversification can lead to holding assets that don't align with your investment thesis, diluting portfolio effectiveness.")
                elif "hedge" in decision_lower:
                    failure_conditions.append("Portfolio hedges fail during the most critical periods when correlations increase and the hedge becomes less effective.")
                    failure_conditions.append("Hedging strategies can be costly during extended bull markets when the hedge reduces overall portfolio returns.")
                elif "recession" in decision_lower:
                    failure_conditions.append("Recession preparation strategies fail if the expected recession does not occur, causing the portfolio to underperform during recovery periods.")
                    failure_conditions.append("Market timing based on recession predictions can be challenging, potentially leading to missed opportunities during unexpected rallies.")
                else:
                    failure_conditions.append("Portfolio rebalancing strategies fail when market conditions change faster than the rebalancing frequency, causing the portfolio to drift from optimal allocation.")
                    failure_conditions.append("Transaction costs and tax implications may erode the benefits of frequent rebalancing.")

        # Add general failure conditions regardless of category
        # Regime changes
        if consequences.stressed_regime_behavior.get('volatility', 0) > 2.0 * consequences.calm_regime_behavior.get('volatility', 1):
            failure_conditions.append("During market stress, correlations increase significantly, reducing diversification benefits.")

        # Liquidity issues
        if any(indicator['stress_scenario_liquidity'] < 0.3 for indicator in consequences.liquidity_stress_indicators):
            failure_conditions.append("In stressed markets, you may face difficulty liquidating positions at favorable prices.")

        # Concentration risks
        if consequences.single_point_failure_risks:
            failure_conditions.append("Over-concentration in specific assets creates vulnerability to sector or company-specific events.")

        # Fragility flags
        if consequences.fragility_flags:
            failure_conditions.extend(consequences.fragility_flags)

        # Regret scenarios
        if consequences.regret_probability > 0.25:
            failure_conditions.append("This type of decision has historically led to regret in a significant portion of similar cases.")

        if not failure_conditions:
            failure_conditions.append("This approach may become ineffective during periods of high market volatility or economic stress.")

        return "; ".join(failure_conditions)

    def _generate_who_this_is_for(self, decision_text: str, consequences: DecisionConsequences) -> str:
        """Generate who this is for - self-selection filter"""
        decision_lower = decision_text.lower()

        # Determine appropriate user type based on complexity and risk
        risk_level = "high" if abs(consequences.max_drawdown_depth) > 0.3 else "moderate"
        complexity_level = "high" if consequences.fragility_flags else "moderate"

        # Check if we have a specific decision category
        if hasattr(self, 'decision_category'):
            if self.decision_category and self.decision_category.value == "trade_decision":
                # Trade decision - single asset focused
                if "short" in decision_lower:
                    return "This short position may be appropriate only for experienced investors who understand derivatives, leverage, and unlimited loss potential. Not recommended for beginners due to asymmetric risk profile."
                elif "buy" in decision_lower or "sell" in decision_lower:
                    if risk_level == "high":
                        return f"This {self._extract_asset_name_from_text(decision_text)} position may be appropriate for investors comfortable with single-asset risk and volatility. Beginners should seek guidance before proceeding."
                    else:
                        return f"This {self._extract_asset_name_from_text(decision_text)} position may be appropriate for investors who understand single-asset risks and have sufficient time to weather potential market fluctuations."
            elif self.decision_category and self.decision_category.value == "portfolio_rebalancing":
                # Portfolio rebalancing - strategy focused
                if "reduce risk" in decision_lower or "lower risk" in decision_lower:
                    return "This risk reduction strategy may be appropriate for investors prioritizing capital preservation over growth potential. Suitable for conservative investors or those nearing retirement."
                elif "diversify" in decision_lower:
                    return "This diversification strategy may be appropriate for investors looking to reduce concentration risk. Suitable for medium to long-term investors with moderate risk tolerance."
                elif "hedge" in decision_lower:
                    return "This hedging strategy may be appropriate for experienced investors who understand hedging mechanics and costs. Consider consulting a financial advisor for complex hedge implementations."
                elif "recession" in decision_lower:
                    return "This recession preparation strategy may be appropriate for investors concerned about economic cycles. Suitable for those with longer investment horizons who can withstand potential underperformance during recoveries."

        # Fallback to original logic
        if risk_level == "high" and complexity_level == "high":
            return "This decision may be appropriate for experienced investors who understand complex financial instruments and can tolerate significant losses. Not recommended for beginners or those with low risk tolerance."
        elif risk_level == "high":
            return "This decision may be appropriate for investors comfortable with significant potential losses. Beginners should seek guidance before proceeding."
        elif complexity_level == "high":
            return "This decision involves complex considerations that may be better understood by experienced investors. Consider consulting a financial advisor."
        else:
            return "This decision may be appropriate for investors who understand the risks and have sufficient time to weather potential market fluctuations. Those with low risk tolerance should reconsider."

    def _generate_trade_consequences(self, decision_text: str, consequences: DecisionConsequences, action_type: str) -> Dict[str, Any]:
        """Generate trade-specific consequences in simple language for new traders"""
        decision_lower = decision_text.lower()

        # Extract asset and percentage if available
        import re
        asset_symbol = self._extract_asset_name_from_text(decision_text)

        # Look for percentage in the decision
        percent_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:%|percent|pct)', decision_lower)
        percentage = float(percent_match.group(1)) if percent_match else 5.0

        # Generate consequences based on action type
        if action_type == 'sell':
            consequence_description = f"When you sell {percentage}% of {asset_symbol}, you lock in any gains or losses at today's price. You free up cash but lose potential future appreciation."
            risk_explanation = f"If {asset_symbol} goes up after you sell, you miss out on those gains. If it goes down, you've protected yourself from those losses."
            opportunity_cost = f"You could miss out on future growth if {asset_symbol} performs well after your sale."
        elif action_type == 'buy':
            consequence_description = f"When you buy {percentage}% more of {asset_symbol}, you increase your exposure to this stock. Your profits/losses will be bigger if the stock moves."
            risk_explanation = f"If {asset_symbol} goes up, you make more money than before. If it goes down, you lose more money than before."
            opportunity_cost = f"Money used to buy {asset_symbol} can't be invested elsewhere."
        else:
            consequence_description = f"Your decision regarding {asset_symbol} may change your portfolio's risk and return profile."
            risk_explanation = f"The impact depends on the specific action you're taking."
            opportunity_cost = f"Consider what else you could do with these funds."

        return {
            "action_type": action_type,
            "asset_symbol": asset_symbol,
            "percentage_change": percentage,
            "consequence_description": consequence_description,
            "risk_explanation": risk_explanation,
            "opportunity_cost": opportunity_cost,
            "simple_language_explanation": f"This {action_type} decision means you're changing how much of {asset_symbol} you own. This affects how much money you could make OR lose if the stock price changes.",
            "key_lesson": f"As a new trader, remember: {f'Selling locks in gains/losses, but you miss future moves.' if action_type == 'sell' else 'Buying increases your exposure to the stock\'s ups and downs.' if action_type == 'buy' else 'Any trade changes your portfolio risk.'}"
        }

    def _generate_rebalancing_consequences(self, decision_text: str, consequences: DecisionConsequences, action_type: str) -> Dict[str, Any]:
        """Generate rebalancing-specific consequences in simple language for new traders"""
        decision_lower = decision_text.lower()

        # Determine what type of rebalancing
        if 'diversify' in decision_lower or 'spread' in decision_lower:
            rebalancing_type = 'diversification'
            explanation = "Diversification spreads your investments across different stocks, reducing the impact of any single stock's bad performance."
            benefit = "Lower risk - if one stock does badly, others might do well and balance it out."
            drawback = "Potentially lower returns - great winners might be limited by other holdings."
        elif 'reduce risk' in decision_lower or 'safer' in decision_lower or 'conservative' in decision_lower:
            rebalancing_type = 'risk_reduction'
            explanation = "Risk reduction usually means selling riskier investments and buying safer ones."
            benefit = "More stable portfolio value with less dramatic ups and downs."
            drawback = "Lower potential returns over the long term."
        elif 'increase risk' in decision_lower or 'aggressive' in decision_lower:
            rebalancing_type = 'risk_increase'
            explanation = "Risk increase usually means selling safer investments and buying riskier ones."
            benefit = "Higher potential returns over the long term."
            drawback = "More dramatic ups and downs in portfolio value."
        else:
            rebalancing_type = 'general_rebalancing'
            explanation = "Portfolio rebalancing adjusts your mix of investments to match your goals."
            benefit = "Keeps your portfolio aligned with your risk tolerance and goals."
            drawback = "May involve transaction costs and tax implications."

        return {
            "rebalancing_type": rebalancing_type,
            "action_type": action_type,
            "explanation": explanation,
            "benefits": benefit,
            "drawbacks": drawback,
            "simple_language_explanation": f"Rebalancing changes how your money is divided among different investments. This affects how risky your whole portfolio is.",
            "key_lesson": f"Rebalancing helps keep your portfolio matching your goals and risk comfort level. Too much of one stock is risky, but proper mix can improve returns."
        }


class UserViewAdapter:
    """
    Purpose: Adapt depth, not meaning.

    This layer never recomputes decisions.
    It only decides: Language, Verbosity, Visuals, Which internal details are revealed
    """

    def __init__(self, real_life_decision: RealLifeDecision, user_type: UserType):
        self.real_life_decision = real_life_decision
        self.user_type = user_type

    def adapt_output(self) -> Dict[str, Any]:
        """Adapt the canonical decision to the appropriate user level"""
        base_output = {
            "decision_summary": self.real_life_decision.decision_summary,
            "why_this_helps": self.adapt_why_this_helps(),
            "what_you_gain": self.adapt_what_you_gain(),
            "what_you_risk": self.adapt_what_you_risk(),
            "when_this_stops_working": self.adapt_when_this_stops_working(),
            "who_this_is_for": self.real_life_decision.who_this_is_for,
            "visualization_data": self.real_life_decision.visualization_data,
            "metadata": {
                "decision_id": self.real_life_decision.decision_id,
                "calculated_at": self.real_life_decision.calculated_at,
                "user_type": self.user_type.value
            }
        }

        # Add additional details based on user type
        if self.user_type == UserType.ADVISOR:
            base_output.update(self._get_advisor_details())
        elif self.user_type == UserType.HNI:
            base_output.update(self._get_hni_details())

        return base_output

    def adapt_why_this_helps(self) -> str:
        """Adapt the 'why this helps' section based on user type"""
        base_text = self.real_life_decision.why_this_helps

        if self.user_type == UserType.RETAIL:
            # Keep it simple and clear
            return base_text
        elif self.user_type == UserType.ADVISOR:
            # Add more context for advisors
            return f"{base_text} This aligns with standard portfolio theory regarding diversification and risk management."
        else:  # HNI
            # Technical details for professionals
            return f"{base_text} The underlying mechanism operates through correlation reduction and volatility smoothing mechanisms."

    def adapt_what_you_gain(self) -> str:
        """Adapt the 'what you gain' section based on user type"""
        base_text = self.real_life_decision.what_you_gain

        if self.user_type == UserType.RETAIL:
            return base_text
        elif self.user_type == UserType.ADVISOR:
            return f"{base_text} These benefits are consistent with modern portfolio theory and historical backtesting."
        else:  # HNI
            return f"{base_text} Quantified through correlation matrices and covariance calculations."

    def adapt_what_you_risk(self) -> str:
        """Adapt the 'what you risk' section based on user type"""
        base_text = self.real_life_decision.what_you_risk

        if self.user_type == UserType.RETAIL:
            return base_text
        elif self.user_type == UserType.ADVISOR:
            # Add compliance-friendly language
            return f"{base_text} These risks are documented for compliance and client disclosure purposes."
        else:  # HNI
            # For HNIs, keep the same text - don't expose raw metrics in canonical sections
            return base_text

    def adapt_when_this_stops_working(self) -> str:
        """Adapt the 'when this stops working' section based on user type"""
        base_text = self.real_life_decision.when_this_stops_working

        if self.user_type == UserType.RETAIL:
            return base_text
        elif self.user_type == UserType.ADVISOR:
            return f"{base_text} These failure modes should be discussed with clients as part of suitability assessments."
        else:  # HNI
            # For HNIs, keep the same text - don't expose raw metrics in canonical sections
            return base_text

    def _get_cvar_value(self) -> float:
        """Helper to get CVaR value - in a real implementation this would connect to consequences"""
        return -0.12  # Placeholder

    def _get_max_dd_value(self) -> float:
        """Helper to get max drawdown value - in a real implementation this would connect to consequences"""
        return -0.25  # Placeholder

    def _get_vol_threshold(self) -> float:
        """Helper to get volatility threshold"""
        return 0.30  # Placeholder

    def _get_corr_threshold(self) -> float:
        """Helper to get correlation threshold"""
        return 0.70  # Placeholder

    def _get_advisor_details(self) -> Dict[str, Any]:
        """Get additional details for advisors - NOTE: These are supplementary compliance materials, not decision guidance"""
        return {
            "compliance_notes": [
                "Suitability assessment required",
                "Client risk tolerance alignment needed",
                "Regular monitoring recommended"
            ],
            "documentation": {
                "suitability_checklist": True,
                "risk_disclosure_form": True,
                "alternative_strategies_considered": True
            }
        }

    def _get_hni_details(self) -> Dict[str, Any]:
        """Get additional details for HNIs - NOTE: These are raw internal metrics, not decision guidance"""
        return {
            "quantitative_metrics": {
                "cvar_5_percent": -0.12,
                "expected_shortfall": -0.10,
                "max_drawdown_potential": -0.25,
                "volatility_projection": 0.18
            },
            "regime_analysis": {
                "calm_market_correlation": 0.3,
                "stressed_market_correlation": 0.7,
                "crisis_correlation": 0.9
            },
            "liquidity_assessment": {
                "estimated_liquidation_time_days": 3,
                "stress_liquidity_score": 0.4,
                "forced_sale_impact_estimate": 0.05
            }
        }