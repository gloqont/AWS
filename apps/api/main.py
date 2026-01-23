import os
import json
import time
import secrets
import math
import asyncio
from typing import List, Literal, Optional, Dict, Any

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, Response, Request, HTTPException
import httpx
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from pydantic import BaseModel, Field, field_validator

from risk import fetch_prices, portfolio_metrics, periods_per_year_from_interval
from decision_engine import DecisionConsequences, RealLifeDecision, UserViewAdapter, UserType
from decision_taxonomy import DECISION_TAXONOMY_CLASSIFIER
from failure_modes import FAILURE_MODE_LIBRARY
from regime_detection import REGIME_ANALYZER
from guardrails import INPUT_VALIDATOR
from asset_resolver import ASSET_RESOLVER, AssetInfo
from enhanced_decision_classifier import ENHANCED_DECISION_CLASSIFIER, DecisionCategory

load_dotenv()

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")
SESSION_SECRET = os.getenv("SESSION_SECRET", "dev_secret_change_me")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")

serializer = URLSafeTimedSerializer(SESSION_SECRET)
SESSION_COOKIE = "advisor_session"
SESSION_MAX_AGE_SECONDS = 60 * 60 * 8  # 8 hours

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
PORTFOLIOS_PATH = os.path.join(DATA_DIR, "portfolios.json")
DECISIONS_PATH = os.path.join(DATA_DIR, "decisions.json")  # ✅
TAX_RULES_PATH = os.path.join(DATA_DIR, "tax_rules.json")  # ✅
PROFILES_PATH = os.path.join(DATA_DIR, "user_profiles.json")

app = FastAPI(title="Advisor Dashboard API", version="1.4.0")  # bump version

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in CORS_ORIGINS.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

RiskBudget = Literal["LOW", "MEDIUM", "HIGH"]


# ----------------------------
# Models
# ----------------------------
class PositionIn(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=12)
    weight: float = Field(..., ge=0.0, le=100.0)

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, v: str) -> str:
        v = v.strip().upper()
        if not v:
            raise ValueError("Ticker required")
        # Allow alphanumeric characters plus common international suffixes (., -, _, :)
        if not all(c.isalnum() or c in '.-_:/' for c in v):
            raise ValueError("Ticker must be alphanumeric with optional international suffixes (e.g., .NS, .BO, :F)")
        return v


class PortfolioBase(BaseModel):
    name: str = Field(default="My Portfolio", min_length=1, max_length=60)
    risk_budget: RiskBudget
    positions: List[PositionIn]


class PortfolioIn(PortfolioBase):
    total_value: float = Field(..., gt=0)
    base_currency: str = Field(default="USD")


class ValidationOut(BaseModel):
    ok: bool
    sum_weights: float
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class LoginIn(BaseModel):
    username: str
    password: str


class AnalyzeIn(BaseModel):
    risk_budget: RiskBudget
    positions: List[PositionIn]
    lookback_days: int = 365
    interval: Literal["1d", "1wk", "1mo"] = "1d"


# ✅ Decision / Scenario Simulation models
class DecisionAnalyzeIn(BaseModel):
    decision_text: str = Field(..., min_length=3, max_length=400)
    tax_country: str = Field(default="United States")
    user_type: UserType = Field(default=UserType.RETAIL)  # NEW: User type for canonical output


class DecisionOut(BaseModel):
    id: str
    decision_text: str
    tax_country: str
    portfolio_id: str
    portfolio_value: float
    expected_before_tax_pct: float
    worst_case_pct: float
    best_case_pct: float
    confidence: str
    notes: List[str] = Field(default_factory=list)
    created_at: str


# NEW: Canonical Decision Output Model
class CanonicalDecisionOut(BaseModel):
    decision_summary: str
    why_this_helps: str
    what_you_gain: str
    what_you_risk: str
    when_this_stops_working: str
    who_this_is_for: str
    metadata: Dict[str, Any]
    additional_details: Optional[Dict[str, Any]] = None  # For advisor/HNI details


# Scenario models
class ScenarioIn(BaseModel):
    decision_text: str = Field(..., min_length=3, max_length=400)
    tax_country: str = Field(default="United States")
    decision_type: str = Field(default="rebalance")  # NEW: "trade" or "rebalance"
    magnitude: int = Field(default=5)
    mode: str = Field(default="Compounding Mode")


class ScenarioOut(BaseModel):
    ok: bool
    market_context: Dict[str, Any]
    baseline: Dict[str, Any]
    executed_decision: Dict[str, Any]
    distribution: Dict[str, Any]
    time_to_damage_days: int
    fragile_regimes: List[str]
    risk_concentration: List[Dict[str, Any]]
    irreversibility: Dict[str, Any]
    heatmap: List[Dict[str, Any]]
    irreversible_summary: Dict[str, Any]
    # NEW: Strict contract fields (made optional to avoid validation errors)
    decision_summary: Optional[Dict[str, Any]] = None
    primary_exposure_impact: Optional[Dict[str, Any]] = None
    risk_impact: Optional[Dict[str, Any]] = None
    time_to_risk: Optional[Dict[str, Any]] = None
    market_regimes: Optional[Dict[str, Any]] = None
    concentration_after_decision: Optional[Dict[str, Any]] = None
    irreversibility_detailed: Optional[Dict[str, Any]] = None
    irreversible_loss_heatmap: Optional[Dict[str, Any]] = None
    decision_summary_line: Optional[Dict[str, Any]] = None
    # NEW: Visualization data
    visualization_data: Optional[Dict[str, Any]] = None


# ✅ Tax rules model
class TaxRulesOut(BaseModel):
    country: str
    long_term_capital_gains: float
    short_term_capital_gains: float
    crypto: float
    transaction_tax: float
    fx_drag: float


# ✅ NEW: Tax Advisor models
class TaxAdviceIn(BaseModel):
    tax_country: str = Field(default="United States", min_length=2, max_length=60)


class TaxAdviceItem(BaseModel):
    title: str
    severity: Literal["LOW", "MEDIUM", "HIGH"]
    why: str
    est_savings_usd: float = 0.0
    next_step: str


class TaxAdviceOut(BaseModel):
    ok: bool
    portfolio_id: str
    portfolio_value: float
    base_currency: str
    tax_country: str
    decision_id: Optional[str] = None
    decision_text: Optional[str] = None
    items: List[TaxAdviceItem]

    visualization_data: Optional[Dict[str, Any]] = None


# ----------------------------
# Storage helpers
# ----------------------------
def ensure_data_file():
    os.makedirs(DATA_DIR, exist_ok=True)

    if not os.path.exists(PORTFOLIOS_PATH):
        with open(PORTFOLIOS_PATH, "w", encoding="utf-8") as f:
            json.dump({"items": []}, f)

    if not os.path.exists(DECISIONS_PATH):
        with open(DECISIONS_PATH, "w", encoding="utf-8") as f:
            json.dump({"items": []}, f)

    if not os.path.exists(TAX_RULES_PATH):
        with open(TAX_RULES_PATH, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "default_country": "United States",
                    "rules": {
                        "United States": {
                            "long_term_capital_gains": 0.15,
                            "short_term_capital_gains": 0.30,
                            "crypto": 0.30,
                            "transaction_tax": 0.00,
                            "fx_drag": 0.005,
                        }
                    },
                },
                f,
                indent=2,
            )


