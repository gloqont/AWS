"""
Step 1 Verification: Leverage Correction Test

Portfolio: 100% AAPL
Decision: Buy AAPL 5% (additive trade)
Horizon: 1 day, then 30 days

Expected:
- Weights post-decision: AAPL=1.05, leverage_amount=0.05
- margin_cost_daily = 0.05 * (0.04 + 0.015) / 252 ≈ 0.0000109
- delta_return ≈ 0.05 * baseline_return_per_day - margin_cost_daily
- NOT ≈ 5% absolute

Run with: .\\venv_win\\Scripts\\python.exe test_leverage.py
"""
import sys
import numpy as np

# Ensure imports work
from temporal_engine import TemporalSimulationEngine, run_decision_intelligence
from decision_schema import (
    StructuredDecision, InstrumentAction, Direction, DecisionType, Timing
)

def test_leverage():
    # === Setup ===
    portfolio = {
        "id": "test",
        "total_value": 3276.73,
        "positions": [
            {"ticker": "AAPL", "weight": 1.0}
        ]
    }
    
    decision = StructuredDecision(
        decision_id="test_leverage",
        decision_type=DecisionType.TRADE,
        actions=[
            InstrumentAction(
                symbol="AAPL",
                direction=Direction.BUY,
                size_percent=5.0,
                timing=Timing()
            )
        ],
        original_text="Buy AAPL 5%"
    )
    
    engine = TemporalSimulationEngine()
    
    # === Test 1: Weight Vector ===
    weights_before = {"AAPL": 1.0}
    result = engine._execute_decision(decision, weights_before.copy(), 3276.73)
    
    meta = result.pop("__leverage_meta__", None)
    
    print("=" * 60)
    print("TEST 1: Weight Vector After Buy 5%")
    print("=" * 60)
    print(f"  AAPL weight: {result.get('AAPL', 'MISSING')}")
    print(f"  Leverage metadata: {meta}")
    
    assert result["AAPL"] == 1.05, f"Expected AAPL=1.05, got {result['AAPL']}"
    assert meta is not None, "Leverage metadata missing!"
    assert abs(meta["leverage_amount"] - 0.05) < 1e-10, f"Expected leverage=0.05, got {meta['leverage_amount']}"
    assert abs(meta["gross_exposure"] - 1.05) < 1e-10, f"Expected gross=1.05, got {meta['gross_exposure']}"
    
    # Compute expected daily margin cost
    rf = engine.market_params.risk_free_rate  # 0.04
    margin_rate = rf + 0.015  # 0.055
    expected_daily_cost = 0.05 * margin_rate / 252.0
    print(f"  Expected daily margin cost: {expected_daily_cost:.10f}")
    print(f"  Actual daily margin cost:   {meta['margin_cost_daily']:.10f}")
    assert abs(meta["margin_cost_daily"] - expected_daily_cost) < 1e-14
    print("  [OK] Weight vector PASSED\n")
    
    # === Test 2: Monte Carlo 1-Day Horizon ===
    print("=" * 60)
    print("TEST 2: Monte Carlo 1-Day Simulation")
    print("=" * 60)
    
    np.random.seed(42)
    comparison_1d, score_1d, base_paths, scen_paths = run_decision_intelligence(
        portfolio, decision, horizon_days=1, n_paths=5000, return_paths=True
    )
    
    baseline_ret = comparison_1d.baseline_expected_return
    scenario_ret = comparison_1d.scenario_expected_return
    delta_ret = comparison_1d.delta_return
    
    print(f"  Baseline mean return:  {baseline_ret:.6f}%")
    print(f"  Scenario mean return:  {scenario_ret:.6f}%")
    print(f"  Delta return:          {delta_ret:.6f}%")
    
    # Expected delta: ~5% of baseline return minus margin cost
    # For 1 day: baseline_ret is small (e.g., 0.05%)
    # delta should be ≈ 0.05 * baseline_ret - margin_cost_daily * 100
    # margin_cost_daily in pct = expected_daily_cost * 100
    margin_cost_pct = expected_daily_cost * 100
    expected_delta_approx = 0.05 * baseline_ret - margin_cost_pct
    
    print(f"\n  Expected delta (approx): 0.05 × {baseline_ret:.6f}% - {margin_cost_pct:.6f}% = {expected_delta_approx:.6f}%")
    print(f"  Actual delta:            {delta_ret:.6f}%")
    
    # The delta should be SMALL (< 0.5% absolute for 1 day), not 5%
    assert abs(delta_ret) < 0.5, f"FAIL: Delta return {delta_ret:.4f}% is too large! Should be << 1% for 1-day, 5% leverage change."
    print("  [OK] Delta return is proportional, not explosive. PASSED\n")
    
    # === Test 3: 30-Day Horizon ===
    print("=" * 60)
    print("TEST 3: Monte Carlo 30-Day Simulation")
    print("=" * 60)
    
    np.random.seed(42)
    comparison_30d, score_30d, _, _ = run_decision_intelligence(
        portfolio, decision, horizon_days=30, n_paths=5000, return_paths=True
    )
    
    baseline_30 = comparison_30d.baseline_expected_return
    scenario_30 = comparison_30d.scenario_expected_return
    delta_30 = comparison_30d.delta_return
    
    print(f"  Baseline mean return:  {baseline_30:.6f}%")
    print(f"  Scenario mean return:  {scenario_30:.6f}%")
    print(f"  Delta return:          {delta_30:.6f}%")
    
    # 30-day margin cost in pct
    margin_30d_pct = expected_daily_cost * 30 * 100
    expected_delta_30 = 0.05 * baseline_30 - margin_30d_pct
    
    print(f"\n  Expected delta (approx): 0.05 × {baseline_30:.6f}% - {margin_30d_pct:.6f}% = {expected_delta_30:.6f}%")
    print(f"  Actual delta:            {delta_30:.6f}%")
    
    # Should still be small, proportional — not 5% absolute
    assert abs(delta_30) < 2.0, f"FAIL: 30d delta {delta_30:.4f}% too large for 5% leverage bump!"
    print("  [OK] 30-day delta is proportional. PASSED\n")
    
    # === Test 4: No-leverage case (Rebalance) ===
    print("=" * 60)
    print("TEST 4: Rebalance (no leverage) — confirm no margin drag")
    print("=" * 60)
    
    rebal_decision = StructuredDecision(
        decision_id="test_rebal",
        decision_type=DecisionType.REBALANCE,
        actions=[
            InstrumentAction(
                symbol="AAPL",
                direction=Direction.BUY,
                size_percent=5.0,
                timing=Timing()
            )
        ],
        original_text="Rebalance AAPL 5%"
    )
    
    rebal_result = engine._execute_decision(rebal_decision, {"AAPL": 1.0}, 3276.73)
    rebal_meta = rebal_result.pop("__leverage_meta__", None)
    
    total_w = sum(rebal_result.values())
    print(f"  Weights after rebalance: {rebal_result}")
    print(f"  Total weight: {total_w:.4f}")
    print(f"  Leverage amount: {rebal_meta['leverage_amount'] if rebal_meta else 'N/A'}")
    
    # After rebalance normalization, weights should sum to 1.0
    assert abs(total_w - 1.0) < 0.01, f"Rebalance weights don't sum to 1.0: {total_w}"
    print("  [OK] Rebalance normalizes to 1.0, no leverage. PASSED\n")
    
    print("=" * 60)
    print("ALL LEVERAGE TESTS PASSED [OK]")
    print("=" * 60)

if __name__ == "__main__":
    test_leverage()
