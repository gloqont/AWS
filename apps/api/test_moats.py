"""Quick test: verify moat keys in decision_simulate response."""
import json, requests

r = requests.post("http://localhost:8002/api/v1/decision/simulate",
    json={
        "decision_text": "Buy AAPL 3400 inr",
        "mode": "fast",
        "horizon_days": 182,
        "n_paths": 100,
        "return_paths": False,
        "tax_jurisdiction": "IN",
        "tax_holding_period": "short_term",
        "tax_income_tier": "medium",
        "tax_account_type": "taxable",
    },
    cookies={"session": "admin_session"},
)
d = r.json()

out = []
for key in ["moat_time_travel", "moat_tax_harvest", "moat_correlation_risk"]:
    v = d.get(key, {})
    status = "PASS" if v.get("applicable") else "FAIL"
    reason = v.get("reason", v.get("message", "n/a"))
    out.append("[%s] %s: applicable=%s | %s" % (status, key, v.get("applicable"), str(reason)[:80]))

out.append("")
for key in ["moat_time_travel", "moat_tax_harvest", "moat_correlation_risk"]:
    out.append("--- %s ---" % key)
    out.append(json.dumps(d.get(key, {}), indent=2))
    out.append("")

with open("test_moats_output.txt", "w") as f:
    f.write("\n".join(out))
print("Output written to test_moats_output.txt")
