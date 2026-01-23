import sys
import os
from fastapi.testclient import TestClient
import json

# ensure local app package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from main import app, write_portfolios


def make_sample_portfolio():
    return {
        "id": "prt_test",
        "name": "Test Portfolio",
        "risk_budget": "MEDIUM",
        "total_value": 58000.0,
        "base_currency": "USD",
        "positions": [
            {"ticker": "GOOG", "weight": 0.5111},
            {"ticker": "AAPL", "weight": 0.4475},
            {"ticker": "MSFT", "weight": 0.0413},
        ],
        "created_at": "2026-01-01T00:00:00Z",
    }


def test_scenario_run_basic(tmp_path, monkeypatch):
    # ensure data dir is writable and isolated
    data_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data")
    os.makedirs(data_dir, exist_ok=True)
    write_portfolios({"items": [make_sample_portfolio()]})

    client = TestClient(app)
    resp = client.post("/api/v1/scenario/run", json={"decision_text": "Increase AAPL by 10%", "tax_country": "United States"})
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("ok") is True
    assert "distribution" in data
    assert "irreversible_summary" in data
