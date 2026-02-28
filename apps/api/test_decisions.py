"""
Direct Intent Parser Test — Tests heuristic parser with 20 decisions.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from intent_parser import IntentParser

parser = IntentParser()

PORTFOLIO = {
    "positions": [
        {"ticker": "TCS", "weight": 0.40},
        {"ticker": "RELIANCE.NS", "weight": 0.30},
        {"ticker": "HDFCBANK.NS", "weight": 0.20},
        {"ticker": "AAPL", "weight": 0.10},
    ],
    "total_value": 381.0,
}

TESTS = [
    ("BASIC-1", "Buy AAPL 10%"),
    ("BASIC-2", "Sell TCS 5%"),
    ("BASIC-3", "Short TSLA 15%"),
    ("BASIC-4", "Buy RELIANCE 20%"),
    ("NORMAL-1", "Buy NVDA $5000"),
    ("NORMAL-2", "Buy TCS 2300 inr"),
    ("NORMAL-3", "Buy RELIANCE 50000 rs"),
    ("NORMAL-4", "Buy MSFT 1000 euros"),
    ("NORMAL-5", "Buy AAPL $100"),
    ("MEDIUM-1", "Sell AAPL 40% and put in MSFT"),
    ("MEDIUM-2", "Reduce tech exposure by 10%"),
    ("HARD-1", "What if interest rates rise 2%?"),
    ("HARD-2", "What if oil crashes 30%?"),
    ("HARD-3", "What if tech drops 20%?"),
    ("HARD-4", "What if GDP falls 5%?"),
    ("ADV-1", "Buy 50 shares NVDA"),
    ("ADV-2", "Buy AAPL $2000 after 3 days"),
    ("ADV-3", "Buy TCS 100000 rupees"),
    ("ADV-4", "Buy GOOGL $100"),
    ("ADV-5", "Sell HDFCBANK.NS 10% after 2 weeks"),
]

print("=" * 72)
print("SCENARIO SIMULATION - HEURISTIC PARSER TEST REPORT")
print("=" * 72)

all_results = []
for label, text in TESTS:
    d = parser._parse_heuristic(text, PORTFOLIO)
    ok = True
    notes = []

    # Check currency conversion for INR/EUR tests
    for a in d.actions:
        if a.size_usd is not None:
            tl = text.lower()
            # Extract the raw number from the text for comparison
            import re
            raw_nums = re.findall(r'(\d+)', text)
            raw_amount = float(raw_nums[-1]) if raw_nums else 0

            if "inr" in tl or " rs" in tl or "rupees" in tl:
                # If size_usd is close to the raw number, it wasn't converted
                if raw_amount > 100 and abs(a.size_usd - raw_amount) < raw_amount * 0.1:
                    ok = False
                    notes.append("CURRENCY BUG: size_usd=%.2f (raw INR not converted)" % a.size_usd)
                else:
                    expected = raw_amount / 83.5
                    notes.append("FX OK: INR %.0f -> USD=%.2f (expected ~%.2f)" % (raw_amount, a.size_usd, expected))
            elif "euros" in tl or "eur" in tl:
                if raw_amount > 100 and abs(a.size_usd - raw_amount) < raw_amount * 0.1:
                    ok = False
                    notes.append("CURRENCY BUG: size_usd=%.2f (raw EUR not converted)" % a.size_usd)
                else:
                    expected = raw_amount / 0.92
                    notes.append("FX OK: EUR %.0f -> USD=%.2f (expected ~%.2f)" % (raw_amount, a.size_usd, expected))

    confidence = d.confidence_score
    status = "PASS" if ok and confidence > 0.5 else "FAIL"
    dtype = d.decision_type.value if hasattr(d.decision_type, 'value') else str(d.decision_type)

    print("")
    print("[%s] %s: \"%s\"" % (status, label, text))
    print("      Confidence: %.2f | Type: %s" % (confidence, dtype))

    for a in d.actions:
        dirn = a.direction.value if hasattr(a.direction, 'value') else str(a.direction)
        usd_s = "$%.2f" % a.size_usd if a.size_usd else "None"
        pct_s = "%.1f%%" % a.size_percent if a.size_percent else "None"
        shr_s = str(a.size_shares) if a.size_shares else "None"
        delay = a.timing.delay_days if a.timing and a.timing.delay_days else 0
        print("      -> %s %s | pct=%s usd=%s shares=%s delay=%dd" % (dirn, a.symbol, pct_s, usd_s, shr_s, delay))

    for s in d.market_shocks:
        stype = s.shock_type.value if hasattr(s.shock_type, 'value') else str(s.shock_type)
        print("      -> SHOCK: %s on %s | magnitude=%+.1f%%" % (stype, s.target, s.magnitude))

    for n in notes:
        print("      ** %s" % n)
    for w in d.warnings:
        print("      ! %s" % w)

    all_results.append((label, status, confidence))

print("")
print("=" * 72)
print("SUMMARY")
print("=" * 72)
passed = sum(1 for _, s, _ in all_results if s == "PASS")
failed = len(all_results) - passed
print("Total: %d | Passed: %d | Failed: %d" % (len(all_results), passed, failed))
print("")
for label, status, conf in all_results:
    icon = "+" if status == "PASS" else "X"
    print("  [%s] %s (conf=%.2f)" % (icon, label, conf))
if failed > 0:
    print("\n  !! %d TEST(S) FAILED" % failed)
else:
    print("\n  ALL %d TESTS PASSED!" % passed)
