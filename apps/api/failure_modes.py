"""
Failure Mode Libraries for GLOQONT Decision Engine

This module contains comprehensive libraries of failure modes that can be detected
and analyzed by the DecisionConsequences engine.
"""

from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class HedgeFailureMode:
    """Library of ways hedges can fail"""
    name: str
    description: str
    trigger_conditions: List[str]
    impact_severity: str  # LOW, MEDIUM, HIGH
    probability: float
    mitigation_strategies: List[str]


@dataclass
class DiversificationFailureMode:
    """Library of ways diversification can fail"""
    name: str
    description: str
    trigger_conditions: List[str]
    impact_severity: str
    probability: float
    mitigation_strategies: List[str]


@dataclass
class VolatilityMisestimationMode:
    """Library of ways volatility can be underestimated"""
    name: str
    description: str
    trigger_conditions: List[str]
    impact_severity: str
    probability: float
    mitigation_strategies: List[str]


@dataclass
class LiquidityCompressionMode:
    """Library of liquidity compression scenarios"""
    name: str
    description: str
    trigger_conditions: List[str]
    impact_severity: str
    probability: float
    mitigation_strategies: List[str]


class FailureModeLibrary:
    """Comprehensive library of all failure modes"""
    
    def __init__(self):
        self.hedge_failures = self._build_hedge_failure_library()
        self.diversification_failures = self._build_diversification_failure_library()
        self.volatility_misestimation_modes = self._build_volatility_misestimation_library()
        self.liquidity_compression_modes = self._build_liquidity_compression_library()
    
    def _build_hedge_failure_library(self) -> List[HedgeFailureMode]:
        """Build the hedge failure mode library"""
        return [
            HedgeFailureMode(
                name="Correlation Breakdown",
                description="Hedges fail because correlations increase during stress, making the hedge move in the same direction as the position being hedged",
                trigger_conditions=[
                    "Market stress event occurs",
                    "Volatility spikes above 2-standard deviation levels",
                    "Flight to quality or flight to liquidity occurs"
                ],
                impact_severity="HIGH",
                probability=0.6,
                mitigation_strategies=[
                    "Use multiple uncorrelated hedges",
                    "Monitor correlation stability regularly",
                    "Consider options-based hedges for tail protection",
                    "Test hedge effectiveness under stress scenarios"
                ]
            ),
            HedgeFailureMode(
                name="Basis Risk",
                description="The hedge instrument does not perfectly track the underlying exposure",
                trigger_conditions=[
                    "Different underlying assets or indices",
                    "Time decay in options hedges",
                    "Roll yield in futures hedges"
                ],
                impact_severity="MEDIUM",
                probability=0.4,
                mitigation_strategies=[
                    "Select hedges with high correlation to underlying",
                    "Monitor basis spreads continuously",
                    "Adjust hedge ratios dynamically",
                    "Use swaps or forwards for better matching"
                ]
            ),
            HedgeFailureMode(
                name="Liquidity Mismatch",
                description="The hedge becomes illiquid when needed most, preventing effective hedging",
                trigger_conditions=[
                    "Market liquidity dries up during stress",
                    "Hedge instrument has lower liquidity than underlying",
                    "Counterparty risk emerges"
                ],
                impact_severity="HIGH",
                probability=0.5,
                mitigation_strategies=[
                    "Choose liquid hedge instruments",
                    "Maintain multiple hedge alternatives",
                    "Use exchange-traded instruments when possible",
                    "Monitor bid-ask spreads closely"
                ]
            ),
            HedgeFailureMode(
                name="Timing Risk",
                description="Hedge is put on or removed at the wrong time, reducing effectiveness",
                trigger_conditions=[
                    "Emotional decision-making during volatile periods",
                    "Lack of systematic hedging rules",
                    "Cost concerns leading to delayed hedging"
                ],
                impact_severity="MEDIUM",
                probability=0.7,
                mitigation_strategies=[
                    "Establish systematic hedging rules",
                    "Set predetermined entry/exit triggers",
                    "Avoid emotional timing decisions",
                    "Review hedge effectiveness regularly"
                ]
            )
        ]
    
    def _build_diversification_failure_library(self) -> List[DiversificationFailureMode]:
        """Build the diversification failure mode library"""
        return [
            DiversificationFailureMode(
                name="Correlation Convergence",
                description="Assets that normally have low correlations become highly correlated during stress events",
                trigger_conditions=[
                    "Systemic market stress occurs",
                    "Flight to quality or liquidity",
                    "Common risk factors dominate"
                ],
                impact_severity="HIGH",
                probability=0.8,
                mitigation_strategies=[
                    "Understand fundamental drivers of each position",
                    "Diversify across multiple factors, not just assets",
                    "Stress test portfolio under crisis scenarios",
                    "Monitor correlation matrices regularly"
                ]
            ),
            DiversificationFailureMode(
                name="Concentration Risk",
                description="Portfolio becomes concentrated despite appearing diversified",
                trigger_conditions=[
                    "Hidden correlations between positions",
                    "Sector or factor tilts not recognized",
                    "Geographic or currency concentration"
                ],
                impact_severity="HIGH",
                probability=0.3,
                mitigation_strategies=[
                    "Analyze portfolio at factor level, not just asset level",
                    "Monitor sector, geography, and currency exposures",
                    "Use risk decomposition tools",
                    "Regular portfolio rebalancing"
                ]
            ),
            DiversificationFailureMode(
                name="Illiquidity Trap",
                description="Diversified portfolio becomes difficult to adjust when needed",
                trigger_conditions=[
                    "Multiple illiquid positions simultaneously",
                    "Market stress affecting multiple holdings",
                    "Redemption pressures in fund structures"
                ],
                impact_severity="MEDIUM",
                probability=0.4,
                mitigation_strategies=[
                    "Maintain liquidity buffers",
                    "Understand liquidity profiles of all positions",
                    "Stagger maturity dates when possible",
                    "Keep some liquid alternatives available"
                ]
            ),
            DiversificationFailureMode(
                name="Diversification Drag",
                description="Diversification reduces returns more than it reduces risk",
                trigger_conditions=[
                    "Strong trend in one concentrated area",
                    "Mean reversion not occurring as expected",
                    "Transaction costs eroding benefits"
                ],
                impact_severity="MEDIUM",
                probability=0.5,
                mitigation_strategies=[
                    "Balance diversification with conviction",
                    "Monitor risk-adjusted returns",
                    "Consider tactical allocation adjustments",
                    "Factor in transaction costs"
                ]
            )
        ]
    
    def _build_volatility_misestimation_library(self) -> List[VolatilityMisestimationMode]:
        """Build the volatility misestimation library"""
        return [
            VolatilityMisestimationMode(
                name="Historical Volatility Trap",
                description="Using historical volatility assumes future will resemble past, ignoring regime changes",
                trigger_conditions=[
                    "Regime shift occurs",
                    "Structural market changes",
                    "New market dynamics emerge"
                ],
                impact_severity="HIGH",
                probability=0.7,
                mitigation_strategies=[
                    "Use multiple volatility measures",
                    "Weight recent observations more heavily",
                    "Monitor for structural breaks",
                    "Combine historical with implied volatility"
                ]
            ),
            VolatilityMisestimationMode(
                name="Fat Tail Underestimation",
                description="Normal distribution assumptions underestimate probability of extreme events",
                trigger_conditions=[
                    "Extreme market events occur",
                    "Leverage amplifies movements",
                    "Feedback loops develop"
                ],
                impact_severity="HIGH",
                probability=0.6,
                mitigation_strategies=[
                    "Use fat-tailed distributions",
                    "Stress test for extreme scenarios",
                    "Monitor tail risk measures",
                    "Apply volatility adjustments for extreme events"
                ]
            ),
            VolatilityMisestimationMode(
                name="Calibration Risk",
                description="Volatility models calibrated to calm periods fail during stress",
                trigger_conditions=[
                    "Shift from low to high volatility regime",
                    "Market stress begins",
                    "Uncertainty increases rapidly"
                ],
                impact_severity="HIGH",
                probability=0.5,
                mitigation_strategies=[
                    "Calibrate across multiple market conditions",
                    "Use regime-switching models",
                    "Apply stress adjustments",
                    "Monitor model performance continuously"
                ]
            ),
            VolatilityMisestimationMode(
                name="Time Horizon Mismatch",
                description="Volatility measured at wrong frequency for investment horizon",
                trigger_conditions=[
                    "Investment horizon differs from measurement frequency",
                    "Mean reversion characteristics ignored",
                    "Scaling assumptions are incorrect"
                ],
                impact_severity="MEDIUM",
                probability=0.4,
                mitigation_strategies=[
                    "Match measurement to investment horizon",
                    "Consider mean reversion effects",
                    "Use appropriate scaling methods",
                    "Validate assumptions empirically"
                ]
            )
        ]
    
    def _build_liquidity_compression_library(self) -> List[LiquidityCompressionMode]:
        """Build the liquidity compression library"""
        return [
            LiquidityCompressionMode(
                name="Market Maker Withdrawal",
                description="Market makers reduce quoting activity during stress, reducing liquidity",
                trigger_conditions=[
                    "Market volatility increases sharply",
                    "Capital requirements constrain market makers",
                    "Risk management systems trigger limits"
                ],
                impact_severity="HIGH",
                probability=0.8,
                mitigation_strategies=[
                    "Trade during normal market hours",
                    "Use limit orders to provide liquidity",
                    "Maintain relationships with multiple dealers",
                    "Size trades appropriately"
                ]
            ),
            LiquidityCompressionMode(
                name="Bid-Ask Spread Widening",
                description="Spreads increase dramatically during stress, increasing transaction costs",
                trigger_conditions=[
                    "Market stress intensifies",
                    "Information uncertainty increases",
                    "Trading volume patterns change"
                ],
                impact_severity="HIGH",
                probability=0.9,
                mitigation_strategies=[
                    "Monitor spreads before trading",
                    "Use algorithmic execution",
                    "Time trades to minimize impact",
                    "Consider block trading for large positions"
                ]
            ),
            LiquidityCompressionMode(
                name="Funding Liquidity Crisis",
                description="Ability to finance positions becomes constrained",
                trigger_conditions=[
                    "Credit markets freeze",
                    "Margin requirements increase",
                    "Counterparty risk emerges"
                ],
                impact_severity="HIGH",
                probability=0.6,
                mitigation_strategies=[
                    "Maintain adequate cash buffers",
                    "Diversify funding sources",
                    "Monitor margin requirements",
                    "Avoid excessive leverage"
                ]
            ),
            LiquidityCompressionMode(
                name="Fire Sale Dynamics",
                description="Selling pressure creates negative feedback loop, forcing further selling",
                trigger_conditions=[
                    "Multiple holders need to sell simultaneously",
                    "Stop-losses triggered across market",
                    "Fund redemptions accelerate"
                ],
                impact_severity="HIGH",
                probability=0.4,
                mitigation_strategies=[
                    "Avoid crowded trades",
                    "Maintain liquidity reserves",
                    "Have flexible investment mandates",
                    "Coordinate with other holders when possible"
                ]
            )
        ]
    
    def get_hedge_failures_by_conditions(self, conditions: List[str]) -> List[HedgeFailureMode]:
        """Get hedge failures that match specified conditions"""
        matching_failures = []
        for failure in self.hedge_failures:
            for condition in conditions:
                if any(condition.lower() in trig.lower() for trig in failure.trigger_conditions):
                    if failure not in matching_failures:
                        matching_failures.append(failure)
                    break
        return matching_failures
    
    def get_diversification_failures_by_conditions(self, conditions: List[str]) -> List[DiversificationFailureMode]:
        """Get diversification failures that match specified conditions"""
        matching_failures = []
        for failure in self.diversification_failures:
            for condition in conditions:
                if any(condition.lower() in trig.lower() for trig in failure.trigger_conditions):
                    if failure not in matching_failures:
                        matching_failures.append(failure)
                    break
        return matching_failures
    
    def get_volatility_misestimation_modes_by_conditions(self, conditions: List[str]) -> List[VolatilityMisestimationMode]:
        """Get volatility misestimation modes that match specified conditions"""
        matching_modes = []
        for mode in self.volatility_misestimation_modes:
            for condition in conditions:
                if any(condition.lower() in trig.lower() for trig in mode.trigger_conditions):
                    if mode not in matching_modes:
                        matching_modes.append(mode)
                    break
        return matching_modes
    
    def get_liquidity_compression_modes_by_conditions(self, conditions: List[str]) -> List[LiquidityCompressionMode]:
        """Get liquidity compression modes that match specified conditions"""
        matching_modes = []
        for mode in self.liquidity_compression_modes:
            for condition in conditions:
                if any(condition.lower() in trig.lower() for trig in mode.trigger_conditions):
                    if mode not in matching_modes:
                        matching_modes.append(mode)
                    break
        return matching_modes


# Singleton instance for global access
FAILURE_MODE_LIBRARY = FailureModeLibrary()