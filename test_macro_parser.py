
import os
import sys

# Add the apps/api directory to sys.path
sys.path.append(os.path.join(os.getcwd(), 'apps', 'api'))

from intent_parser import parse_decision
from decision_schema import ScenarioType, Direction
from temporal_engine import run_decision_intelligence

def test_parser():
    test_cases = [
        "What if rates rise 1%?",
        "Simulate an oil crash of 20%",
        "Stress test gdp recession",
        "Buy AAPL 10% after 5 days",
    ]

    print("=== TESTING MACRO PARSER ===")
    for text in test_cases:
        print(f"\nInput: '{text}'")
        decision = parse_decision(text)
        
        print(f"  Decision Type: {decision.decision_type}")
        print(f"  Confidence: {decision.confidence_score}")
        
        if decision.market_shocks:
            print(f"  Shocks: {len(decision.market_shocks)}")
            for shock in decision.market_shocks:
                print(f"    - {shock.shock_type} {shock.target} {shock.magnitude}{shock.unit}")
        
        if decision.actions:
            print(f"  Actions: {len(decision.actions)}")
            for action in decision.actions:
                delay = action.timing.get_execution_offset_days()
                print(f"    - {action.direction} {action.symbol} {action.size_percent}% (Delay: {delay} days)")

def test_simulation():
    print("\n=== TESTING SIMULATION ===")
    
    # Mock Portfolio
    portfolio = {
        "total_value": 100000.0,
        "positions": [
            {"ticker": "AAPL", "weight": 0.4},  # Tech (High rate sensitivity)
            {"ticker": "JPM", "weight": 0.3},   # Financials (Positive rate sensitivity)
            {"ticker": "XOM", "weight": 0.3},   # Energy
        ]
    }
    
    # Case 1: Macro Shock (Rates +1%)
    # Expect: Tech down heavily (-2%), Financials up (+0.5%), Energy down slightly (-0.5%)
    # Net impact approx: 0.4*-2 + 0.3*0.5 + 0.3*-0.5 = -0.8 + 0.15 - 0.15 = -0.8%
    text1 = "What if rates rise 1%?"
    decision1 = parse_decision(text1)
    
    print(f"Running simulation for: '{text1}'")
    comp1, score1, _, _ = run_decision_intelligence(portfolio, decision1, horizon_days=30)
    
    print(f"  Delta Return: {comp1.delta_return:.2f}%")
    print(f"  Delta Drawdown: {comp1.delta_drawdown:.2f}%")
    
    # Verify negative impact
    if comp1.delta_return < -0.2:
        print("  [PASS] Rates hike correctly negatively impacted portfolio (Tech heavy).")
    else:
        print(f"  [FAIL] Rates hike impact expected to be negative < -0.2, got {comp1.delta_return}")

    # Case 2: Delayed Trade
    text2 = "Buy NVDA 10% after 10 days"
    decision2 = parse_decision(text2, portfolio)
    
    print(f"\nRunning simulation for: '{text2}'")
    comp2, score2, base_paths, scen_paths = run_decision_intelligence(portfolio, decision2, horizon_days=30, return_paths=True)
    
    print(f"  Delta Return: {comp2.delta_return:.2f}%")
    print(f"  Verdict: {score2.verdict}")
    print("  [PASS] Delayed trade simulation ran successfully.")

if __name__ == "__main__":
    with open("parser_results.log", "w", encoding="utf-8") as f:
         sys.stdout = f
         test_parser()
         test_simulation()
