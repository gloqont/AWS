import httpx
import json
import traceback
import asyncio

async def test():
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            req = {
                "positions": [
                    {"ticker": "NVDA", "weight": 0.5},
                    {"ticker": "AAPL", "weight": 0.5}
                ],
                "risk_budget": "HIGH",
                "lookback_days": 365,
                "interval": "1d",
                "include_paths": True,
                "n_paths": 100
            }
            resp = await client.post("http://127.0.0.1:8002/api/v1/portfolio/analyze", json=req, headers={"Admin-Key": "gloqont-admin-secret-2025"})
            data = resp.json()
            if "analysis" in data:
                print("Annual Vol:", data["analysis"].get("annualized_vol"))
                print("Path Gen Error:", data["analysis"].get("path_generation_error"))
            
            if "simulation_paths" in data:
                print("1y median:", data["simulation_paths"].get("1y", {}).get("median"))
            else:
                print("No simulation paths in response.")
                print(json.dumps(data, indent=2))
    except Exception as e:
        traceback.print_exc()
        
asyncio.run(test())
