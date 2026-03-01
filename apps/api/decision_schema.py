"""
GLOQONT Decision Schema — Structured Decision Objects

This module defines the canonical data structures for decisions parsed from
natural language. LLMs output these structures; deterministic engines consume them.

Core Philosophy:
- LLMs interpret. Deterministic engines decide.
- All structures are serializable, cacheable, and auditable.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class DecisionType(str, Enum):
    """Type of portfolio decision."""
    TRADE = "trade"           # Additive: portfolio + decision (allows >100%)
    REBALANCE = "rebalance"   # Redistributive: normalize to 100%


class Direction(str, Enum):
    """Direction of the trade."""
    BUY = "buy"
    SELL = "sell"
    SHORT = "short"
    COVER = "cover"
    HOLD = "hold"


class TimingType(str, Enum):
    """When to execute the decision."""
    IMMEDIATE = "immediate"   # Execute now (T=0)
    DELAY = "delay"           # Execute after a delay (T+n)
    TRIGGER = "trigger"       # Execute when condition is met
    SCHEDULE = "schedule"     # Execute at specific time


class CapitalSource(str, Enum):
    """Where capital comes from for trades exceeding 100%."""
    CASH = "cash"             # From cash reserves
    MARGIN = "margin"         # Borrowed capital (default)
    LEVERAGE = "leverage"     # Leveraged instrument
    PRO_RATA = "pro_rata"     # Proportional reduction from existing


class ScenarioType(str, Enum):
    """Type of macro-economic scenario."""
    CUSTOM_SHOCK = "custom_shock"
    RATES_CHANGE = "rates_change"
    INFLATION_CHANGE = "inflation_change"
    GDP_GROWTH = "gdp_growth"
    SECTOR_SHOCK = "sector_shock"
    COMMODITY_SHOCK = "commodity_shock"
    VOLATILITY_SHOCK = "volatility_shock"


class MarketShock(BaseModel):
    """A macro-economic shock to apply to the simulation."""
    shock_type: ScenarioType = Field(..., description="Type of shock")
    target: str = Field(..., description="Target variable (e.g. RATES, OIL, TECH)")
    magnitude: float = Field(..., description="Magnitude of shock (e.g. +2.0, -5.0)")
    unit: str = Field(default="percent", description="Unit: percent, bps, sigma")
    description: Optional[str] = Field(default=None, description="Human readable description")


class Timing(BaseModel):
    """Temporal specification for decision execution."""
    type: TimingType = Field(default=TimingType.IMMEDIATE)
    delay_days: Optional[int] = Field(default=None, description="Days to wait before execution")
    delay_hours: Optional[int] = Field(default=None)
    trigger_condition: Optional[str] = Field(default=None, description="Condition string for TRIGGER type")
    
    def get_execution_offset_days(self) -> float:
        """Get the execution offset in days from T=0."""
        if self.type == TimingType.IMMEDIATE:
            return 0.0
        elif self.type == TimingType.DELAY:
            days = self.delay_days or 0
            hours = self.delay_hours or 0
            return days + (hours / 24.0)
        else:
            return 0.0  # For triggers/schedules, we'd need more complex handling


class Constraint(BaseModel):
    """Constraints on decision execution."""
    constraint_type: str = Field(..., description="Type: stop_loss, take_profit, max_allocation, etc.")
    value: float = Field(...)
    unit: str = Field(default="percent", description="percent, usd, shares")


class InstrumentAction(BaseModel):
    """A single action on a single instrument."""
    symbol: str = Field(..., description="Ticker symbol (e.g., AAPL, NVDA)")
    direction: Direction = Field(...)
    size_percent: Optional[float] = Field(default=None, description="Percentage of portfolio/position")
    size_usd: Optional[float] = Field(default=None, description="Absolute dollar amount")
    size_shares: Optional[float] = Field(default=None, description="Absolute number of shares")
    timing: Timing = Field(default_factory=Timing)
    constraints: List[Constraint] = Field(default_factory=list)
    holding_period_days: Optional[int] = Field(default=None, description="Expected holding period")
    
    def get_effective_size_percent(self, portfolio_value: float, current_price: Optional[float] = None) -> float:
        """Get size as percentage, converting from other units if needed."""
        if self.size_percent is not None:
            return self.size_percent
        elif self.size_usd is not None and portfolio_value > 0:
            return (self.size_usd / portfolio_value) * 100.0
        elif self.size_shares is not None and current_price is not None and portfolio_value > 0:
            return ((self.size_shares * current_price) / portfolio_value) * 100.0
        else:
            return 0.0


class StructuredDecision(BaseModel):
    """
    The canonical structured decision object.
    
    This is the output of the NLP/LLM Intent Parser and the input to the
    Decision Graph Compiler.
    """
    decision_id: str = Field(default="", description="Unique decision ID")
    decision_type: DecisionType = Field(default=DecisionType.TRADE)
    actions: List[InstrumentAction] = Field(default_factory=list)
    market_shocks: List[MarketShock] = Field(default_factory=list, description="Macro-economic shocks to apply")
    capital_source: CapitalSource = Field(default=CapitalSource.PRO_RATA)
    
    # Evaluation parameters
    evaluation_horizon_days: int = Field(default=30, description="How far to project outcomes")
    comparison_baseline: str = Field(default="do_nothing", description="What to compare against")
    
    # Original input for audit
    original_text: str = Field(default="")
    parsed_at: Optional[datetime] = Field(default=None)
    
    # Metadata
    confidence_score: float = Field(default=1.0, description="Parser confidence 0-1")
    ambiguity_score: float = Field(default=0.0, description="Ambiguity score 0-1 (inverse of confidence)")
    requires_confirmation: bool = Field(default=False)
    warnings: List[str] = Field(default_factory=list)
    
    def get_all_symbols(self) -> List[str]:
        """Get all unique symbols in this decision."""
        return list(set(action.symbol for action in self.actions))
    
    def get_max_execution_delay(self) -> float:
        """Get the maximum execution delay across all actions."""
        if not self.actions:
            return 0.0
        return max(action.timing.get_execution_offset_days() for action in self.actions)
    
    def is_immediate(self) -> bool:
        """Check if all actions are immediate."""
        return all(action.timing.type == TimingType.IMMEDIATE for action in self.actions)
    
    def has_shorts(self) -> bool:
        """Check if any actions involve shorting."""
        return any(action.direction == Direction.SHORT for action in self.actions)

    def validate(self, portfolio_context: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Critical Safety Gate: Validate decision financial correctness.
        
        Checks:
        - Instrument existence (basic format check)
        - Size sanity (no > 100% unless margin)
        - Portfolio compatibility (selling what you don't own)
        """
        errors = []
        
        # 1. Structural Validation
        if not self.actions and not self.market_shocks:
            errors.append("Decision has no actionable items (actions list and market_shocks are empty).")
            
        # 2. Action-level Validation
        for i, action in enumerate(self.actions):
            # Symbol check
            if not action.symbol or not action.symbol.isupper():
                errors.append(f"Action {i+1}: Invalid symbol format '{action.symbol}'. Expecting uppercase ticker.")
                
            # Size check
            if action.size_percent is not None:
                if action.size_percent <= 0:
                    errors.append(f"Action {i+1}: Negative or zero size percent is invalid.")
                if action.size_percent > 100 and self.capital_source != CapitalSource.MARGIN:
                    # Allow >100% only if margin is explicitly set or inferred
                    # But for now, let's warn/error. 
                    # User design says: "Size sanity (no accidental liquidation)"
                    errors.append(f"Action {i+1}: Size {action.size_percent}% exceeds 100% without explicit margin source.")
            
            # Shorting check
            if action.direction == Direction.SHORT and self.capital_source != CapitalSource.MARGIN:
                self.capital_source = CapitalSource.MARGIN # inferred
                self.warnings.append(f"Action {i+1}: Short selling requires margin account.")

            # Portfolio Compatibility (Selling logic)
            if portfolio_context and (action.direction == Direction.SELL or action.direction == Direction.COVER):
                portfolio_positions = {p.get("ticker", "").upper(): p for p in portfolio_context.get("positions", [])}
                if action.symbol not in portfolio_positions:
                    errors.append(f"Action {i+1}: Cannot SELL/COVER '{action.symbol}' because it is not in the portfolio.")
                else:
                    # Check if selling more than we have
                    pos = portfolio_positions[action.symbol]
                    current_weight = pos.get("weight", 0) * 100.0
                    sell_size = action.size_percent or 100.0 # Default to sell all if unspecified? No, require specs.
                    if action.size_percent and sell_size > current_weight + 0.01: # Epsilon
                        errors.append(f"Action {i+1}: Cannot sell {sell_size}% of '{action.symbol}'. You only hold {current_weight:.2f}%.")

        return errors



