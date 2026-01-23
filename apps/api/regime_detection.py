"""
Regime Detection and Classification for GLOQONT Decision Engine

This module implements regime awareness capabilities to detect when market conditions
shift from calm to stressed to crisis states.
"""

from typing import List, Dict, Any
import numpy as np
import pandas as pd
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum


class RegimeState(Enum):
    CALM = "calm"
    STRESSED = "stressed"
    CRISIS = "crisis"


@dataclass
class RegimeMetrics:
    """Current market regime metrics"""
    volatility_regime: RegimeState
    correlation_regime: RegimeState
    liquidity_regime: RegimeState
    momentum_regime: RegimeState
    overall_regime: RegimeState
    confidence: float
    timestamp: str


class RegimeDetector:
    """Detects and classifies market regimes"""
    
    def __init__(self):
        # Thresholds for regime classification
        self.volatility_thresholds = {
            'calm': 0.15,      # 15% annualized vol or below
            'stressed': 0.25,  # 15-25% annualized vol
            'crisis': 0.40     # Above 25% annualized vol
        }
        
        self.correlation_thresholds = {
            'calm': 0.3,       # Average correlation below 0.3
            'stressed': 0.6,   # 0.3-0.6 average correlation
            'crisis': 0.8      # Above 0.6 average correlation
        }
        
        self.liquidity_thresholds = {
            'calm': 0.7,       # High liquidity score (0-1 scale)
            'stressed': 0.4,   # Medium liquidity score
            'crisis': 0.2      # Low liquidity score
        }
        
        self.momentum_thresholds = {
            'calm': 0.1,       # Low momentum persistence
            'stressed': 0.3,   # Moderate momentum
            'crisis': 0.5      # High momentum (trend following)
        }
    
    def detect_regime(self, prices_df: pd.DataFrame, lookback_days: int = 60) -> RegimeMetrics:
        """
        Detect current market regime based on price data
        
        Args:
            prices_df: DataFrame with price data for multiple assets
            lookback_days: Number of days to look back for regime detection
        
        Returns:
            RegimeMetrics object with current regime classification
        """
        # Get recent data
        recent_data = prices_df.tail(lookback_days) if len(prices_df) >= lookback_days else prices_df
        returns_data = recent_data.pct_change().dropna()
        
        if returns_data.empty or returns_data.shape[0] < 10:
            # Not enough data, default to calm
            return RegimeMetrics(
                volatility_regime=RegimeState.CALM,
                correlation_regime=RegimeState.CALM,
                liquidity_regime=RegimeState.CALM,
                momentum_regime=RegimeState.CALM,
                overall_regime=RegimeState.CALM,
                confidence=0.3,  # Low confidence due to limited data
                timestamp=datetime.utcnow().isoformat()
            )
        
        # Calculate regime indicators
        vol_regime = self._classify_volatility_regime(returns_data)
        corr_regime = self._classify_correlation_regime(returns_data)
        liq_regime = self._classify_liquidity_regime(prices_df, returns_data)
        mom_regime = self._classify_momentum_regime(returns_data)
        
        # Overall regime is the most stressed of individual regimes
        overall_regime = self._combine_regimes(vol_regime, corr_regime, liq_regime, mom_regime)
        
        # Calculate confidence based on data availability and consistency
        confidence = self._calculate_confidence(returns_data)
        
        return RegimeMetrics(
            volatility_regime=vol_regime,
            correlation_regime=corr_regime,
            liquidity_regime=liq_regime,
            momentum_regime=mom_regime,
            overall_regime=overall_regime,
            confidence=confidence,
            timestamp=datetime.utcnow().isoformat()
        )
    
    def _classify_volatility_regime(self, returns_data: pd.DataFrame) -> RegimeState:
        """Classify volatility regime based on return volatility"""
        # Calculate annualized volatility
        vol = returns_data.std().mean() * np.sqrt(252)  # Assuming daily data
        
        if vol <= self.volatility_thresholds['calm']:
            return RegimeState.CALM
        elif vol <= self.volatility_thresholds['stressed']:
            return RegimeState.STRESSED
        else:
            return RegimeState.CRISIS
    
    def _classify_correlation_regime(self, returns_data: pd.DataFrame) -> RegimeState:
        """Classify correlation regime based on pairwise correlations"""
        if returns_data.shape[1] < 2:
            # Single asset, default to calm
            return RegimeState.CALM
            
        # Calculate correlation matrix
        corr_matrix = returns_data.corr()
        
        # Get average correlation (excluding diagonal)
        triu_indices = np.triu_indices_from(corr_matrix, k=1)
        avg_corr = np.mean(corr_matrix.values[triu_indices])
        
        if avg_corr <= self.correlation_thresholds['calm']:
            return RegimeState.CALM
        elif avg_corr <= self.correlation_thresholds['stressed']:
            return RegimeState.STRESSED
        else:
            return RegimeState.CRISIS
    
    def _classify_liquidity_regime(self, prices_df: pd.DataFrame, returns_data: pd.DataFrame) -> RegimeState:
        """Classify liquidity regime based on trading characteristics"""
        # Use bid-ask spread proxy: ratio of high-low range to close price
        if len(prices_df) < 2:
            return RegimeState.CALM
            
        # Calculate high-low volatility as liquidity proxy
        if hasattr(prices_df, 'high') and hasattr(prices_df, 'low'):
            # If we have high/low data
            avg_range = ((prices_df['high'] - prices_df['low']) / prices_df['close']).mean()
            # Lower range indicates higher liquidity
            liq_score = 1.0 / (1.0 + avg_range)  # Normalize to 0-1 scale
        else:
            # Use return volatility as inverse liquidity measure
            vol = returns_data.std().mean()
            # Higher volatility often indicates lower liquidity
            liq_score = 1.0 / (1.0 + vol * 10)  # Scale appropriately
        
        if liq_score >= self.liquidity_thresholds['calm']:
            return RegimeState.CALM
        elif liq_score >= self.liquidity_thresholds['stressed']:
            return RegimeState.STRESSED
        else:
            return RegimeState.CRISIS
    
    def _classify_momentum_regime(self, returns_data: pd.DataFrame) -> RegimeState:
        """Classify momentum regime based on trend persistence"""
        if len(returns_data) < 20:
            return RegimeState.CALM
            
        # Calculate autocorrelation of returns (momentum indicator)
        autocorr = []
        for col in returns_data.columns:
            if len(returns_data[col].dropna()) > 10:
                # Calculate 1-lag autocorrelation
                series = returns_data[col].dropna()
                ac = pd.Series(series[:-1]).corr(pd.Series(series[1:]))
                if not np.isnan(ac):
                    autocorr.append(ac)
        
        if not autocorr:
            return RegimeState.CALM
            
        avg_autocorr = np.mean(autocorr)
        
        # Higher autocorrelation indicates stronger momentum
        if abs(avg_autocorr) <= self.momentum_thresholds['calm']:
            return RegimeState.CALM
        elif abs(avg_autocorr) <= self.momentum_thresholds['stressed']:
            return RegimeState.STRESSED
        else:
            return RegimeState.CRISIS
    
    def _combine_regimes(self, vol_reg: RegimeState, corr_reg: RegimeState, 
                         liq_reg: RegimeState, mom_reg: RegimeState) -> RegimeState:
        """Combine individual regimes into overall regime"""
        # Map to numeric values for comparison (higher = more stressed)
        regime_values = {
            RegimeState.CALM: 0,
            RegimeState.STRESSED: 1,
            RegimeState.CRISIS: 2
        }
        
        max_regime_val = max([
            regime_values[vol_reg],
            regime_values[corr_reg], 
            regime_values[liq_reg],
            regime_values[mom_reg]
        ])
        
        # Convert back to regime state
        for regime, val in regime_values.items():
            if val == max_regime_val:
                return regime
        
        return RegimeState.CALM  # Default
    
    def _calculate_confidence(self, returns_data: pd.DataFrame) -> float:
        """Calculate confidence in regime classification"""
        n_obs = len(returns_data)
        n_assets = returns_data.shape[1]
        
        # Confidence increases with more observations and assets
        obs_conf = min(1.0, n_obs / 60.0)  # Full confidence after 60 days
        asset_conf = min(1.0, n_assets / 10.0)  # Full confidence with 10 assets
        
        return (obs_conf + asset_conf) / 2.0
    
    def predict_regime_shift_probability(self, current_regime: RegimeState, 
                                       lookforward_days: int = 30) -> Dict[str, float]:
        """
        Predict probability of shifting to different regimes
        
        Args:
            current_regime: Current market regime
            lookforward_days: Number of days to predict ahead
        
        Returns:
            Dictionary with probabilities for each regime
        """
        # Historical transition probabilities (simplified model)
        transition_probs = {
            RegimeState.CALM: {
                RegimeState.CALM: 0.85,
                RegimeState.STRESSED: 0.14,
                RegimeState.CRISIS: 0.01
            },
            RegimeState.STRESSED: {
                RegimeState.CALM: 0.20,
                RegimeState.STRESSED: 0.70,
                RegimeState.CRISIS: 0.10
            },
            RegimeState.CRISIS: {
                RegimeState.CALM: 0.05,
                RegimeState.STRESSED: 0.30,
                RegimeState.CRISIS: 0.65
            }
        }
        
        return transition_probs.get(current_regime, transition_probs[RegimeState.CALM])


