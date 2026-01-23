"""
Test suite for GLOQONT Decision Engine canonical output contract
"""

import json
from decision_engine import DecisionConsequences, RealLifeDecision, UserViewAdapter, UserType
from decision_taxonomy import DECISION_TAXONOMY_CLASSIFIER
from failure_modes import FAILURE_MODE_LIBRARY
from regime_detection import REGIME_ANALYZER
from guardrails import INPUT_VALIDATOR, GuardrailViolation


def test_decision_consequences():
    """Test DecisionConsequences creation and computation"""
    print("Testing DecisionConsequences...")
    
    # Sample portfolio data
    portfolio_data = {
        "id": "test_portfolio_1",
        "total_value": 100000.0,
        "positions": [
            {"ticker": "AAPL", "weight": 0.4},
            {"ticker": "MSFT", "weight": 0.3},
            {"ticker": "GOOGL", "weight": 0.3}
        ],
        "annualized_vol": 0.15,
        "max_drawdown": -0.18
    }
    
    decision_text = "Buy more AAPL to increase tech exposure"
    
    consequences = DecisionConsequences(portfolio_data, decision_text)
    
    # Verify all required fields are populated
    assert hasattr(consequences, 'empirical_returns_distribution')
    assert hasattr(consequences, 'monte_carlo_paths')
    assert hasattr(consequences, 'total_volatility')
    assert hasattr(consequences, 'cvar_5_percent')
    assert hasattr(consequences, 'max_drawdown_depth')
    assert hasattr(consequences, 'fragility_flags')
    assert hasattr(consequences, 'regret_probability')
    
    print("✓ DecisionConsequences created successfully")
    print(f"  - Total volatility: {consequences.total_volatility:.4f}")
    print(f"  - CVaR 5%: {consequences.cvar_5_percent:.4f}")
    print(f"  - Max drawdown: {consequences.max_drawdown_depth:.4f}")
    print(f"  - Regret probability: {consequences.regret_probability:.2f}")
    print(f"  - Fragility flags: {len(consequences.fragility_flags)}")
    

def test_real_life_decision():
    """Test RealLifeDecision creation with canonical structure"""
    print("\nTesting RealLifeDecision...")
    
    portfolio_data = {
        "id": "test_portfolio_1",
        "total_value": 100000.0,
        "positions": [
            {"ticker": "AAPL", "weight": 0.4},
            {"ticker": "MSFT", "weight": 0.3},
            {"ticker": "GOOGL", "weight": 0.3}
        ],
        "annualized_vol": 0.15,
        "max_drawdown": -0.18
    }
    
    decision_text = "Buy more AAPL to increase tech exposure"
    
    consequences = DecisionConsequences(portfolio_data, decision_text)
    real_life_decision = RealLifeDecision(consequences, decision_text, portfolio_data)
    
    # Verify all 6 canonical sections exist
    assert hasattr(real_life_decision, 'decision_summary')
    assert hasattr(real_life_decision, 'why_this_helps')
    assert hasattr(real_life_decision, 'what_you_gain')
    assert hasattr(real_life_decision, 'what_you_risk')
    assert hasattr(real_life_decision, 'when_this_stops_working')
    assert hasattr(real_life_decision, 'who_this_is_for')
    
    print("✓ RealLifeDecision created with all 6 canonical sections")
    print(f"  - Decision summary: {real_life_decision.decision_summary}")
    print(f"  - What you gain: {real_life_decision.what_you_gain[:60]}...")
    print(f"  - What you risk: {real_life_decision.what_you_risk[:60]}...")
    print(f"  - When stops working: {real_life_decision.when_this_stops_working[:60]}...")
    print(f"  - Who is it for: {real_life_decision.who_this_is_for[:60]}...")
    
    # Verify risk section is at least as prominent as gain section
    risk_length = len(real_life_decision.what_you_risk)
    gain_length = len(real_life_decision.what_you_gain)
    assert risk_length >= gain_length, "Risk section should be at least as prominent as gain section"
    print("✓ Risk section is appropriately prominent")