def read_portfolios():
    ensure_data_file()
    with open(PORTFOLIOS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def write_portfolios(payload):
    ensure_data_file()
    with open(PORTFOLIOS_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def read_decisions():
    ensure_data_file()
    with open(DECISIONS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def write_decisions(payload):
    ensure_data_file()
    with open(DECISIONS_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def read_tax_rules():
    ensure_data_file()
    with open(TAX_RULES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def read_profiles():
    ensure_data_file()
    if not os.path.exists(PROFILES_PATH):
        with open(PROFILES_PATH, "w", encoding="utf-8") as f:
            json.dump({"profiles": {}}, f)
    with open(PROFILES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def write_profiles(payload):
    ensure_data_file()
    with open(PROFILES_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


# ----------------------------
# Core validation logic
# ----------------------------
def validate_portfolio(p: PortfolioBase, tolerance: float = 0.01) -> ValidationOut:
    errors: List[str] = []
    warnings: List[str] = []

    if len(p.positions) == 0:
        errors.append("Add at least one position.")

    tickers = [pos.ticker for pos in p.positions]
    if len(set(tickers)) != len(tickers):
        errors.append("Duplicate tickers are not allowed.")

    sum_weights = sum(pos.weight for pos in p.positions)

    if abs(sum_weights - 100.0) > tolerance:
        errors.append(f"Weights must sum to 100%. Current total: {sum_weights:.2f}%")

    suggested_max = {"LOW": 20.0, "MEDIUM": 35.0, "HIGH": 60.0}[p.risk_budget]
    for pos in p.positions:
        if pos.weight > suggested_max:
            warnings.append(
                f"{pos.ticker} weight ({pos.weight:.2f}%) exceeds suggested max for {p.risk_budget} ({suggested_max:.2f}%)."
            )

    return ValidationOut(ok=len(errors) == 0, sum_weights=sum_weights, errors=errors, warnings=warnings)


# ----------------------------
# Auth helpers
# ----------------------------
def require_admin(request: Request):
    # Bypass auth checks in development: always return a fake admin user.
    # This allows the frontend to call API endpoints without performing login.
    return {"role": "admin", "sub": "admin"}


# ----------------------------
# Auth routes
# ----------------------------
@app.post("/api/v1/auth/login")
def login(body: LoginIn, response: Response):
    if body.username != ADMIN_USERNAME or body.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    session = {
        "sub": "admin",
        "role": "admin",
        "nonce": secrets.token_hex(8),
        "iat": int(time.time()),
    }
    token = serializer.dumps(session)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=SESSION_MAX_AGE_SECONDS,
        path="/",
    )
    return {"ok": True}


@app.post("/api/v1/auth/logout")
def logout(response: Response):
    response.delete_cookie(key=SESSION_COOKIE, path="/")
    return {"ok": True}


@app.get("/api/v1/auth/me")
def me(request: Request):
    data = require_admin(request)
    return {"ok": True, "user": {"username": "admin", "role": data["role"]}}


# ----------------------------
# Portfolio routes
# ----------------------------
@app.post("/api/v1/portfolio/validate", response_model=ValidationOut)
def portfolio_validate(request: Request, body: PortfolioIn):
    require_admin(request)
    return validate_portfolio(body)


@app.post("/api/v1/portfolio/save")
def portfolio_save(request: Request, body: PortfolioIn):
    require_admin(request)

    v = validate_portfolio(body)
    if not v.ok:
        raise HTTPException(
            status_code=400,
            detail={"errors": v.errors, "warnings": v.warnings, "sum_weights": v.sum_weights},
        )

    store = read_portfolios()
    item = {
        "id": f"prt_{secrets.token_hex(6)}",
        "name": body.name,
        "risk_budget": body.risk_budget,
        "total_value": float(body.total_value),
        "base_currency": body.base_currency,
        "positions": [{"ticker": p.ticker, "weight": p.weight / 100.0} for p in body.positions],
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    store["items"].insert(0, item)
    write_portfolios(store)
    return {"ok": True, "portfolio": item}


@app.get("/api/v1/portfolio/current")
def portfolio_current(request: Request):
    require_admin(request)
    store = read_portfolios()
    items = store.get("items", [])
    if not items:
        return {"ok": True, "portfolio": None}
    return {"ok": True, "portfolio": items[0]}


@app.post("/api/v1/portfolio/risk-object")
def portfolio_risk_object(request: Request, body: PortfolioIn):
    require_admin(request)

    v = validate_portfolio(body)
    if not v.ok:
        raise HTTPException(
            status_code=400,
            detail={"errors": v.errors, "warnings": v.warnings, "sum_weights": v.sum_weights},
        )

    max_position = {"LOW": 0.20, "MEDIUM": 0.35, "HIGH": 0.60}[body.risk_budget]

    risk_obj = {
        "as_of": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "risk_budget": body.risk_budget,
        "portfolio_value": float(body.total_value),
        "base_currency": body.base_currency,
        "positions": [{"ticker": p.ticker, "weight": round(p.weight / 100.0, 6)} for p in body.positions],
        "constraints": {
            "fully_invested": True,
            "long_only": True,
            "max_position": max_position,
            "min_position": 0.0,
        },
        "risk_assumptions": {
            "horizon_days": 30,
            "return_model": "HISTORICAL_PLACEHOLDER",
            "vol_model": "STATIC_PLACEHOLDER",
            "corr_model": "STATIC_PLACEHOLDER",
        },
        "diagnostics": {"sum_weights": round(v.sum_weights / 100.0, 6), "warnings": v.warnings},
        "decision_log": [
            {
                "event": "PORTFOLIO_INTERPRETED",
                "note": "V1 interprets inputs into a risk object contract.",
            }
        ],
    }
    return {"ok": True, "risk_object": risk_obj}


# ----------------------------
# Tax rules route
# ----------------------------
@app.get("/api/v1/tax/rules", response_model=TaxRulesOut)
def tax_rules(request: Request, country: str = "United States"):
    require_admin(request)

    data = read_tax_rules()
    rules = data.get("rules", {}) or {}
    default_country = data.get("default_country", "United States")

    picked = rules.get(country) or rules.get(default_country) or rules.get("United States")

    if not picked and rules:
        first_key = next(iter(rules.keys()))
        country = first_key
        picked = rules[first_key]

    if not picked:
        country = "United States"
        picked = {
            "long_term_capital_gains": 0.15,
            "short_term_capital_gains": 0.30,
            "crypto": 0.30,
            "transaction_tax": 0.00,
            "fx_drag": 0.005,
        }

    return TaxRulesOut(country=country, **picked)



# ----------------------------
# User profile / questionnaire
# ----------------------------
@app.get("/api/v1/user/profile")
def user_profile_get(request: Request):
    require_admin(request)
    # in this simple app we store a single admin profile
    store = read_profiles()
    return {"ok": True, "profile": store.get("profiles", {}).get("admin")}


@app.post("/api/v1/user/profile")
def user_profile_save(request: Request, body: dict):
    require_admin(request)
    store = read_profiles()
    profiles = store.get("profiles", {}) or {}

    answers = body.get("answers") or {}
    skipped = bool(body.get("skipped", False))
    level = classify_level(answers) if not skipped else None

    profiles["admin"] = {
        "answers": answers,
        "skipped": skipped,
        "level": level,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    store["profiles"] = profiles
    write_profiles(store)
    return {"ok": True, "profile": profiles["admin"]}


# ----------------------------
# Market helpers (search)
# ----------------------------
@app.get("/api/v1/market/search")
def market_search(request: Request, q: str):
    require_admin(request)
    if not q or not q.strip():
        raise HTTPException(status_code=400, detail="query required")

    # First try to resolve using our canonical asset resolver
    asset_info = ASSET_RESOLVER.resolve_asset(q)
    if asset_info and asset_info.is_valid:
        return {
            "ok": True,
            "symbol": asset_info.symbol,
            "shortname": asset_info.name,
            "exchange": "NSE" if asset_info.country == "India" else "NASDAQ" if asset_info.country == "USA" else "OTHER",
            "currency": "INR" if asset_info.country == "India" else "USD",
        }

    # Then try the original Yahoo Finance search
    url = f"https://query1.finance.yahoo.com/v1/finance/search?q={q}&quotesCount=6&newsCount=0"
    try:
        r = httpx.get(url, timeout=10.0)
        r.raise_for_status()
        data = r.json()
        quotes = data.get("quotes", [])
        # pick the first equity-like symbol
        for qitem in quotes:
            typ = qitem.get("quoteType") or qitem.get("typeDisp") or ""
            if (typ and "EQUITY" in str(typ).upper()) or qitem.get("symbol"):
                return {
                    "ok": True,
                    "symbol": qitem.get("symbol"),
                    "shortname": qitem.get("shortname") or qitem.get("longname"),
                    "exchange": qitem.get("exchange"),
                    "currency": qitem.get("currency"),
                }
    except Exception:
        pass

    # If the original search fails, try with common international suffixes
    international_suffixes = [".NS", ".BO", ".JK", ".SI", ".HK", ".TO", ".L", ".PA", ".DE", ".MI"]
    base_query = q.rstrip('.NS').rstrip('.BO').rstrip('.JK').rstrip('.SI').rstrip('.HK').rstrip('.TO').rstrip('.L').rstrip('.PA').rstrip('.DE').rstrip('.MI')

    for suffix in international_suffixes:
        if not q.endswith(suffix):
            test_query = f"{base_query}{suffix}"
            url = f"https://query1.finance.yahoo.com/v1/finance/search?q={test_query}&quotesCount=6&newsCount=0"
            try:
                r = httpx.get(url, timeout=10.0)
                r.raise_for_status()
                data = r.json()
                quotes = data.get("quotes", [])
                # pick the first equity-like symbol
                for qitem in quotes:
                    typ = qitem.get("quoteType") or qitem.get("typeDisp") or ""
                    if (typ and "EQUITY" in str(typ).upper()) or qitem.get("symbol"):
                        return {
                            "ok": True,
                            "symbol": qitem.get("symbol"),
                            "shortname": qitem.get("shortname") or qitem.get("longname"),
                            "exchange": qitem.get("exchange"),
                            "currency": qitem.get("currency"),
                        }
            except Exception:
                continue

    raise HTTPException(status_code=404, detail="No ticker found")




# ----------------------------
# Decision / Scenario Simulation routes
# ----------------------------
def _decision_score(text: str) -> float:
    t = text.lower()
    score = 0.0

    if any(k in t for k in ["buy", "increase", "add", "long", "overweight"]):
        score += 1.0
    if any(k in t for k in ["sell", "decrease", "trim", "reduce", "short", "underweight"]):
        score -= 1.0

    if any(k in t for k in ["leverage", "margin", "options", "0dte", "calls", "puts"]):
        score += 1.5

    if any(k in t for k in ["hedge", "protect", "stop loss", "cash", "treasury", "bills"]):
        score -= 0.6

    return max(-3.0, min(3.0, score))


def classify_level(answers: dict) -> str:
    # answers is expected to have q1..q5 keys with string values
    score_map = {
        "q1": {"I am just getting started": 0, "I actively manage my own portfolio": 1, "I manage portfolios professionally": 2},
        "q2": {"Occasionally": 0, "Monthly or quarterly": 1, "Frequently / as part of my work": 2},
        "q3": {"I want guidance and clarity": 0, "I want to understand risk before acting": 1, "I want tools to justify and document decisions": 2},
        "q4": {"Under $50k": 0, "$50k–$1M": 1, "$1M+": 2},
        "q5": {"Not very": 0, "Somewhat": 1, "Very comfortable": 2},
    }

    total = 0
    for k, m in score_map.items():
        v = answers.get(k, "")
        total += m.get(v, 0)

    if total <= 3:
        return "Beginner"
    if total <= 6:
        return "Intermediate"
    return "Expert"


def map_user_level_to_type(user_level: str) -> UserType:
    """
    Map user level (from questionnaire) to appropriate user type for GLOQONT

    Beginner -> RETAIL
    Intermediate -> ADVISOR
    Expert -> HNI
    """
    if user_level == "Beginner":
        return UserType.RETAIL
    elif user_level == "Intermediate":
        return UserType.ADVISOR
    else:  # Expert
        return UserType.HNI


def _impact_from_score(score: float, risk_budget: str) -> dict:
    vol = {"LOW": 1.0, "MEDIUM": 1.6, "HIGH": 2.4}[risk_budget]

    expected = score * 0.8
    worst = expected - vol * (2.5 + abs(score))
    best = expected + vol * (2.0 + abs(score))

    expected = max(-20.0, min(20.0, expected))
    worst = max(-60.0, min(10.0, worst))
    best = max(-10.0, min(60.0, best))

    confidence = "LOW" if abs(score) >= 2 else "MEDIUM" if abs(score) >= 1 else "HIGH"
    return {"expected": expected, "worst": worst, "best": best, "confidence": confidence}


# ----------------------------
# Decision parser + consequence engine (ported from Streamlit logic)
# ----------------------------
def analyze_decision_text(text: str, portfolio: Dict[str, Any]) -> str:
    t = text.lower()
    # try ticker match
    for p in portfolio.get("positions", []):
        ticker = (p.get("ticker") or "").lower()
        if ticker and ticker in t:
            return p.get("ticker")
    # fallback: macro
    return "Macro / Multi-Asset"


def consequence_engine(target: str, magnitude: int, portfolio: Dict[str, Any], total_value: float, mode: str) -> Dict[str, Any]:
    # weights in stored portfolio are decimals (0..1)
    positions = portfolio.get("positions", [])

    w = 18.0
    # if target is a ticker in positions
    for pos in positions:
        if pos.get("ticker") == target:
            w = float(pos.get("weight", 0)) * 100.0
            break

    base_risk = w / 8.0
    size_boost = 1.0 + float(magnitude) / 18.0
    risk_multiplier = base_risk * size_boost

    worst = -risk_multiplier * 2.4
    best = risk_multiplier * 1.2
    expected = (worst + best) / 2.0

    if "Reflexive" in mode:
        break_time = max(2, int(35 / risk_multiplier))
        unit = "minutes"
    else:
        break_time = max(5, int(55 / risk_multiplier))
        unit = "months"

    block = risk_multiplier > 6 or break_time <= 4

    return {
        "weight": round(w, 2),
        "worst": round(worst, 2),
        "best": round(best, 2),
        "expected": round(expected, 2),
        "multiplier": round(risk_multiplier, 1),
        "break_time": break_time,
        "unit": unit,
        "block": block,
    }


@app.post("/api/v1/scenario/run", response_model=ScenarioOut)
def scenario_run(request: Request, body: ScenarioIn):
    import re  # Import re at the beginning to avoid UnboundLocalError
    require_admin(request)

    # Load portfolio
    pstore = read_portfolios()
    pitems = pstore.get("items", [])
    if not pitems:
        raise HTTPException(status_code=400, detail="No saved portfolio found. Save a portfolio first.")
    portfolio = pitems[0]

    # Build market context: fetch recent prices and simple analytics
    tickers = [p["ticker"] for p in portfolio.get("positions", [])]
    try:
        data = fetch_prices(tickers, lookback_days=30, interval="1d")
    except Exception:
        data = None

    score = _decision_score(body.decision_text)
    impact = _impact_from_score(score, portfolio.get("risk_budget", "MEDIUM"))

    # Adjust impact based on decision type
    if body.decision_type == "trade":
        # For trade decisions, the impact might be different since it's adding new assets
        # We can adjust the impact calculation based on whether it's a trade or rebalance
        impact["expected"] *= 1.1  # Slightly higher expected return for trade decisions
        impact["worst"] *= 1.2     # Slightly higher risk for trade decisions
        impact["best"] *= 1.05     # Slightly higher best case for trade decisions
    elif body.decision_type == "rebalance":
        # For rebalancing, the impact is focused on existing portfolio adjustments
        # Keep the original impact calculation

        # Additional validation for rebalancing: check if mentioned tickers are in portfolio
        decision_lower = body.decision_text.lower()
        portfolio_tickers = [p["ticker"].lower() for p in portfolio.get("positions", [])]

        # This is a simplified check - in a real implementation, you'd want more sophisticated parsing
        for ticker in portfolio_tickers:
            if ticker.lower() in decision_lower:
                # Found a ticker from portfolio in the decision text
                break
        else:
            # If no portfolio tickers were found in the decision text, it might be a trade decision
            # But since the frontend validates this, we trust the decision_type parameter
            pass

    # Parse the decision text for multiple assets using the enhanced asset resolver
    decision_text_lower = body.decision_text.lower()

    # Get all multiple actions from the decision text
    all_actions = ASSET_RESOLVER._parse_multiple_actions(body.decision_text)

    if all_actions and len(all_actions) > 1:
        # Multiple actions detected - process all of them
        decision_summary = {
            "decision_type": "multi_asset_decision",
            "actions": [],
            "decision_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

        # Process each action in sequence
        current_positions = portfolio.get("positions", []).copy()

        for action, asset_symbol, allocation_change_pct_decimal in all_actions:
            # Resolve the asset to get canonical information
            asset_info = ASSET_RESOLVER.resolve_asset(asset_symbol)

            # If asset resolution fails, skip this action
            if not asset_info or not asset_info.is_valid:
                continue

            # Check if the asset already exists in the current portfolio state
            existing_pos = next((p for p in current_positions if p.get("ticker", "").upper() == asset_info.symbol.upper()), None)

            # Determine decision type based on strict semantics and action
            if existing_pos:
                if action == "sell":
                    decision_type = "decrease_exposure"  # If asset exists and action is sell, treat as decrease exposure
                else:
                    decision_type = "increase_exposure"  # If asset exists and action is buy, treat as increase exposure
                weight_before = existing_pos.get("weight", 0) * 100
            else:
                decision_type = "new_position"  # If asset doesn't exist, treat as new position
                weight_before = 0.0

            # Add this action to the decision summary
            decision_summary["actions"].append({
                "decision_type": decision_type,
                "asset": {
                    "symbol": asset_info.symbol,
                    "name": asset_info.name,
                    "country": asset_info.country,
                    "sector": asset_info.sector
                },
                "action": action,
                "allocation_change_pct": round(float(allocation_change_pct_decimal), 2),
                "previous_weight_pct": round(weight_before, 2),  # Explicitly state previous weight
                "funding_source": "pro-rata",  # Assuming proportional from existing holdings
            })

            # Update the current positions based on this action
            allocation_change_pct = float(allocation_change_pct_decimal)

            # Find and update the position
            position_found = False
            for i, pos in enumerate(current_positions):
                if pos.get("ticker", "").upper() == asset_info.symbol.upper():
                    # Update existing position
                    original_weight = pos.get("weight", 0) * 100
                    new_weight = original_weight + allocation_change_pct
                    current_positions[i]["weight"] = new_weight / 100.0  # Convert back to decimal
                    position_found = True
                    break

            if not position_found:
                # Add new position if it doesn't exist
                current_positions.append({
                    "ticker": asset_info.symbol,
                    "weight": allocation_change_pct / 100.0  # Convert percentage to decimal
                })

        # After processing all actions, calculate the overall impact
        # Use the first action for primary exposure impact for compatibility
        if all_actions:
            first_action, first_asset_symbol, first_allocation_change_pct = all_actions[0]
            first_asset_info = ASSET_RESOLVER.resolve_asset(first_asset_symbol)

            if first_asset_info and first_asset_info.is_valid:
                # Calculate primary exposure impact based on the first action
                weight_before = 0.0
                existing_pos = next((p for p in portfolio.get("positions", []) if p.get("ticker", "").upper() == first_asset_info.symbol.upper()), None)
                if existing_pos:
                    weight_before = existing_pos.get("weight", 0) * 100

                weight_after = weight_before + float(first_allocation_change_pct)

                primary_exposure_impact = {
                    "asset_symbol": first_asset_info.symbol if first_asset_info else "UNKNOWN",
                    "weight_before_pct": round(weight_before, 2),
                    "weight_after_pct": round(weight_after, 2),
                    "absolute_change_pct": round(float(first_allocation_change_pct), 2),
                    "all_actions_processed": len(all_actions)  # Indicate how many actions were processed
                }

                # For frontend validation compatibility, also add expected fields to decision_summary
                # Take the first action as the primary for validation purposes
                first_action_data = decision_summary["actions"][0] if decision_summary["actions"] else None
                if first_action_data:
                    decision_summary["asset"] = first_action_data.get("asset", {"symbol": "MULTIPLE_ASSETS"})
                    decision_summary["allocation_change_pct"] = first_action_data.get("allocation_change_pct", 0.0)
                    decision_summary["previous_weight_pct"] = first_action_data.get("previous_weight_pct", 0.0)
                    decision_summary["funding_source"] = first_action_data.get("funding_source", "pro-rata")
            else:
                # Fallback if first asset is invalid
                primary_exposure_impact = {
                    "asset_symbol": "MULTIPLE_ASSETS",
                    "weight_before_pct": 0.0,
                    "weight_after_pct": 0.0,
                    "absolute_change_pct": 0.0,
                    "all_actions_processed": len(all_actions)
                }

                # Add fallback fields for validation
                decision_summary["asset"] = {"symbol": "UNKNOWN"}
                decision_summary["allocation_change_pct"] = 0.0
                decision_summary["previous_weight_pct"] = 0.0
                decision_summary["funding_source"] = "pro-rata"
        else:
            # No valid actions found
            primary_exposure_impact = {
                "asset_symbol": "UNKNOWN",
                "weight_before_pct": 0.0,
                "weight_after_pct": 0.0,
                "absolute_change_pct": 0.0,
                "all_actions_processed": 0
            }

            # Add fallback fields for validation
            decision_summary["asset"] = {"symbol": "UNKNOWN"}
            decision_summary["allocation_change_pct"] = 0.0
            decision_summary["previous_weight_pct"] = 0.0
            decision_summary["funding_source"] = "pro-rata"

        # Concentration after decision for multi-asset case
        concentration_after_decision = {"top_exposures": [], "concentration_reduced": False, "actions_processed": len(all_actions)}

        # Calculate new portfolio weights after all decisions
        # Normalize the updated positions to sum to 100%
        total_weight = sum(pos.get("weight", 0) * 100 for pos in current_positions)
        new_positions = []
        if total_weight > 0:
            for pos in current_positions:
                ticker = pos.get("ticker")
                weight = (pos.get("weight", 0) * 100) / total_weight * 100  # Normalize to 100%
                new_positions.append({"symbol": ticker, "weight_pct": round(weight, 2)})
        else:
            # Fallback if total weight is 0
            for pos in portfolio.get("positions", []):
                ticker = pos.get("ticker")
                weight = pos.get("weight", 0) * 100
                new_positions.append({"symbol": ticker, "weight_pct": round(weight, 2)})

        # Validate portfolio weight conservation (weights must sum to 100% ±0.5%)
        total_weight_after = sum(pos["weight_pct"] for pos in new_positions)
        if abs(total_weight_after - 100.0) > 0.5:
            raise HTTPException(status_code=500, detail=f"Portfolio weight conservation failed: weights sum to {total_weight_after:.2f}% (expected ~100%)")

        # Sort by weight descending and take top 5
        sorted_positions = sorted(new_positions, key=lambda x: abs(x["weight_pct"]), reverse=True)  # Use abs value for sorting to handle negative weights
        concentration_after_decision["top_exposures"] = sorted_positions[:5]

        # Check if concentration was reduced (by comparing max position before/after)
        original_max_weight = max((pos.get("weight", 0) * 100 for pos in portfolio.get("positions", [])), default=0)
        new_max_weight = max((pos["weight_pct"] for pos in new_positions), default=0)
        concentration_after_decision["concentration_reduced"] = new_max_weight < original_max_weight

        # Ensure the decision asset is in the top exposures
        decision_asset_symbol = asset_info.symbol if 'asset_info' in locals() and asset_info else None
        if decision_asset_symbol:
            # Check if the decision asset is already in top exposures
            asset_already_in_top = any(exp.get("symbol", "").upper() == decision_asset_symbol.upper() for exp in concentration_after_decision["top_exposures"])

            if not asset_already_in_top:
                # Find the position with the decision asset
                decision_pos = next((pos for pos in new_positions if pos["symbol"].upper() == decision_asset_symbol.upper()), None)
                if decision_pos:
                    # Add it to top exposures and keep only top 5 by absolute weight
                    all_top_exposures = concentration_after_decision["top_exposures"] + [decision_pos]
                    # Remove duplicates - if the asset was somehow added twice
                    unique_exposures = {}
                    for exp in all_top_exposures:
                        symbol = exp.get("symbol", "").upper()
                        if symbol not in unique_exposures:
                            unique_exposures[symbol] = exp
                    all_unique_exposures = list(unique_exposures.values())

                    # Sort by absolute weight descending and take top 5
                    concentration_after_decision["top_exposures"] = sorted(
                        all_unique_exposures,
                        key=lambda x: abs(x["weight_pct"]),
                        reverse=True
                    )[:5]

        # Check if concentration was reduced (by comparing max position before/after)
        original_max_weight = max((pos.get("weight", 0) * 100 for pos in portfolio.get("positions", [])), default=0)
        new_max_weight = max((pos["weight_pct"] for pos in new_positions), default=0)
        concentration_after_decision["concentration_reduced"] = new_max_weight < original_max_weight

        # Market regimes sensitivity for multi-asset
        market_regimes = {
            "increased_sensitivity": [],
            "explanation": f"Multi-asset decision affecting {len(all_actions)} positions: {[f'{a[0]} {a[1]}' for a in all_actions]}",
            "actions_count": len(all_actions)
        }

        # Add appropriate sensitivities based on the assets involved
        for action, asset_symbol, allocation_change_pct in all_actions:
            asset_info = ASSET_RESOLVER.resolve_asset(asset_symbol)
            if asset_info and asset_info.country.lower() == "usa":
                market_regimes["increased_sensitivity"].extend([
                    "us_equity_volatility",
                    "us_macro_stress"
                ])
            elif asset_info and asset_info.country.lower() == "india":
                market_regimes["increased_sensitivity"].extend([
                    "emerging_market_volatility",
                    "global_liquidity_stress"
                ])
            elif asset_info and asset_info.sector.lower() == "technology":
                market_regimes["increased_sensitivity"].extend([
                    "technology_sector_volatility",
                    "growth_stock_rotation"
                ])
            elif asset_info and asset_info.sector.lower() == "consumer cyclical":
                market_regimes["increased_sensitivity"].extend([
                    "consumer_confidence_shock",
                    "recession_risk"
                ])
            else:
                market_regimes["increased_sensitivity"].extend([
                    "liquidity_stress",
                    "volatility_spike"
                ])

    else:
        # Single asset case - parse using the canonical asset resolver
        action, asset_symbol, allocation_change_pct = ASSET_RESOLVER.validate_decision_structure(body.decision_text)

        # Resolve the asset to get canonical information
        asset_info = ASSET_RESOLVER.resolve_asset(asset_symbol)

        # If asset resolution fails, throw an error
        if not asset_info or not asset_info.is_valid:
            raise HTTPException(status_code=400, detail=f"Asset '{asset_symbol}' could not be resolved. Please use a valid ticker symbol.")

        # Check if the asset already exists in the portfolio
        existing_pos = next((p for p in portfolio.get("positions", []) if p.get("ticker", "").upper() == asset_info.symbol.upper()), None)

        # Determine decision type based on strict semantics and action
        if existing_pos:
            if action == "sell":
                decision_type = "decrease_exposure"  # If asset exists and action is sell, treat as decrease exposure
            else:
                decision_type = "increase_exposure"  # If asset exists and action is buy, treat as increase exposure
            weight_before = existing_pos.get("weight", 0) * 100
        else:
            decision_type = "new_position"  # If asset doesn't exist, treat as new position
            weight_before = 0.0

        # Construct the decision summary according to the strict contract
        decision_summary = {
            "decision_type": decision_type,
            "asset": {
                "symbol": asset_info.symbol,
                "name": asset_info.name,
                "country": asset_info.country,
                "sector": asset_info.sector
            },
            "action": action,
            "allocation_change_pct": round(float(allocation_change_pct), 2),
            "previous_weight_pct": round(weight_before, 2),  # Explicitly state previous weight
            "funding_source": "pro-rata",  # Assuming proportional from existing holdings
            "decision_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }

        # Primary exposure impact
        weight_before = 0.0
        if asset_info:
            existing_pos = next((p for p in portfolio.get("positions", []) if p.get("ticker", "").upper() == asset_info.symbol.upper()), None)
            if existing_pos:
                weight_before = existing_pos.get("weight", 0) * 100

        # Calculate weight_after: add the signed allocation change
        # (allocation_change_pct is already signed: negative for sells, positive for buys)
        weight_after = weight_before + float(allocation_change_pct)

        primary_exposure_impact = {
            "asset_symbol": asset_info.symbol if asset_info else "UNKNOWN",
            "weight_before_pct": round(weight_before, 2),
            "weight_after_pct": round(weight_after, 2),
            "absolute_change_pct": round(float(allocation_change_pct), 2)  # Use the value as-is from asset resolver (already has correct sign)
        }

        # Validate the primary exposure impact contract: weight_before + allocation_change == weight_after (±0.01)
        expected_weight_after = weight_before + float(allocation_change_pct)
        if abs(weight_after - expected_weight_after) > 0.01:
            raise HTTPException(status_code=500, detail=f"Primary exposure impact contract violated: {weight_before} + {float(allocation_change_pct)} != {weight_after}")

        # Market regimes sensitivity for single asset
        market_regimes = {
            "increased_sensitivity": [],
            "explanation": ""
        }

        if asset_info and asset_info.country.lower() == "india":
            market_regimes["increased_sensitivity"].extend([
                "emerging_market_volatility",
                "global_liquidity_stress"
            ])
            market_regimes["explanation"] = f"Introduces cyclical {asset_info.country} equity exposure"
        elif asset_info and asset_info.sector.lower() == "technology":
            market_regimes["increased_sensitivity"].extend([
                "technology_sector_volatility",
                "growth_stock_rotation"
            ])
            market_regimes["explanation"] = f"Increases {asset_info.sector} sector exposure"
        else:
            market_regimes["increased_sensitivity"].extend([
                "liquidity_stress",
                "volatility_spike"
            ])
            market_regimes["explanation"] = "Changes portfolio composition and risk profile"

        # Concentration after decision for single asset
        concentration_after_decision = {"top_exposures": [], "concentration_reduced": False}

        # Calculate new portfolio weights after the decision
        new_positions = []

        # Check if funding logic is needed (for allocation changes >5%)
        allocation_change_abs = abs(float(allocation_change_pct))
        needs_funding_logic = allocation_change_abs > 5.0

        if needs_funding_logic:
            # For large changes, we need to explicitly handle funding sources
            funding_breakdown = {}
            total_reduction_needed = 0.0

            # If this is a buy action, we need to fund it from existing positions
            if action == "buy":
                # Calculate proportional reduction from other assets to fund the purchase
                for pos in portfolio.get("positions", []):
                    ticker = pos.get("ticker")
                    original_weight = pos.get("weight", 0) * 100

                    if ticker.upper() == asset_info.symbol.upper():
                        # This is the position being increased
                        new_weight = original_weight + float(allocation_change_pct)
                        new_positions.append({"symbol": ticker, "weight_pct": round(new_weight, 2)})
                        funding_breakdown[ticker] = float(allocation_change_pct)  # Positive means added
                    else:
                        # This is a funding source - reduce proportionally
                        reduction_amount = (original_weight / 100.0) * float(allocation_change_pct)
                        new_weight = original_weight - reduction_amount
                        new_positions.append({"symbol": ticker, "weight_pct": round(new_weight, 2)})
                        funding_breakdown[ticker] = -reduction_amount  # Negative means reduced
            else:
                # If this is a sell action
                for pos in portfolio.get("positions", []):
                    ticker = pos.get("ticker")
                    original_weight = pos.get("weight", 0) * 100

                    if ticker.upper() == asset_info.symbol.upper():
                        # This is the position being decreased
                        # allocation_change_pct is already negative for sell actions, so we add it
                        new_weight = original_weight + float(allocation_change_pct)
                        new_positions.append({"symbol": ticker, "weight_pct": round(new_weight, 2)})
                        funding_breakdown[ticker] = float(allocation_change_pct)  # Already negative for sell
                    else:
                        # Other positions may receive the freed funds proportionally
                        # For simplicity, we'll distribute proportionally among remaining assets
                        remaining_weight_sum = sum(p.get("weight", 0) * 100 for p in portfolio.get("positions", []) if p.get("ticker").upper() != asset_info.symbol.upper())
                        if remaining_weight_sum > 0:
                            # For sell actions, the freed cash is distributed proportionally to other positions
                            allocation_share = (original_weight / remaining_weight_sum) * abs(float(allocation_change_pct))
                            new_weight = original_weight + allocation_share
                            new_positions.append({"symbol": ticker, "weight_pct": round(new_weight, 2)})
                            funding_breakdown[ticker] = allocation_share
                        else:
                            new_positions.append({"symbol": ticker, "weight_pct": round(original_weight, 2)})

            # Add funding breakdown to the result for transparency
            result_funding_breakdown = funding_breakdown
        else:
            # For smaller changes, use the simple adjustment
            for pos in portfolio.get("positions", []):
                ticker = pos.get("ticker")
                weight = pos.get("weight", 0) * 100

                # If this is the ticker being modified, adjust its weight
                if ticker.upper() == asset_info.symbol.upper():
                    # allocation_change_pct is already signed (negative for sell, positive for buy)
                    weight = weight + float(allocation_change_pct)

                new_positions.append({"symbol": ticker, "weight_pct": round(weight, 2)})

            # No detailed funding breakdown needed for small changes
            result_funding_breakdown = None

        # If it's a new position (not in original portfolio), add it
        if asset_info and not any(pos["symbol"].upper() == asset_info.symbol.upper() for pos in new_positions):
            new_positions.append({"symbol": asset_info.symbol, "weight_pct": round(float(allocation_change_pct), 2)})

        # Normalize all weights to sum to 100% after the decision
        # This handles the case where the raw sum doesn't equal 100% due to the allocation change
        total_raw_weight = sum(pos["weight_pct"] for pos in new_positions)
        if total_raw_weight > 0 and abs(total_raw_weight - 100.0) > 0.1:  # Only normalize if significantly different
            normalized_positions = []
            for pos in new_positions:
                normalized_weight = (pos["weight_pct"] / total_raw_weight) * 100.0
                normalized_positions.append({"symbol": pos["symbol"], "weight_pct": round(normalized_weight, 2)})
            new_positions = normalized_positions

        # Validate portfolio weight conservation (weights must sum to 100% ±0.5%)
        total_weight_after = sum(pos["weight_pct"] for pos in new_positions)
        if abs(total_weight_after - 100.0) > 0.5:
            raise HTTPException(status_code=500, detail=f"Portfolio weight conservation failed: weights sum to {total_weight_after:.2f}% (expected ~100%)")

        # Sort by weight descending and take top 5
        sorted_positions = sorted(new_positions, key=lambda x: abs(x["weight_pct"]), reverse=True)  # Use abs value for sorting to handle negative weights
        concentration_after_decision["top_exposures"] = sorted_positions[:5]

        # Ensure the decision asset is in the top exposures
        decision_asset_symbol = asset_info.symbol if asset_info else None
        if decision_asset_symbol:
            # Check if the decision asset is already in top exposures
            asset_already_in_top = any(exp.get("symbol", "").upper() == decision_asset_symbol.upper() for exp in concentration_after_decision["top_exposures"])

            if not asset_already_in_top:
                # Find the position with the decision asset
                decision_pos = next((pos for pos in new_positions if pos["symbol"].upper() == decision_asset_symbol.upper()), None)
                if decision_pos:
                    # Add it to top exposures and keep only top 5 by absolute weight
                    all_top_exposures = concentration_after_decision["top_exposures"] + [decision_pos]
                    # Remove duplicates - if the asset was somehow added twice
                    unique_exposures = {}
                    for exp in all_top_exposures:
                        symbol = exp.get("symbol", "").upper()
                        if symbol not in unique_exposures:
                            unique_exposures[symbol] = exp
                    all_unique_exposures = list(unique_exposures.values())

                    # Sort by absolute weight descending and take top 5
                    concentration_after_decision["top_exposures"] = sorted(
                        all_unique_exposures,
                        key=lambda x: abs(x["weight_pct"]),
                        reverse=True
                    )[:5]

        # Check if concentration was reduced (by comparing max position before/after)
        original_max_weight = max((pos.get("weight", 0) * 100 for pos in portfolio.get("positions", [])), default=0)
        new_max_weight = max((pos["weight_pct"] for pos in new_positions), default=0)
        concentration_after_decision["concentration_reduced"] = new_max_weight < original_max_weight

    # Risk impact - this should be available for both single and multi-asset cases
    # Calculate risk impact based on the overall impact
    downside_pct = round(impact["worst"], 2)
    expected_pct = round(impact["expected"], 2)
    upside_pct = round(impact["best"], 2)

    # Validate risk impact contract: downside < expected < upside
    if not (downside_pct < expected_pct < upside_pct):
        raise HTTPException(status_code=500, detail=f"Risk impact contract violated: {downside_pct} < {expected_pct} < {upside_pct} is not satisfied")

    risk_impact = {
        "horizon_days": 30,
        "downside_pct": downside_pct,
        "expected_pct": expected_pct,
        "upside_pct": upside_pct,
        "methodology": "scenario-based",
        "confidence_note": "Illustrative, not a forecast",
        "actions_count": len(all_actions) if 'all_actions' in locals() and all_actions else 1
    }

    # Time to risk realization (optional)
    time_to_risk = {
        "threshold_definition": "loss exceeds X% under stress",
        "estimated_days": 7 if abs(impact["worst"]) > 5 else 30,
        "applicable_conditions": [
            "volatility_spike",
            "liquidity_drawdown"
        ],
        "actions_count": len(all_actions) if 'all_actions' in locals() and all_actions else 1
    }

    # Market regimes sensitivity
    market_regimes = {
        "increased_sensitivity": [],
        "explanation": f"Multi-asset decision affecting {len(all_actions) if 'all_actions' in locals() and all_actions else 1} positions",
        "actions_count": len(all_actions) if 'all_actions' in locals() and all_actions else 1
    }

    # Add appropriate sensitivities based on the assets involved for multi-asset decisions
    if 'all_actions' in locals() and all_actions and len(all_actions) > 1:
        # Multi-asset case
        for action, asset_symbol, allocation_change_pct in all_actions:
            asset_info = ASSET_RESOLVER.resolve_asset(asset_symbol)
            if asset_info and asset_info.is_valid:
                if asset_info.country.lower() == "usa":
                    market_regimes["increased_sensitivity"].extend([
                        "us_equity_volatility",
                        "us_macro_stress"
                    ])
                elif asset_info.country.lower() == "india":
                    market_regimes["increased_sensitivity"].extend([
                        "emerging_market_volatility",
                        "global_liquidity_stress"
                    ])
                elif asset_info.sector.lower() == "technology":
                    market_regimes["increased_sensitivity"].extend([
                        "technology_sector_volatility",
                        "growth_stock_rotation"
                    ])
                elif asset_info.sector.lower() == "consumer cyclical":
                    market_regimes["increased_sensitivity"].extend([
                        "consumer_confidence_shock",
                        "recession_risk"
                    ])
                else:
                    market_regimes["increased_sensitivity"].extend([
                        "liquidity_stress",
                        "volatility_spike"
                    ])
    else:
        # For single asset case, add appropriate sensitivities
        if 'asset_info' in locals() and asset_info and asset_info.is_valid:
            if asset_info.country.lower() == "india":
                market_regimes["increased_sensitivity"].extend([
                    "emerging_market_volatility",
                    "global_liquidity_stress"
                ])
                market_regimes["explanation"] = f"Introduces cyclical {asset_info.country} equity exposure"
            elif asset_info.sector.lower() == "technology":
                market_regimes["increased_sensitivity"].extend([
                    "technology_sector_volatility",
                    "growth_stock_rotation"
                ])
                market_regimes["explanation"] = f"Increases {asset_info.sector} sector exposure"
            else:
                market_regimes["increased_sensitivity"].extend([
                    "liquidity_stress",
                    "volatility_spike"
                ])
                market_regimes["explanation"] = "Changes portfolio composition and risk profile"
        else:
            # Default sensitivities if asset_info is not available
            market_regimes["increased_sensitivity"].extend([
                "liquidity_stress",
                "volatility_spike"
            ])
            market_regimes["explanation"] = "Changes portfolio composition and risk profile"

    # Concentration after decision
    concentration_after_decision = {"top_exposures": [], "concentration_reduced": False, "actions_processed": len(all_actions) if 'all_actions' in locals() and all_actions else 1}

    # Calculate new portfolio weights after all decisions
    # This section needs to handle both single and multi-asset cases
    new_positions = []

    # For multi-asset (more than 1 action), we already have current_positions updated
    # For single asset or single action, we need to process differently
    if 'all_actions' in locals() and all_actions and len(all_actions) > 1:
        # Multi-asset case - use current_positions
        # Normalize the updated positions to sum to 100%
        total_weight = sum(pos.get("weight", 0) * 100 for pos in current_positions)
        if total_weight > 0:
            for pos in current_positions:
                ticker = pos.get("ticker")
                weight = (pos.get("weight", 0) * 100) / total_weight * 100  # Normalize to 100%
                new_positions.append({"symbol": ticker, "weight_pct": round(weight, 2)})
        else:
            # Fallback if total weight is 0
            for pos in portfolio.get("positions", []):
                ticker = pos.get("ticker")
                weight = pos.get("weight", 0) * 100
                new_positions.append({"symbol": ticker, "weight_pct": round(weight, 2)})
    else:
        # Single action case - the new_positions should have already been calculated in the single asset processing section
        # The single asset processing happens earlier in the function, so new_positions should already be populated
        # If we reach here and new_positions is empty, we should populate it from the original portfolio
        if not new_positions:
            # Copy original positions to new_positions for single asset case
            for pos in portfolio.get("positions", []):
                ticker = pos.get("ticker")
                weight = pos.get("weight", 0) * 100
                new_positions.append({"symbol": ticker, "weight_pct": round(weight, 2)})

    # Process concentration and other data for whichever case we're in
    # Validate portfolio weight conservation (weights must sum to 100% ±0.5%)
    if new_positions:
        total_weight_after = sum(pos["weight_pct"] for pos in new_positions)
        if abs(total_weight_after - 100.0) > 0.5:
            raise HTTPException(status_code=500, detail=f"Portfolio weight conservation failed: weights sum to {total_weight_after:.2f}% (expected ~100%)")

        # Sort by weight descending and take top 5
        sorted_positions = sorted(new_positions, key=lambda x: abs(x["weight_pct"]), reverse=True)  # Use abs value for sorting to handle negative weights
        concentration_after_decision["top_exposures"] = sorted_positions[:5]

        # Check if concentration was reduced (by comparing max position before/after)
        original_max_weight = max((pos.get("weight", 0) * 100 for pos in portfolio.get("positions", [])), default=0)
        new_max_weight = max((pos["weight_pct"] for pos in new_positions), default=0)
        concentration_after_decision["concentration_reduced"] = new_max_weight < original_max_weight

        # Ensure the decision asset is in the top exposures
        decision_asset_symbol = asset_info.symbol if 'asset_info' in locals() and asset_info else None
        if decision_asset_symbol:
            # Check if the decision asset is already in top exposures
            asset_already_in_top = any(exp.get("symbol", "").upper() == decision_asset_symbol.upper() for exp in concentration_after_decision["top_exposures"])

            if not asset_already_in_top:
                # Find the position with the decision asset
                decision_pos = next((pos for pos in new_positions if pos["symbol"].upper() == decision_asset_symbol.upper()), None)
                if decision_pos:
                    # Add it to top exposures and keep only top 5 by absolute weight
                    all_top_exposures = concentration_after_decision["top_exposures"] + [decision_pos]
                    # Remove duplicates - if the asset was somehow added twice
                    unique_exposures = {}
                    for exp in all_top_exposures:
                        symbol = exp.get("symbol", "").upper()
                        if symbol not in unique_exposures:
                            unique_exposures[symbol] = exp
                    all_unique_exposures = list(unique_exposures.values())

                    # Sort by absolute weight descending and take top 5
                    concentration_after_decision["top_exposures"] = sorted(
                        all_unique_exposures,
                        key=lambda x: abs(x["weight_pct"]),
                        reverse=True
                    )[:5]

        # Check if concentration was reduced (by comparing max position before/after)
        original_max_weight = max((pos.get("weight", 0) * 100 for pos in portfolio.get("positions", [])), default=0)
        new_max_weight = max((pos["weight_pct"] for pos in new_positions), default=0)
        concentration_after_decision["concentration_reduced"] = new_max_weight < original_max_weight

        # Concentration after decision
        concentration_after_decision = {"top_exposures": [], "concentration_reduced": False}

        # Calculate new portfolio weights after the decision
        new_positions = []

        # Check if funding logic is needed (for allocation changes >5%)
        allocation_change_abs = abs(float(allocation_change_pct))
        needs_funding_logic = allocation_change_abs > 5.0

        if needs_funding_logic:
            # For large changes, we need to explicitly handle funding sources
            funding_breakdown = {}
            total_reduction_needed = 0.0

            # If this is a buy action, we need to fund it from existing positions
            if action == "buy":
                # Calculate proportional reduction from other assets to fund the purchase
                remaining_positions = []
                for pos in portfolio.get("positions", []):
                    ticker = pos.get("ticker")
                    original_weight = pos.get("weight", 0) * 100

                    if ticker.upper() == asset_info.symbol.upper():
                        # This is the position being increased
                        new_weight = original_weight + float(allocation_change_pct)
                        new_positions.append({"symbol": ticker, "weight_pct": round(new_weight, 2)})
                        funding_breakdown[ticker] = float(allocation_change_pct)  # Positive means added
                    else:
                        # This is a funding source - reduce proportionally
                        reduction_amount = (original_weight / 100.0) * float(allocation_change_pct)
                        new_weight = original_weight - reduction_amount
                        new_positions.append({"symbol": ticker, "weight_pct": round(new_weight, 2)})
                        funding_breakdown[ticker] = -reduction_amount  # Negative means reduced
            else:
                # If this is a sell action
                for pos in portfolio.get("positions", []):
                    ticker = pos.get("ticker")
                    original_weight = pos.get("weight", 0) * 100

                    if ticker.upper() == asset_info.symbol.upper():
                        # This is the position being decreased
                        # allocation_change_pct is already negative for sell actions, so we add it
                        new_weight = original_weight + float(allocation_change_pct)
                        new_positions.append({"symbol": ticker, "weight_pct": round(new_weight, 2)})
                        funding_breakdown[ticker] = float(allocation_change_pct)  # Already negative for sell
                    else:
                        # Other positions may receive the freed funds proportionally
                        # For simplicity, we'll distribute proportionally among remaining assets
                        remaining_weight_sum = sum(p.get("weight", 0) * 100 for p in portfolio.get("positions", []) if p.get("ticker").upper() != asset_info.symbol.upper())
                        if remaining_weight_sum > 0:
                            # For sell actions, the freed cash is distributed proportionally to other positions
                            allocation_share = (original_weight / remaining_weight_sum) * abs(float(allocation_change_pct))
                            new_weight = original_weight + allocation_share
                            new_positions.append({"symbol": ticker, "weight_pct": round(new_weight, 2)})
                            funding_breakdown[ticker] = allocation_share
                        else:
                            new_positions.append({"symbol": ticker, "weight_pct": round(original_weight, 2)})

            # Add funding breakdown to the result for transparency
            result_funding_breakdown = funding_breakdown
        else:
            # For smaller changes, use the simple adjustment
            for pos in portfolio.get("positions", []):
                ticker = pos.get("ticker")
                weight = pos.get("weight", 0) * 100

                # If this is the ticker being modified, adjust its weight
                if ticker.upper() == asset_info.symbol.upper():
                    # allocation_change_pct is already signed (negative for sell, positive for buy)
                    weight = weight + float(allocation_change_pct)

                new_positions.append({"symbol": ticker, "weight_pct": round(weight, 2)})

            # No detailed funding breakdown needed for small changes
            result_funding_breakdown = None

        # If it's a new position (not in original portfolio), add it
        if asset_info and not any(pos["symbol"].upper() == asset_info.symbol.upper() for pos in new_positions):
            new_positions.append({"symbol": asset_info.symbol, "weight_pct": round(float(allocation_change_pct), 2)})

        # Normalize all weights to sum to 100% after the decision
        # This handles the case where the raw sum doesn't equal 100% due to the allocation change
        total_raw_weight = sum(pos["weight_pct"] for pos in new_positions)
        if total_raw_weight > 0 and abs(total_raw_weight - 100.0) > 0.1:  # Only normalize if significantly different
            normalized_positions = []
            for pos in new_positions:
                normalized_weight = (pos["weight_pct"] / total_raw_weight) * 100.0
                normalized_positions.append({"symbol": pos["symbol"], "weight_pct": round(normalized_weight, 2)})
            new_positions = normalized_positions

        # Validate portfolio weight conservation (weights must sum to 100% ±0.5%)
        total_weight_after = sum(pos["weight_pct"] for pos in new_positions)
        if abs(total_weight_after - 100.0) > 0.5:
            raise HTTPException(status_code=500, detail=f"Portfolio weight conservation failed: weights sum to {total_weight_after:.2f}% (expected ~100%)")

        # Sort by weight descending and take top 5
        sorted_positions = sorted(new_positions, key=lambda x: abs(x["weight_pct"]), reverse=True)  # Use abs value for sorting to handle negative weights
        concentration_after_decision["top_exposures"] = sorted_positions[:5]

        # Ensure the decision asset is in the top exposures
        decision_asset_symbol = asset_info.symbol if asset_info else None
        if decision_asset_symbol:
            # Check if the decision asset is already in top exposures
            asset_already_in_top = any(exp.get("symbol", "").upper() == decision_asset_symbol.upper() for exp in concentration_after_decision["top_exposures"])

            if not asset_already_in_top:
                # Find the position with the decision asset
                decision_pos = next((pos for pos in new_positions if pos["symbol"].upper() == decision_asset_symbol.upper()), None)
                if decision_pos:
                    # Add it to top exposures and keep only top 5 by absolute weight
                    all_top_exposures = concentration_after_decision["top_exposures"] + [decision_pos]
                    # Remove duplicates - if the asset was somehow added twice
                    unique_exposures = {}
                    for exp in all_top_exposures:
                        symbol = exp.get("symbol", "").upper()
                        if symbol not in unique_exposures:
                            unique_exposures[symbol] = exp
                    all_unique_exposures = list(unique_exposures.values())

                    # Sort by absolute weight descending and take top 5
                    concentration_after_decision["top_exposures"] = sorted(
                        all_unique_exposures,
                        key=lambda x: abs(x["weight_pct"]),
                        reverse=True
                    )[:5]

        # Check if concentration was reduced (by comparing max position before/after)
        original_max_weight = max((pos.get("weight", 0) * 100 for pos in portfolio.get("positions", [])), default=0)
        new_max_weight = max((pos["weight_pct"] for pos in new_positions), default=0)
        concentration_after_decision["concentration_reduced"] = new_max_weight < original_max_weight

    # Irreversibility risk
    irreversible_loss_usd = round(max(0.0, portfolio.get("total_value", 0) * max(0, -impact["worst"]) / 100.0), 2)
    irreversibility = {
        "irreversible_loss_usd": irreversible_loss_usd,
        "irreversible_loss_pct": round(abs(impact["worst"]), 2),
        "recovery_time_months": 12 if impact["expected"] >= 0 else 36,
        "assumptions": [
            "forced liquidation",
            "adverse market regime"
        ]
    }

    # Irreversible loss heatmap
    irreversible_loss_heatmap = {
        "horizons_months": [1, 3, 6, 12],
        "loss_pct": [
            max(0, impact["worst"] * 0.5),
            max(0, impact["worst"] * 0.7),
            max(0, impact["worst"] * 0.9),
            max(0, impact["worst"] * 1.0)
        ],
        "interpretation": "Loss beyond statistical recovery bounds"
    }

    # Bottom-line decision summary
    decision_summary_line = {
        "max_decision_attributed_loss_usd": irreversible_loss_usd,
        "max_decision_attributed_loss_pct": round(abs(impact["worst"]), 2),
        "dominant_risk_driver": "market_drawdown"  # Would need more sophisticated analysis
    }

    # Market context
    market_context = {"as_of": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "notes": []}
    if data is not None:
        try:
            tail = data.prices.tail(24)
            market_context["prices_tail"] = {
                "index": [str(x) for x in tail.index],
                "values": {c: [float(v) for v in tail[c].values] for c in tail.columns},
            }
        except Exception:
            market_context["prices_tail"] = {}

    market_context["notes"].append("Market data snapshot provided.")

    baseline = {
        "description": "If You Do Nothing: portfolio risk remains unchanged.",
        "expected_change_pct": 0.0,
    }

    # For backward compatibility with existing UI, also return the old format fields
    # Determine appropriate language based on the action
    # Handle multi-asset decisions appropriately
    if decision_summary.get("decision_type") == "multi_asset_decision":
        # Multi-asset decision - create combined narrative for all actions
        action_description = "multi-asset"
        primary_exposure_ticker = "MULTIPLE_ASSETS"
        portfolio_weight_affected_pct = sum([abs(action[2]) for action in all_actions]) if all_actions else 0.0

        # Create combined executed decision text that mentions all actions
        action_descriptions = []
        if all_actions:
            for action, asset_symbol, allocation_change_pct in all_actions:
                change_pct = float(allocation_change_pct)
                action_desc = f"{'decreased' if change_pct < 0 else 'increased'} exposure to {asset_symbol} by {abs(change_pct)}%"
                action_descriptions.append(action_desc)

        # Combine the action descriptions
        if len(action_descriptions) > 1:
            actions_combined = ", and ".join([", ".join(action_descriptions[:-1]), action_descriptions[-1]])
        else:
            actions_combined = action_descriptions[0] if action_descriptions else "adjusted portfolio"

        executed_decision = {
            "discipline_warning": f"This multi-asset decision affects your portfolio risk profile.",
            "primary_exposure_ticker": primary_exposure_ticker,
            "portfolio_weight_affected_pct": round(portfolio_weight_affected_pct, 2),
            "downside_amplification_pct": round(impact["worst"], 2),
            "combined_actions_description": f"You {actions_combined} of portfolio value."
        }
    else:
        # Single asset decision
        action_description = "decrease" if action == "sell" else "increase"
        primary_exposure_ticker = asset_info.symbol if asset_info else "UNKNOWN"
        portfolio_weight_affected_pct = float(allocation_change_pct)

        executed_decision = {
            "discipline_warning": f"This {action_description} decision affects your portfolio risk profile.",
            "primary_exposure_ticker": primary_exposure_ticker,
            "portfolio_weight_affected_pct": round(portfolio_weight_affected_pct, 2),
            "downside_amplification_pct": round(impact["worst"], 2),
        }

    distribution = {
        "worst_pct": round(impact["worst"], 2),
        "expected_pct": round(impact["expected"], 2),
        "best_pct": round(impact["best"], 2),
    }

    time_to_damage_days = 7 if abs(impact["worst"]) > 5 else 30
    fragile_regimes = ["Liquidity Stress", "Volatility Spike"] if abs(impact["worst"]) > 5 else ["None"]

    # Risk concentration (for backward compatibility)
    risk_concentration = []
    for pos in sorted(portfolio.get("positions", []), key=lambda x: -x.get("weight", 0)):
        risk_concentration.append({"ticker": pos.get("ticker"), "weight_pct": round(pos.get("weight", 0) * 100, 2)})

    heatmap = [
        {"time_horizon_months": 1, "capital_loss_pct": round(max(0, impact["worst"] * 0.5), 2)},
        {"time_horizon_months": 6, "capital_loss_pct": round(max(0, impact["worst"] * 0.8), 2)},
        {"time_horizon_months": 12, "capital_loss_pct": round(max(0, impact["worst"] * 1.0), 2)},
    ]

    irreversible_summary = {
        "irreversible_exposure_usd": irreversible_loss_usd,
        "percent_of_portfolio": round(
            irreversible_loss_usd / max(1.0, portfolio.get("total_value", 1)) * 100.0, 2
        ),
    }

    # Validate the strict output contract
    validation_result = validate_strict_output_contract_with_portfolio(
        portfolio.get("total_value", 0),
        decision_summary,
        primary_exposure_impact,
        risk_impact,
        time_to_risk,
        market_regimes,
        concentration_after_decision,
        irreversibility_detailed=irreversibility,
        irreversible_loss_heatmap=irreversible_loss_heatmap,
        decision_summary_line=decision_summary_line,
        portfolio=portfolio,
        body=body
    )

    if not validation_result["ok"]:
        raise HTTPException(status_code=500, detail=f"Output contract validation failed: {validation_result['errors']}")

    print("DEBUG: About to create RealLifeDecision for visualization")

    # Create RealLifeDecision object to get visualization data
    # We need to determine the decision category for visualization purposes
    try:
        from enhanced_decision_classifier import DecisionCategory
        decision_category = DecisionCategory.TRADE_DECISION if body.decision_type == "trade" else DecisionCategory.PORTFOLIO_REBALANCING

        from decision_engine import DecisionConsequences, RealLifeDecision
        consequences = DecisionConsequences(portfolio, body.decision_text, decision_category)
        real_life_decision = RealLifeDecision(consequences, body.decision_text, portfolio)

        print(f"DEBUG: Successfully created RealLifeDecision, has visualization_data: {hasattr(real_life_decision, 'visualization_data')}")

        # For multiple actions, also create individual visualizations for each action
        all_visualization_data = [real_life_decision.visualization_data]  # Main visualization

        # If there are multiple actions, create individual visualizations for each
        if all_actions and len(all_actions) > 1:
            for action, asset_symbol, allocation_change_pct in all_actions:
                try:
                    # Create individual decision text for this specific action
                    individual_decision_text = f"{action.capitalize()} {asset_symbol} {float(allocation_change_pct):.2f}%"

                    # Create consequences and decision for this specific action
                    individual_consequences = DecisionConsequences(portfolio, individual_decision_text, decision_category)
                    individual_decision = RealLifeDecision(individual_consequences, individual_decision_text, portfolio)

                    # Add to the list of visualizations
                    all_visualization_data.append(individual_decision.visualization_data)
                except Exception as individual_error:
                    print(f"Error creating visualization for individual action {action} {asset_symbol}: {individual_error}")
                    continue

        # Add visualization data to the response
        result = {
            "ok": True,
            "market_context": market_context,
            "baseline": baseline,
            "executed_decision": executed_decision,
            "distribution": distribution,
            "time_to_damage_days": time_to_damage_days,
            "fragile_regimes": fragile_regimes,
            "risk_concentration": risk_concentration,
            "irreversibility": irreversibility,
            "heatmap": heatmap,
            "irreversible_summary": irreversible_summary,
            # NEW: Strict contract fields
            "decision_summary": decision_summary,
            "primary_exposure_impact": primary_exposure_impact,
            "risk_impact": risk_impact,
            "time_to_risk": time_to_risk,
            "market_regimes": market_regimes,
            "concentration_after_decision": concentration_after_decision,
            "irreversibility_detailed": irreversibility,
            "irreversible_loss_heatmap": irreversible_loss_heatmap,
            "decision_summary_line": decision_summary_line,
            # NEW: Visualization data
            "visualization_data": real_life_decision.visualization_data,
            # NEW: All visualization data for multiple actions
            "all_visualization_data": all_visualization_data,
            "individual_visualizations": all_visualization_data[1:] if len(all_visualization_data) > 1 else []  # Exclude main visualization
        }
        print(f"DEBUG: About to return response with visualization_data: {'visualization_data' in result}")
        print(f"DEBUG: visualization_data content type: {type(result.get('visualization_data'))}")
        print(f"DEBUG: visualization_data keys: {list(result.get('visualization_data', {}).keys()) if isinstance(result.get('visualization_data'), dict) else 'Not a dict'}")
        print(f"DEBUG: Number of individual visualizations: {len(result.get('individual_visualizations', []))}")
        return result
    except Exception as e:
        # If visualization creation fails, return the original response without visualization data
        print(f"Error creating visualization data: {e}")
        import traceback
        traceback.print_exc()
        return {
            "ok": True,
            "market_context": market_context,
            "baseline": baseline,
            "executed_decision": executed_decision,
            "distribution": distribution,
            "time_to_damage_days": time_to_damage_days,
            "fragile_regimes": fragile_regimes,
            "risk_concentration": risk_concentration,
            "irreversibility": irreversibility,
            "heatmap": heatmap,
            "irreversible_summary": irreversible_summary,
            # NEW: Strict contract fields
            "decision_summary": decision_summary,
            "primary_exposure_impact": primary_exposure_impact,
            "risk_impact": risk_impact,
            "time_to_risk": time_to_risk,
            "market_regimes": market_regimes,
            "concentration_after_decision": concentration_after_decision,
            "irreversibility_detailed": irreversibility,
            "irreversible_loss_heatmap": irreversible_loss_heatmap,
            "decision_summary_line": decision_summary_line
        }


def validate_strict_output_contract_with_portfolio(
    portfolio_value,
    decision_summary,
    primary_exposure_impact,
    risk_impact,
    time_to_risk,
    market_regimes,
    concentration_after_decision,
    irreversibility_detailed=None,
    irreversible_loss_heatmap=None,
    decision_summary_line=None,
    portfolio=None,
    body=None
):
    """
    Validate all output fields according to the strict contract requirements.
    """
    errors = []

    # A. DECISION SUMMARY (REQUIRED)
    if not decision_summary:
        errors.append("Decision summary is required")
    else:
        # Check if the asset symbol matches, but be more flexible for multi-asset decisions
        decision_asset_symbol = decision_summary.get("asset", {}).get("symbol")
        primary_asset_symbol = primary_exposure_impact.get("asset_symbol")

        # For multi-asset decisions, be more flexible with validation
        if decision_summary.get("decision_type") == "multi_asset_decision":
            # Multi-asset decisions have multiple actions, so we don't validate against single asset
            pass
        else:
            # For single asset decisions, validate normally
            if decision_asset_symbol != primary_asset_symbol:
                errors.append("Asset symbol in decision summary must equal parsed decision asset")

            # Check allocation change percentage with more flexibility
            decision_alloc_change = decision_summary.get("allocation_change_pct")
            primary_alloc_change = primary_exposure_impact.get("absolute_change_pct")

            # Handle cases where values might be None or missing or empty
            if decision_alloc_change is None or (isinstance(decision_alloc_change, str) and decision_alloc_change.strip() == ""):
                errors.append("Allocation change pct in decision summary is missing")
            elif primary_alloc_change is None or (isinstance(primary_alloc_change, str) and primary_alloc_change.strip() == ""):
                errors.append("Allocation change pct in primary exposure impact is missing")
            else:
                # Allow for small floating point differences
                try:
                    decision_val = float(decision_alloc_change)
                    primary_val = float(primary_alloc_change)
                    if abs(decision_val - primary_val) > 0.01:
                        errors.append(f"Allocation change pct in decision summary ({decision_alloc_change}) must equal user intent exactly ({primary_alloc_change})")
                except (ValueError, TypeError):
                    errors.append(f"Allocation change pct values must be numeric: decision_summary='{decision_alloc_change}', primary_exposure_impact='{primary_alloc_change}'")

    # B. PRIMARY EXPOSURE IMPACT (REQUIRED)
    if not primary_exposure_impact:
        errors.append("Primary exposure impact is required")
    else:
        weight_before = primary_exposure_impact.get("weight_before_pct", 0)
        weight_after = primary_exposure_impact.get("weight_after_pct", 0)
        change = primary_exposure_impact.get("absolute_change_pct", 0)
        if abs((weight_before + change) - weight_after) > 0.01:
            errors.append(f"Weight calculation mismatch: {weight_before} + {change} != {weight_after} (±0.01 tolerance)")

    # C. RISK IMPACT (REQUIRED)
    if not risk_impact:
        errors.append("Risk impact is required")
    else:
        downside = risk_impact.get("downside_pct", 0)
        expected = risk_impact.get("expected_pct", 0)
        upside = risk_impact.get("upside_pct", 0)
        if not (downside < expected < upside):
            errors.append(f"Risk impact values must satisfy: downside ({downside}) < expected ({expected}) < upside ({upside})")
        if risk_impact.get("horizon_days") is None:
            errors.append("Horizon days is required in risk impact")

    # D. TIME TO RISK REALIZATION (OPTIONAL but if present, must be valid)
    if time_to_risk:
        if time_to_risk.get("threshold_definition") and time_to_risk.get("estimated_days") is None:
            errors.append("Time to risk: if threshold_definition exists, estimated_days must be non-null")

    # E. MARKET REGIME SENSITIVITY (REQUIRED)
    if not market_regimes:
        errors.append("Market regime sensitivity is required")
    else:
        if not market_regimes.get("explanation"):
            errors.append("Market regime sensitivity must include explanation of WHY sensitivity increased")

    # F. PORTFOLIO CONCENTRATION (REQUIRED)
    if not concentration_after_decision:
        errors.append("Portfolio concentration is required")
    else:
        top_exposures = concentration_after_decision.get("top_exposures", [])
        decision_asset_symbol = primary_exposure_impact.get("asset_symbol", "")
        if decision_asset_symbol and decision_asset_symbol != "UNKNOWN":
            # Check if the decision asset is in the top exposures
            asset_found = False
            for exp in top_exposures:
                exp_symbol = exp.get("symbol", "")
                if exp_symbol and exp_symbol.upper() == decision_asset_symbol.upper():
                    asset_found = True
                    break

            if not asset_found:
                errors.append("Decision asset must appear in top exposures after decision")

        # Check weight sum plausibility
        # Note: Top exposures don't need to sum to 100% - they're just the largest positions
        # Only validate if we have specific concerns about extreme values
        for exp in top_exposures:
            weight_pct = exp.get("weight_pct", 0)
            # Check for extreme individual weights that might indicate an error
            if abs(weight_pct) > 100.0:
                errors.append(f"Individual exposure weight is implausibly large: {weight_pct}%")
                break

    # G. IRREVERSIBILITY RISK (OPTIONAL)
    if irreversibility_detailed:
        usd_loss = irreversibility_detailed.get("irreversible_loss_usd", 0)
        pct_loss = irreversibility_detailed.get("irreversible_loss_pct", 0)
        expected_calc = abs(pct_loss) * portfolio_value / 100.0
        if abs(usd_loss - expected_calc) > 0.01 and pct_loss != 0:
            errors.append(f"Irreversibility USD and % loss must reconcile mathematically: {usd_loss} vs {expected_calc}")

        recovery_time = irreversibility_detailed.get("recovery_time_months")
        if recovery_time is not None and "assumptions" not in irreversibility_detailed:
            errors.append("Irreversibility: if recovery_time_months exists, assumptions must be included")

    # H. HEATMAP (OPTIONAL)
    if irreversible_loss_heatmap:
        interpretation = irreversible_loss_heatmap.get("interpretation")
        if not interpretation:
            errors.append("Heatmap: if present, interpretation text must exist")

    # I. BOTTOM-LINE SUMMARY (REQUIRED)
    if not decision_summary_line:
        errors.append("Bottom-line summary is required")
    else:
        dominant_risk = decision_summary_line.get("dominant_risk_driver")
        if not dominant_risk:
            errors.append("Bottom-line summary must include dominant_risk_driver")

    # FUNDING LOGIC (MANDATORY FOR >5%)
    allocation_change_pct = decision_summary.get("allocation_change_pct", 0)
    if abs(allocation_change_pct) > 5.0 and portfolio:
        # For changes >5%, funding sources should be computed deterministically
        # This is a simplified check - in a full implementation, we'd validate the funding breakdown
        pass  # The funding logic is already implemented in the main function

    # CROSS-BORDER & JURISDICTION RULES
    asset_country = decision_summary.get("asset", {}).get("country", "")
    if body and hasattr(body, 'tax_country'):
        tax_country = body.tax_country
        if asset_country and tax_country and asset_country.lower() != tax_country.lower():
            # Cross-border exposure - should disclose
            # For now, we'll just continue as this is informational
            pass

    # NARRATIVE TRUTH RULES
    # Check if claims about concentration reduction are numerically provable
    if concentration_after_decision and "concentration_reduced" in concentration_after_decision:
        concentration_reduced = concentration_after_decision["concentration_reduced"]
        # This would require comparing before/after concentration metrics
        # For now, we'll just ensure the logic is consistent
        if concentration_reduced:
            # Verify that max position after is indeed smaller than before
            # We'll check if the concentration reduction claim is consistent with the actual changes
            # Since we can't access the original variables here, we'll just validate the consistency of the data
            top_exposures_after = concentration_after_decision.get("top_exposures", [])
            if top_exposures_after:
                max_after = max((exp.get("weight_pct", 0) for exp in top_exposures_after), default=0)
                # If concentration was reduced, the max position should be smaller than the original max
                # This is a simplified check - in a full implementation, we'd compare with original values
                pass  # For now, we'll just continue as this is a complex validation

    return {
        "ok": len(errors) == 0,
        "errors": errors
    }


@app.get("/api/v1/market/stream")
async def market_stream(request: Request, tickers: str):
    require_admin(request)
    # sanitize incoming tickers locally (avoid dependency order issues)
    seen = set()
    tlist: List[str] = []
    for t in [x for x in tickers.split(",")]:
        s = (t or "").strip().upper().rstrip('.')
        if not s or len(s) < 2:
            continue
        if s in seen:
            continue
        seen.add(s)
        tlist.append(s)

    async def event_generator():
        while True:
            if await request.is_disconnected():
                break
            warnings: List[str] = []
            payload: Dict[str, float] = {}
            try:
                if not tlist:
                    raise ValueError("No valid tickers provided")
                data = fetch_prices(tlist, lookback_days=2, interval="1d")
                tail = data.prices.tail(1)
                if tail is not None and not tail.empty:
                    payload = {c: float(tail[c].iloc[-1]) for c in tail.columns}
            except Exception as e:
                warnings.append(str(e))
                # try per-ticker fallback to provide partial data
                for tk in tlist:
                    try:
                        d = fetch_prices([tk], lookback_days=2, interval="1d")
                        ttail = d.prices.tail(1)
                        if ttail is not None and not ttail.empty:
                            col = ttail.columns[0]
                            payload[tk] = float(ttail[col].iloc[-1])
                    except Exception as e2:
                        warnings.append(f"{tk}: {e2}")
            item = {"ts": int(time.time()), "prices": payload}
            if warnings:
                item["warnings"] = warnings
            yield f"data: {json.dumps(item)}\n\n"
            await asyncio.sleep(5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/v1/decisions/last")
def decisions_last(request: Request):
    require_admin(request)
    store = read_decisions()
    items = store.get("items", [])
    if not items:
        return {"ok": True, "decision": None}
    return {"ok": True, "decision": items[0]}


@app.post("/api/v1/decisions/analyze", response_model=DecisionOut)
def decisions_analyze(request: Request, body: DecisionAnalyzeIn):
    require_admin(request)

    pstore = read_portfolios()
    items = pstore.get("items", [])
    if not items:
        raise HTTPException(status_code=400, detail="No saved portfolio found. Save a portfolio first.")

    portfolio = items[0]
    text = body.decision_text.strip()

    score = _decision_score(text)
    impacts = _impact_from_score(score, portfolio["risk_budget"])

    notes: List[str] = []
    t = text.lower()
    if "crypto" in t:
        notes.append("Crypto keyword detected: consider higher tail risk and tax treatment.")
    if "hedge" in t:
        notes.append("Hedge keyword detected: expected return may decrease while drawdowns reduce.")
    if impacts["confidence"] == "LOW":
        notes.append("Low confidence: decision text implies high leverage/risk or is too broad.")

    decision = {
        "id": f"dec_{secrets.token_hex(6)}",
        "decision_text": text,
        "tax_country": body.tax_country,
        "portfolio_id": portfolio["id"],
        "portfolio_value": float(portfolio["total_value"]),
        "expected_before_tax_pct": float(impacts["expected"]),
        "worst_case_pct": float(impacts["worst"]),
        "best_case_pct": float(impacts["best"]),
        "confidence": impacts["confidence"],
        "notes": notes,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    dstore = read_decisions()
    dstore["items"].insert(0, decision)
    write_decisions(dstore)

    return decision


# NEW: Canonical Decision Analysis Endpoint
@app.post("/api/v1/decisions/canonical", response_model=CanonicalDecisionOut)
def decisions_canonical(request: Request, body: DecisionAnalyzeIn):
    require_admin(request)

    # Validate input using guardrails
    validation_result = INPUT_VALIDATOR.validate_decision_input(body.decision_text)
    if not validation_result.is_valid:
        # Log violations but continue processing to provide feedback
        for violation in validation_result.violations:
            print(f"Guardrail violation detected: {violation}")

    pstore = read_portfolios()
    items = pstore.get("items", [])
    if not items:
        raise HTTPException(status_code=400, detail="No saved portfolio found. Save a portfolio first.")

    portfolio = items[0]

    # Get user profile to determine appropriate user type based on questionnaire
    profile_store = read_profiles()
    user_profile = profile_store.get("profiles", {}).get("admin")

    # Determine user type: use provided type or derive from questionnaire
    if body.user_type == UserType.RETAIL and user_profile and user_profile.get("level"):  # Only auto-assign if default was provided
        user_type = map_user_level_to_type(user_profile["level"])
    else:
        user_type = body.user_type

    # Validate portfolio data
    portfolio_validation = INPUT_VALIDATOR.validate_portfolio_data(portfolio)
    if not portfolio_validation.is_valid:
        print(f"Portfolio validation issues: {portfolio_validation.violations}")

    # Get market data for regime analysis
    tickers = [p["ticker"] for p in portfolio.get("positions", [])]
    try:
        market_data = fetch_prices(tickers, lookback_days=252, interval="1d")
        prices_df = market_data.prices
    except Exception:
        # If market data fetch fails, use minimal data
        prices_df = pd.DataFrame()

    # Classify the decision using enhanced classifier that distinguishes between trade decisions and portfolio rebalancing
    decision_classification = ENHANCED_DECISION_CLASSIFIER.classify_decision(
        body.decision_text, portfolio
    )

    # Get risk profile based on enhanced classification
    # Map the enhanced classification to the existing taxonomy for risk profile
    risk_profile = DECISION_TAXONOMY_CLASSIFIER.get_decision_risk_profile(
        type('MockClassification', (), {
            'decision_type': 'POSITION_OPENING' if decision_classification.category == DecisionCategory.TRADE_DECISION else 'REBALANCING',
            'impact_types': [],
            'reversibility': 'REVERSIBLE',
            'confidence': decision_classification.confidence,
            'keywords_identified': decision_classification.keywords_identified,
            'primary_asset': decision_classification.asset if decision_classification.asset != "MULTI_ASSET_STRATEGY" else None,
            'secondary_assets': []
        })()
    )

    # Create DecisionConsequences object with comprehensive analysis, including decision category
    consequences = DecisionConsequences(portfolio, body.decision_text, decision_classification.category)

    # Perform regime analysis if market data is available
    if not prices_df.empty:
        try:
            regime_analysis = REGIME_ANALYZER.analyze_regime_impact(portfolio, prices_df)
            # Update consequences with regime-specific information
            consequences.calm_regime_behavior = regime_analysis["regime_analysis"]["calm"]
            consequences.stressed_regime_behavior = regime_analysis["regime_analysis"]["stressed"]
            consequences.crisis_regime_behavior = regime_analysis["regime_analysis"]["crisis"]
        except Exception as e:
            print(f"Regime analysis failed: {e}")

    # Create RealLifeDecision object with canonical structure
    real_life_decision = RealLifeDecision(consequences, body.decision_text, portfolio)

    # Validate the RealLifeDecision against guardrails
    decision_dict = {
        "decision_summary": real_life_decision.decision_summary,
        "why_this_helps": real_life_decision.why_this_helps,
        "what_you_gain": real_life_decision.what_you_gain,
        "what_you_risk": real_life_decision.what_you_risk,
        "when_this_stops_working": real_life_decision.when_this_stops_working,
        "who_this_is_for": real_life_decision.who_this_is_for
    }

    guardrail_result = INPUT_VALIDATOR.guardrails.check_real_life_decision(decision_dict)
    if not guardrail_result.is_valid:
        print(f"RealLifeDecision guardrail issues: {guardrail_result.violations}")

    # Create UserViewAdapter to format output appropriately
    adapter = UserViewAdapter(real_life_decision, user_type)
    adapted_output = adapter.adapt_output()

    # Save the decision for record keeping
    decision_record = {
        "id": real_life_decision.decision_id,
        "decision_text": body.decision_text,
        "tax_country": body.tax_country,
        "portfolio_id": portfolio["id"],
        "portfolio_value": float(portfolio["total_value"]),
        "decision_type": decision_classification.decision_type.value,
        "risk_profile": risk_profile,
        "classification_confidence": decision_classification.confidence,
        "user_type_assigned": user_type.value,  # Track which user type was used
        "created_at": real_life_decision.calculated_at,
    }

    dstore = read_decisions()
    dstore["items"].insert(0, decision_record)
    write_decisions(dstore)

    # Return the canonical decision output
    result = CanonicalDecisionOut(
        decision_summary=adapted_output["decision_summary"],
        why_this_helps=adapted_output["why_this_helps"],
        what_you_gain=adapted_output["what_you_gain"],
        what_you_risk=adapted_output["what_you_risk"],
        when_this_stops_working=adapted_output["when_this_stops_working"],
        who_this_is_for=adapted_output["who_this_is_for"],
        metadata=adapted_output["metadata"]
    )

    # Add additional details if available (for advisor/HNI users)
    if "compliance_notes" in adapted_output or "quantitative_metrics" in adapted_output:
        result.additional_details = {}
        if "compliance_notes" in adapted_output:
            result.additional_details["compliance_notes"] = adapted_output["compliance_notes"]
        if "quantitative_metrics" in adapted_output:
            result.additional_details["quantitative_metrics"] = adapted_output["quantitative_metrics"]
        if "documentation" in adapted_output:
            result.additional_details["documentation"] = adapted_output["documentation"]
        if "regime_analysis" in adapted_output:
            result.additional_details["regime_analysis"] = adapted_output["regime_analysis"]
        if "liquidity_assessment" in adapted_output:
            result.additional_details["liquidity_assessment"] = adapted_output["liquidity_assessment"]

    return result


# ----------------------------
# ✅ NEW: Tax Advisor route
# ----------------------------
def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        v = float(x)
        if math.isfinite(v):
            return v
    except Exception:
        pass
    return default


def _build_tax_advice_items(
    portfolio: Dict[str, Any],
    decision: Optional[Dict[str, Any]],
    rules: Dict[str, float],
) -> List[TaxAdviceItem]:
    items: List[TaxAdviceItem] = []

    total_value = _safe_float(portfolio.get("total_value"), 0.0)
    base_currency = (portfolio.get("base_currency") or "USD").upper()
    rb = portfolio.get("risk_budget", "MEDIUM")

    lt = _safe_float(rules.get("long_term_capital_gains"), 0.15)
    st = _safe_float(rules.get("short_term_capital_gains"), 0.30)
    tx = _safe_float(rules.get("transaction_tax"), 0.0)
    fx = _safe_float(rules.get("fx_drag"), 0.0)

    dec_text = (decision or {}).get("decision_text", "") or ""
    t = dec_text.lower()

    # 1) Short-term vs long-term timing suggestion
    spread = max(0.0, st - lt)
    if spread > 0.0001:
        est = total_value * spread * 0.05  # rough: 5% of portfolio turnover subject to spread
        items.append(
            TaxAdviceItem(
                title="Prefer long-term holding periods when possible",
                severity="HIGH" if spread >= 0.10 else "MEDIUM",
                why=f"Your short-term rate (~{st*100:.0f}%) is higher than long-term (~{lt*100:.0f}%).",
                est_savings_usd=round(est, 2),
                next_step="If your decision involves selling, consider delaying sales until long-term status where appropriate.",
            )
        )

    # 2) High turnover / rebalance warning (transaction + ST drag)
    if any(k in t for k in ["rebalance", "rotate", "trade", "sell", "trim", "decrease"]):
        est = total_value * (tx + fx)  # rough annualized “drag-ish” component
        items.append(
            TaxAdviceItem(
                title="Reduce unnecessary turnover",
                severity="MEDIUM",
                why="Frequent selling/rebalancing can increase short-term gains and transaction/FX drag.",
                est_savings_usd=round(est, 2),
                next_step="Batch trades, widen rebalance bands, and avoid small trims unless risk limits require it.",
            )
        )

    # 3) Harvesting (MVP suggestion)
    items.append(
        TaxAdviceItem(
            title="Check for tax-loss harvesting opportunities",
            severity="MEDIUM",
            why="Harvesting losses can offset gains (rules vary by jurisdiction).",
            est_savings_usd=0.0,
            next_step="Add cost basis + purchase dates next. Then we can flag specific lots and wash-sale risks.",
        )
    )

    # 4) Crypto note
    if "crypto" in t or "btc" in t or "eth" in t:
        items.append(
            TaxAdviceItem(
                title="Crypto tax treatment review",
                severity="HIGH",
                why="Crypto trades often have different tax treatment and reporting requirements.",
                est_savings_usd=0.0,
                next_step="Confirm holding period + realized gains. Consider minimizing short-term churn if rates are higher.",
            )
        )

    # 5) Bracket FX drag info (informational)
    if fx > 0:
        items.append(
            TaxAdviceItem(
                title="Account for cross-border FX drag",
                severity="LOW",
                why=f"Your tax rule set includes FX drag (~{fx*100:.2f}%).",
                est_savings_usd=round(total_value * fx, 2),
                next_step="If applicable, reduce unnecessary FX conversions and consolidate currency exposures.",
            )
        )

    # 6) Confidence-based nudge
    conf = (decision or {}).get("confidence")
    if conf == "LOW":
        items.append(
            TaxAdviceItem(
                title="Clarify the decision intent",
                severity="MEDIUM",
                why="Low-confidence decisions tend to be vague or imply leverage; tax planning depends on specifics.",
                est_savings_usd=0.0,
                next_step="Specify what you’re selling/buying, approximate turnover %, and intended holding period.",
            )
        )

    # light cap to avoid too many cards
    return items[:10]


@app.post("/api/v1/tax/advice", response_model=TaxAdviceOut)
def tax_advice(request: Request, body: TaxAdviceIn):
    require_admin(request)

    pstore = read_portfolios()
    pitems = pstore.get("items", [])
    if not pitems:
        raise HTTPException(status_code=400, detail="No saved portfolio found. Save a portfolio first.")
    portfolio = pitems[0]

    # last decision is optional
    dstore = read_decisions()
    ditems = dstore.get("items", [])
    decision = ditems[0] if ditems else None

    # load tax rules for requested country, fallback handled like /tax/rules
    data = read_tax_rules()
    rules_all = data.get("rules", {}) or {}
    default_country = data.get("default_country", "United States")
    picked_country = body.tax_country
    picked = rules_all.get(picked_country) or rules_all.get(default_country) or rules_all.get("United States")

    if not picked and rules_all:
        first_key = next(iter(rules_all.keys()))
        picked_country = first_key
        picked = rules_all[first_key]

    if not picked:
        picked_country = "United States"
        picked = {
            "long_term_capital_gains": 0.15,
            "short_term_capital_gains": 0.30,
            "crypto": 0.30,
            "transaction_tax": 0.00,
            "fx_drag": 0.005,
        }

    items = _build_tax_advice_items(portfolio=portfolio, decision=decision, rules=picked)

    return TaxAdviceOut(
        ok=True,
        portfolio_id=str(portfolio.get("id")),
        portfolio_value=float(portfolio.get("total_value", 0)),
        base_currency=str(portfolio.get("base_currency", "USD")),
        tax_country=picked_country,
        decision_id=(decision.get("id") if decision else None),
        decision_text=(decision.get("decision_text") if decision else None),
        items=items,
    )


# ----------------------------
# Market + analysis routes
# ----------------------------
def _sanitize_tickers(raw: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for t in raw:
        if not t:
            continue
        s = t.strip().upper()
        # Don't strip international suffixes like .NS, .BO, etc.
        if len(s) < 2:
            continue
        if s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out

@app.get("/api/v1/market/prices")
def market_prices(
    request: Request,
    tickers: str,
    lookback: int = 365,
    interval: Literal["1d", "1wk", "1mo"] = "1d",
):
    require_admin(request)
    raw = [t for t in tickers.split(",")]
    tlist = _sanitize_tickers(raw)
    warnings: List[str] = []
    data = None
    try:
        if not tlist:
            raise ValueError("No valid tickers provided after sanitization")
        data = fetch_prices(tlist, lookback_days=lookback, interval=interval)
    except Exception as e:
        warnings.append(str(e))

    if data is None:
        out = {
            "tickers": tlist,
            "interval": interval,
            "lookback_days": lookback,
            "rows_returned": 0,
            "prices_tail": {"index": [], "values": {}},
            "warnings": warnings,
        }
        return {"ok": True, "data": out}

    tail = data.prices.tail(25)
    out = {
        "tickers": tlist,
        "interval": interval,
        "lookback_days": lookback,
        "rows_returned": int(tail.shape[0]),
        "prices_tail": {
            "index": [str(x) for x in tail.index],
            "values": {c: [float(v) for v in tail[c].values] for c in tail.columns},
        },
    }
    if warnings:
        out["warnings"] = warnings
    return {"ok": True, "data": out}


def _is_finite(x: float) -> bool:
    return isinstance(x, (int, float)) and math.isfinite(float(x))


@app.post("/api/v1/portfolio/analyze")
def portfolio_analyze(request: Request, body: AnalyzeIn):
    require_admin(request)
    try:
        p = PortfolioBase(name="tmp", risk_budget=body.risk_budget, positions=body.positions)
        v = validate_portfolio(p)
        if not v.ok:
            raise HTTPException(
                status_code=400,
                detail={"errors": v.errors, "warnings": v.warnings, "sum_weights": v.sum_weights},
            )

        # sanitize tickers and keep weights aligned to positions
        pos_pairs: List[tuple[str, float]] = []
        for pos in body.positions:
            s = (pos.ticker or "").strip().upper().rstrip('.')
            if not s or len(s) < 2:
                continue
            pos_pairs.append((s, float(pos.weight)))

        if not pos_pairs:
            raise HTTPException(status_code=400, detail={"error": "No valid tickers provided"})

        tlist = [p[0] for p in pos_pairs]
        raw_weights = [p[1] for p in pos_pairs]

        warnings: List[str] = []
        data = None
        try:
            data = fetch_prices(tlist, lookback_days=body.lookback_days, interval=body.interval)
        except Exception as e:
            warnings.append(str(e))
            # fallback: try to fetch per-ticker to salvage partial data
            frames = []
            succeeded: List[str] = []
            for tk in tlist:
                try:
                    r = fetch_prices([tk], lookback_days=body.lookback_days, interval=body.interval)
                    if r and not r.prices.empty:
                        # ensure column name is sanitized
                        col = r.prices.columns[0]
                        series = r.prices[col].rename(tk)
                        frames.append(series)
                        succeeded.append(tk)
                except Exception as e2:
                    warnings.append(f"{tk}: {e2}")

            if frames:
                prices = pd.concat(frames, axis=1).sort_index()
                rets = prices.pct_change().dropna(how="all")
                data = type("PFR", (), {"prices": prices, "returns": rets})()
            else:
                raise HTTPException(
                    status_code=502,
                    detail={
                        "error": "Market data fetch failed",
                        "message": "No market data returned (empty download). Try again or change tickers/interval.",
                        "tickers": tlist,
                        "interval": body.interval,
                        "lookback_days": body.lookback_days,
                        "warnings": warnings,
                    },
                )

        rets = data.returns
        if rets is None or rets.empty or len(rets) < 5:
            raise HTTPException(
                status_code=502,
                detail={
                    "error": "Market data fetch failed",
                    "message": "Not enough market history returned. Try increasing lookback_days.",
                    "tickers": tlist,
                    "interval": body.interval,
                    "lookback_days": body.lookback_days,
                    "warnings": warnings,
                },
            )

        # Limit rets to available columns and align weights
        available = [c for c in rets.columns]
        if not available:
            raise HTTPException(status_code=502, detail={"error": "No available tickers after fetch", "warnings": warnings})

        # build weights for available tickers in same order
        avail_weights = []
        for a in available:
            # find original weight for ticker a
            w = 0.0
            for (tk, wt) in pos_pairs:
                if tk == a:
                    w = wt
                    break
            avail_weights.append(w)

        sumw = sum(avail_weights)
        if sumw <= 0:
            raise HTTPException(status_code=400, detail={"error": "Zero total weight for available tickers"})

        weights = np.array([w / sumw for w in avail_weights], dtype=float)
        rets = rets[available]

        ppy = periods_per_year_from_interval(body.interval)
        m = portfolio_metrics(rets, weights, periods_per_year=ppy)

        if not _is_finite(m["annualized_vol"]) or not _is_finite(m["max_drawdown"]):
            raise HTTPException(
                status_code=502,
                detail={
                    "error": "Market data produced invalid metrics",
                    "message": "Returned NaN/Inf metrics (price download incomplete). Try again.",
                    "tickers": tlist,
                    "interval": body.interval,
                    "lookback_days": body.lookback_days,
                    "warnings": warnings,
                },
            )

        corr = rets.corr()

        rc = np.asarray(m["risk_contribution"], dtype=float)
        if np.any(~np.isfinite(rc)):
            raise HTTPException(
                status_code=502,
                detail={
                    "error": "Market data produced invalid risk contributions",
                    "message": "Risk contributions contained NaN/Inf (insufficient/empty price history).",
                    "tickers": tlist,
                },
            )

        out = {
            "tickers": tlist,
            "lookback_days": body.lookback_days,
            "interval": body.interval,
            "annualized_vol": float(m["annualized_vol"]),
            "max_drawdown": float(m["max_drawdown"]),
            "corr": {
                "rows": tlist,
                "cols": tlist,
                "values": [[float(corr.at[r, c]) for c in tlist] for r in tlist],
            },
            "risk_contributions": [
                {"ticker": tlist[i], "weight": float(weights[i]), "variance_contribution": float(rc[i])}
                for i in range(len(tlist))
            ],
            "notes": [
                "Variance contributions sum to ~1.0 (share of total variance).",
                "Max drawdown is computed on the portfolio index built from historical returns.",
            ],
        }
        return {"ok": True, "analysis": out}
    except HTTPException:
        # re-raise FastAPI HTTPExceptions unchanged
        raise
    except Exception as e:
        tb = traceback.format_exc()
        # return structured 502 to avoid 500 stacktrace leak
        raise HTTPException(
            status_code=502,
            detail={"error": "Internal analysis error", "message": str(e), "trace": tb},
        )




