import json
import asyncio
from temporal_engine import TemporalSimulationEngine
from decision_schema import StructuredDecision, Direction, DecisionType

def test_engine():
    engine = TemporalSimulationEngine()
    
    portfolio = {
        "total_value": 100000,
        "positions": [
            {"ticker": "NVDA", "weight": 1.0}
        ]
    }
    
    decision = StructuredDecision(
        decision_id="test",
        decision_type=DecisionType.REBALANCE,
        actions=[]
    )
    
    # 147 trading days = 21 weeks approx (user screenshot scenario)
    baseline, scen = engine.simulate(portfolio, decision, horizon_days=147, n_paths=5000)
    
    rets = [p.terminal_return_pct for p in baseline]
    medians = sorted(rets)
    median_ret = medians[len(medians)//2]
    
    with open('temporal_out.json', 'w') as f:
        json.dump({
            "median": median_ret,
            "best": medians[-1],
            "worst": medians[0]
        }, f, indent=2)
    
if __name__ == "__main__":
    test_engine()