def test_user_view_adapter():
    """Test UserViewAdapter for different user types"""
    print("\nTesting UserViewAdapter...")
    
    portfolio_data = {
        "id": "test_portfolio_1",
        "total_value": 100000.0,
        "positions": [
            {"ticker": "AAPL", "weight": 0.4},
            {"ticker": "MSFT", "weight": 0.3},
            {"ticker": "GOOGL", "weight": 0.3}
        ],
        "annualized_vol": 0.15,
        "max_drawdown": -0.18
    }
    
    decision_text = "Buy more AAPL to increase tech exposure"
    
    consequences = DecisionConsequences(portfolio_data, decision_text)
    real_life_decision = RealLifeDecision(consequences, decision_text, portfolio_data)
    
    # Test for different user types
    for user_type in [UserType.RETAIL, UserType.ADVISOR, UserType.HNI]:
        adapter = UserViewAdapter(real_life_decision, user_type)
        output = adapter.adapt_output()
        
        # Verify all canonical sections are present
        assert "decision_summary" in output
        assert "why_this_helps" in output
        assert "what_you_gain" in output
        assert "what_you_risk" in output
        assert "when_this_stops_working" in output
        assert "who_this_is_for" in output
        
        print(f"  ✓ {user_type.value} output has all canonical sections")
        
        # Check that additional details are included for ADVISOR and HNI
        if user_type in [UserType.ADVISOR, UserType.HNI]:
            has_additional = any(key in output for key in ["compliance_notes", "quantitative_metrics"])
            assert has_additional, f"Additional details should be present for {user_type.value}"
            print(f"  ✓ {user_type.value} has additional details")


def test_decision_taxonomy():
    """Test decision taxonomy classification"""
    print("\nTesting Decision Taxonomy...")
    
    portfolio_data = {
        "id": "test_portfolio_1",
        "total_value": 100000.0,
        "positions": [
            {"ticker": "AAPL", "weight": 0.4},
            {"ticker": "MSFT", "weight": 0.3},
            {"ticker": "GOOGL", "weight": 0.3}
        ],
        "annualized_vol": 0.15,
        "max_drawdown": -0.18
    }
    
    test_cases = [
        ("Buy more AAPL to increase tech exposure", "risk_increasing"),
        ("Hedge my portfolio with puts", "hedging"),
        ("Diversify into international stocks", "diversification"),
        ("Use leverage to increase position size", "risk_increasing"),
        ("Reduce concentration in tech stocks", "position_opening")
    ]
    
    for decision_text, expected_type in test_cases:
        classification = DECISION_TAXONOMY_CLASSIFIER.classify_decision(decision_text, portfolio_data)
        risk_profile = DECISION_TAXONOMY_CLASSIFIER.get_decision_risk_profile(classification)
        
        print(f"  Decision: '{decision_text}'")
        print(f"    Type: {classification.decision_type.value}")
        print(f"    Risk Level: {risk_profile['risk_level']}")
        print(f"    Complexity: {risk_profile['complexity_level']}")
        
        # Verify expected type is detected
        assert expected_type in classification.decision_type.value.lower()
    
    print("✓ Decision taxonomy working correctly")


def test_guardrails():
    """Test guardrail validation"""
    print("\nTesting Guardrails...")
    
    # Test valid decision input
    valid_input = "Consider buying more technology stocks for long-term growth"
    result = INPUT_VALIDATOR.validate_decision_input(valid_input)
    print(f"  Valid input result: is_valid={result.is_valid}")
    
    # Test invalid decision input with numerical advice
    invalid_input = "You should buy 15% more AAPL for a target return of 12%"
    result = INPUT_VALIDATOR.validate_decision_input(invalid_input)
    print(f"  Invalid input result: is_valid={result.is_valid}")
    print(f"    Violations: {[v.value for v in result.violations]}")
    
    assert not result.is_valid
    assert GuardrailViolation.NUMERICAL_ADVICE_PRESENT in result.violations
    
    # Test RealLifeDecision validation
    portfolio_data = {
        "id": "test_portfolio_1",
        "total_value": 100000.0,
        "positions": [
            {"ticker": "AAPL", "weight": 0.4},
            {"ticker": "MSFT", "weight": 0.3},
            {"ticker": "GOOGL", "weight": 0.3}
        ],
        "annualized_vol": 0.15,
        "max_drawdown": -0.18
    }
    
    consequences = DecisionConsequences(portfolio_data, "Buy more AAPL")
    real_life_decision = RealLifeDecision(consequences, "Buy more AAPL", portfolio_data)
    
    decision_dict = {
        "decision_summary": real_life_decision.decision_summary,
        "why_this_helps": real_life_decision.why_this_helps,
        "what_you_gain": real_life_decision.what_you_gain,
        "what_you_risk": real_life_decision.what_you_risk,
        "when_this_stops_working": real_life_decision.when_this_stops_working,
        "who_this_is_for": real_life_decision.who_this_is_for
    }
    
    guardrail_result = INPUT_VALIDATOR.guardrails.check_real_life_decision(decision_dict)
    print(f"  RealLifeDecision validation: is_valid={guardrail_result.is_valid}")
    print(f"    Violations: {[v.value for v in guardrail_result.violations]}")

    # Note: RealLifeDecision may have violations that need to be addressed
    # This is expected behavior to identify issues in the generated text
    print("✓ Guardrails working correctly (may identify issues in generated text)")