class SimulationState(BaseModel):
    """
    A snapshot of the world at time T.
    
    Used by the Temporal Market Simulation Engine.
    """
    timestamp: datetime = Field(...)
    day_offset: float = Field(default=0.0, description="Days from T=0")
    
    # Market state
    prices: Dict[str, float] = Field(default_factory=dict)
    volatilities: Dict[str, float] = Field(default_factory=dict)
    correlations: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    
    # Regime state
    market_regime: str = Field(default="normal", description="normal, stress, crash, rally")
    vix_level: float = Field(default=15.0)
    
    # Portfolio state at this time
    portfolio_weights: Dict[str, float] = Field(default_factory=dict)
    portfolio_value: float = Field(default=0.0)
    cash_balance: float = Field(default=0.0)
    margin_used: float = Field(default=0.0)
    
    # Metrics at this time
    expected_return_pct: float = Field(default=0.0)
    volatility_pct: float = Field(default=0.0)
    var_95_pct: float = Field(default=0.0)
    max_drawdown_pct: float = Field(default=0.0)


class SimulationPath(BaseModel):
    """
    A complete simulation path from T=0 to T=horizon.
    
    Represents one possible future world.
    """
    path_id: str = Field(default="")
    states: List[SimulationState] = Field(default_factory=list)
    probability_weight: float = Field(default=1.0, description="Probability weight for this path")
    
    # Lightweight storage for performance (Vectorized engine output)
    daily_values: List[float] = Field(default_factory=list, description="Daily portfolio values for projections")
    
    # Terminal metrics
    terminal_return_pct: float = Field(default=0.0)
    terminal_volatility_pct: float = Field(default=0.0)
    max_drawdown_pct: float = Field(default=0.0)
    path_integrated_risk: float = Field(default=0.0, description="Time-integrated risk measure")