class RegimeAwareAnalyzer:
    """Analyzes portfolio behavior under different market regimes"""
    
    def __init__(self):
        self.detector = RegimeDetector()
    
    def analyze_regime_impact(self, portfolio_data: Dict[str, Any], 
                            prices_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze how portfolio behaves under different market regimes
        
        Args:
            portfolio_data: Portfolio configuration data
            prices_df: Historical price data
            
        Returns:
            Analysis of portfolio behavior across regimes
        """
        # Detect current regime
        current_regime = self.detector.detect_regime(prices_df)
        
        # Simulate portfolio behavior under different regimes
        regime_analysis = {}
        
        for regime in [RegimeState.CALM, RegimeState.STRESSED, RegimeState.CRISIS]:
            regime_analysis[regime.value] = self._simulate_portfolio_under_regime(
                portfolio_data, prices_df, regime
            )
        
        return {
            "current_regime": current_regime,
            "regime_analysis": regime_analysis,
            "transition_probabilities": self.detector.predict_regime_shift_probability(
                current_regime.overall_regime
            )
        }
    
    def _simulate_portfolio_under_regime(self, portfolio_data: Dict[str, Any], 
                                       prices_df: pd.DataFrame, 
                                       regime: RegimeState) -> Dict[str, float]:
        """Simulate portfolio metrics under a specific regime"""
        # This is a simplified simulation - in practice, this would use
        # more sophisticated regime-dependent models
        
        # Get positions and weights
        positions = portfolio_data.get('positions', [])
        weights = np.array([pos.get('weight', 0.0) for pos in positions])
        
        if len(weights) == 0:
            return {"volatility": 0.0, "return": 0.0, "sharpe_ratio": 0.0}
        
        # Adjust returns based on regime characteristics
        base_returns = prices_df.pct_change().dropna()
        
        # Select columns that match portfolio positions
        tickers = [pos.get('ticker') for pos in positions if pos.get('ticker')]
        available_cols = [col for col in tickers if col in base_returns.columns]
        
        if not available_cols:
            return {"volatility": 0.0, "return": 0.0, "sharpe_ratio": 0.0}
        
        selected_returns = base_returns[available_cols]
        
        # Calculate portfolio returns
        portfolio_returns = (selected_returns * weights[:len(available_cols)]).sum(axis=1)
        
        # Adjust for regime-specific characteristics
        regime_multipliers = {
            RegimeState.CALM: {"volatility": 1.0, "return": 1.0},
            RegimeState.STRESSED: {"volatility": 1.8, "return": 0.7},
            RegimeState.CRISIS: {"volatility": 3.0, "return": 0.3}
        }
        
        mult = regime_multipliers[regime]
        
        vol = portfolio_returns.std() * np.sqrt(252) * mult["volatility"]
        ret = portfolio_returns.mean() * 252 * mult["return"]
        sharpe = ret / vol if vol != 0 else 0.0
        
        return {
            "volatility": float(vol),
            "return": float(ret),
            "sharpe_ratio": float(sharpe)
        }


# Global instance for use in decision engine
REGIME_ANALYZER = RegimeAwareAnalyzer()