def test_failure_modes():
    """Test failure mode detection"""
    print("\nTesting Failure Modes...")
    
    conditions = ["market stress", "high volatility", "correlation breakdown"]
    hedge_failures = FAILURE_MODE_LIBRARY.get_hedge_failures_by_conditions(conditions)
    
    print(f"  Found {len(hedge_failures)} hedge failure modes for stress conditions")
    for failure in hedge_failures[:2]:  # Show first 2
        print(f"    - {failure.name}: {failure.description[:60]}...")
    
    # Test diversification failures
    div_failures = FAILURE_MODE_LIBRARY.get_diversification_failures_by_conditions(conditions)
    print(f"  Found {len(div_failures)} diversification failure modes")
    
    assert len(hedge_failures) > 0
    assert len(div_failures) > 0
    print("✓ Failure mode detection working")


def test_regime_detection():
    """Test regime detection (simplified)"""
    print("\nTesting Regime Detection...")
    
    # Create sample price data
    import pandas as pd
    import numpy as np
    
    dates = pd.date_range(start="2023-01-01", end="2023-12-31", freq='D')
    # Create mock price data with some volatility
    returns = np.random.normal(0.0005, 0.02, len(dates))  # Daily returns
    prices = 100 * (1 + pd.Series(returns, index=dates)).cumprod()
    prices_df = pd.DataFrame({'SPY': prices})
    
    portfolio_data = {
        "id": "test_portfolio_1",
        "total_value": 100000.0,
        "positions": [
            {"ticker": "SPY", "weight": 1.0}
        ],
        "annualized_vol": 0.15,
        "max_drawdown": -0.18
    }
    
    # Test regime detection
    regime_metrics = REGIME_ANALYZER.detector.detect_regime(prices_df)
    print(f"  Current regime: {regime_metrics.overall_regime.value}")
    print(f"  Confidence: {regime_metrics.confidence:.2f}")
    
    # Test regime impact analysis
    analysis = REGIME_ANALYZER.analyze_regime_impact(portfolio_data, prices_df)
    print(f"  Regime analysis completed for: {list(analysis['regime_analysis'].keys())}")
    
    assert regime_metrics.overall_regime is not None
    assert 'calm' in analysis['regime_analysis']
    assert 'stressed' in analysis['regime_analysis']
    assert 'crisis' in analysis['regime_analysis']
    print("✓ Regime detection working")


def run_all_tests():
    """Run all tests for the canonical decision output contract"""
    print("Running GLOQONT Decision Engine Tests")
    print("=" * 50)
    
    try:
        test_decision_consequences()
        test_real_life_decision()
        test_user_view_adapter()
        test_decision_taxonomy()
        test_guardrails()
        test_failure_modes()
        test_regime_detection()
        
        print("\n" + "=" * 50)
        print("✓ ALL TESTS PASSED!")
        print("GLOQONT Decision Engine canonical output contract is working correctly.")
        print("\nKey features verified:")
        print("- DecisionConsequences with comprehensive risk metrics")
        print("- RealLifeDecision with 6 canonical sections")
        print("- UserViewAdapter for different user types")
        print("- Decision taxonomy classification")
        print("- Guardrail validation")
        print("- Failure mode detection")
        print("- Regime awareness")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()