class DecisionComparison(BaseModel):
    """
    Comparison between baseline (do nothing) and scenario (execute decision).
    
    This is the output of the Counterfactual Comparator.
    """
    decision_id: str = Field(...)
    
    # Baseline metrics (without decision)
    baseline_expected_return: float = Field(default=0.0)
    baseline_volatility: float = Field(default=0.0)
    baseline_var_95: float = Field(default=0.0)
    baseline_max_drawdown: float = Field(default=0.0)
    baseline_tail_loss: float = Field(default=0.0)
    
    # Scenario metrics (with decision)
    scenario_expected_return: float = Field(default=0.0)
    scenario_volatility: float = Field(default=0.0)
    scenario_var_95: float = Field(default=0.0)
    scenario_max_drawdown: float = Field(default=0.0)
    scenario_tail_loss: float = Field(default=0.0)
    
    # Deltas
    delta_return: float = Field(default=0.0)
    delta_volatility: float = Field(default=0.0)
    delta_var_95: float = Field(default=0.0)
    delta_drawdown: float = Field(default=0.0)
    delta_tail_loss: float = Field(default=0.0)
    
    # Risk-adjusted metrics
    sharpe_ratio_baseline: float = Field(default=0.0)
    sharpe_ratio_scenario: float = Field(default=0.0)
    information_ratio: float = Field(default=0.0)


class DecisionVerdict(str, Enum):
    """Final verdict on a decision."""
    STRONGLY_POSITIVE = "strongly_positive"
    MODERATELY_POSITIVE = "moderately_positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    DANGEROUS = "dangerous"


class DecisionScore(BaseModel):
    """
    The final decision dominance score.
    
    Output of the Decision Dominance Engine.
    """
    decision_id: str = Field(...)
    verdict: DecisionVerdict = Field(...)
    
    # Component scores (0-100 scale)
    return_score: float = Field(default=50.0)
    risk_score: float = Field(default=50.0)
    tail_risk_score: float = Field(default=50.0)
    drawdown_score: float = Field(default=50.0)
    capital_efficiency_score: float = Field(default=50.0)
    stability_score: float = Field(default=50.0)
    
    # Composite score
    composite_score: float = Field(default=50.0)
    
    # Human-readable summary
    summary: str = Field(default="")
    key_factors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    
    # Confidence
    confidence: float = Field(default=1.0)



class AssetDelta(BaseModel):
    """Change in specific asset allocation."""
    symbol: str = Field(...)
    weight_before: float = Field(default=0.0)
    weight_after: float = Field(default=0.0)
    weight_delta: float = Field(default=0.0)


class ExecutionContext(BaseModel):
    """
    Portfolio exposure snapshot before and after decision.
    Section 2 of Universal Output Blueprint.
    """
    # Before
    total_value_usd: float = Field(default=0.0)
    gross_exposure_before: float = Field(default=100.0, description="Gross exposure % before decision")
    net_exposure_before: float = Field(default=100.0, description="Net exposure % before decision")
    leverage_before: float = Field(default=1.0)
    margin_usage_before: float = Field(default=0.0, description="Margin % before decision")
    
    # After
    gross_exposure_after: float = Field(default=100.0)
    net_exposure_after: float = Field(default=100.0)
    leverage_after: float = Field(default=1.0)
    margin_usage_after: float = Field(default=0.0)
    
    interpretation: str = Field(default="")
    
    # NEW: Granular Asset Changes
    asset_deltas: List[AssetDelta] = Field(default_factory=list, description="List of individual asset weight changes")


class RiskAnalysis(BaseModel):
    """
    Advanced risk metrics for a decision.
    Sections 6-10 of Universal Output Blueprint.
    """
    # Section 6: Primary Risk Drivers
    primary_risk_drivers: List[str] = Field(default_factory=list)
    
    # Section 7: Time-to-Risk Realization
    time_to_risk_days: float = Field(default=0.0, description="Estimated days for material loss")
    time_to_risk_interpretation: str = Field(default="")
    
    # Section 8: Irreversibility Analysis
    worst_case_permanent_loss_usd: float = Field(default=0.0)
    worst_case_permanent_loss_pct: float = Field(default=0.0)
    recovery_time_months: float = Field(default=0.0)
    irreversibility_interpretation: str = Field(default="")
    
    # Section 9: Regime Sensitivity
    sensitive_regimes: List[str] = Field(default_factory=list)
    
    # Section 10: Exposure Summary
    decision_attributed_downside_usd: float = Field(default=0.0)
    decision_attributed_downside_pct: float = Field(default=0.0)
    decision_attributed_upside_usd: float = Field(default=0.0)
    decision_attributed_upside_pct: float = Field(default=0.0)
    risk_reward_ratio: str = Field(default="1:1")
