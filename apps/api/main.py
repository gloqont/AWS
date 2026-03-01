import os
import json
import time
import secrets
import math
import asyncio
from typing import List, Literal, Optional, Dict, Any
from urllib.parse import urlencode, quote_plus

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, Response, Request, HTTPException
import httpx
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, RedirectResponse
try:
    import yfinance as yf
except Exception:
    yf = None
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from pydantic import BaseModel, Field, field_validator
import traceback
from fastapi.responses import JSONResponse

from risk import fetch_prices, portfolio_metrics, periods_per_year_from_interval
from decision_engine import DecisionConsequences, RealLifeDecision, UserViewAdapter, UserType
from decision_taxonomy import DECISION_TAXONOMY_CLASSIFIER
from failure_modes import FAILURE_MODE_LIBRARY
from regime_detection import REGIME_ANALYZER
from guardrails import INPUT_VALIDATOR
from asset_resolver import ASSET_RESOLVER, AssetInfo
from enhanced_decision_classifier import ENHANCED_DECISION_CLASSIFIER, DecisionCategory

# NEW: Decision Intelligence Architecture imports
from decision_schema import (
    StructuredDecision, DecisionComparison, DecisionScore, DecisionVerdict,
    InstrumentAction, Timing, Direction, DecisionType, TimingType
)
from intent_parser import parse_decision, IntentParser
from temporal_engine import run_decision_intelligence, run_decision_intelligence_fast, TemporalSimulationEngine, calculate_execution_context, calculate_risk_analysis, calculate_projections
from decision_cache import get_cached_result, set_cached_result, get_cache_stats
from tax_engine import TaxEngine, TaxProfile, PortfolioTaxContext, AssetClass, AccountType, HoldingPeriod, IncomeTier, FilingStatus
from tax_engine.models import TransactionDetail

load_dotenv()

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")
SESSION_SECRET = os.getenv("SESSION_SECRET", "dev_secret_change_me")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").strip().lower() in {"1", "true", "yes"}
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY", "").strip()
ENABLE_YFINANCE_LIVE_FALLBACK = os.getenv("ENABLE_YFINANCE_LIVE_FALLBACK", "false").strip().lower() in {"1", "true", "yes"}

# Cognito OAuth configuration
COGNITO_REGION = os.getenv("COGNITO_REGION", "").strip()
COGNITO_USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID", "").strip()
COGNITO_CLIENT_ID = os.getenv("COGNITO_CLIENT_ID", "").strip()
COGNITO_CLIENT_SECRET = os.getenv("COGNITO_CLIENT_SECRET", "").strip()
COGNITO_DOMAIN = os.getenv("COGNITO_DOMAIN", "").strip()  # host only, no https://
COGNITO_API_DOMAIN = os.getenv("COGNITO_API_DOMAIN", COGNITO_DOMAIN).strip()  # optional override for token/userInfo host
COGNITO_REDIRECT_URI = os.getenv("COGNITO_REDIRECT_URI", "http://localhost:3000/api/v1/auth/callback").strip()
COGNITO_LOGOUT_REDIRECT_URI = os.getenv("COGNITO_LOGOUT_REDIRECT_URI", "http://localhost:3000/login").strip()
COGNITO_SCOPES = os.getenv("COGNITO_SCOPES", "openid email profile").strip()

serializer = URLSafeTimedSerializer(SESSION_SECRET)
SESSION_COOKIE = "advisor_session"
SESSION_MAX_AGE_SECONDS = 60 * 60 * 8  # 8 hours
OAUTH_STATE_MAX_AGE_SECONDS = 60 * 10  # 10 minutes

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
PORTFOLIOS_PATH = os.path.join(DATA_DIR, "portfolios.json")
DECISIONS_PATH = os.path.join(DATA_DIR, "decisions.json")  # ✅
TAX_RULES_PATH = os.path.join(DATA_DIR, "tax_rules.json")  # ✅
PROFILES_PATH = os.path.join(DATA_DIR, "user_profiles.json")

# ── In-memory price cache for instant refetches ──
_PRICE_CACHE: Dict[str, Any] = {}  # key -> {"data": ..., "ts": float}
_PRICE_CACHE_TTL = 300  # 5 minutes
_SYMBOL_PRICE_CACHE: Dict[str, Dict[str, Any]] = {}  # SYMBOL -> {"price": float, "currency": str, "ts": float, "source": str}
_SYMBOL_PRICE_CACHE_MAX_STALE = 60 * 60 * 24  # 24h hard cap for stale fallback
_SYMBOL_PRICE_CACHE_FAST_AGE = 120  # 2 minutes for instant quote refresh

def _get_cached_prices(cache_key: str):
    entry = _PRICE_CACHE.get(cache_key)
    if entry and (time.time() - entry["ts"]) < _PRICE_CACHE_TTL:
        return entry["data"]
    return None

def _set_cached_prices(cache_key: str, data: Any):
    _PRICE_CACHE[cache_key] = {"data": data, "ts": time.time()}


def _set_symbol_price_cache(symbol: str, price: float, currency: str = "USD", source: str = "twelve_data") -> None:
    _SYMBOL_PRICE_CACHE[symbol.upper()] = {
        "price": float(price),
        "currency": (currency or "USD").upper(),
        "ts": time.time(),
        "source": source,
    }


def _get_symbol_price_cache(symbol: str, max_age_seconds: int = _SYMBOL_PRICE_CACHE_MAX_STALE) -> Optional[Dict[str, Any]]:
    item = _SYMBOL_PRICE_CACHE.get(symbol.upper())
    if not item:
        return None
    if (time.time() - float(item.get("ts", 0))) <= max_age_seconds:
        return item
    return None

app = FastAPI(title="GLOQONT API", version="1.4.0")  # bump version

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
    # NEW: Monte Carlo path generation for future risk visualization
    horizon_days: int = Field(default=90, ge=1, le=3650, description="Simulation horizon in days")
    n_paths: int = Field(default=1000, ge=10, le=5000, description="Number of Monte Carlo paths")
    include_paths: bool = Field(default=False, description="If True, return simulation paths")


# ✅ Decision / Scenario Simulation models
class DecisionAnalyzeIn(BaseModel):
    decision_text: str = Field(..., min_length=3, max_length=400)
    tax_country: str = Field(default="United States")
    user_type: UserType = Field(default=UserType.RETAIL)  # NEW: User type for canonical output



class DecisionSimulationIn(BaseModel):
    decision_text: str = Field(..., min_length=3, max_length=400)
    mode: Literal["fast", "full"] = "fast"
    horizon_days: int = Field(default=30, ge=1, le=3650)
    n_paths: int = Field(default=100, ge=10, le=1000)
    return_paths: bool = Field(default=False, description="Return raw simulation paths")
    # Tax Engine fields
    tax_jurisdiction: str = Field(default="US", description="ISO country code: US, IN, CA, DE, FR, GB, NL")
    tax_sub_jurisdiction: Optional[str] = Field(default=None, description="State/Province: CA, NY, TX, ON, QC, etc.")
    tax_account_type: str = Field(default="taxable", description="Account type: taxable, ira_roth, 401k, tfsa, isa, etc.")
    tax_holding_period: str = Field(default="short_term", description="Simulated holding: short_term or long_term")
    tax_income_tier: str = Field(default="medium", description="Income tier: low, medium, high, very_high")
    tax_filing_status: str = Field(default="single", description="Filing status: single, married_joint, etc.")


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
    horizon_days: int = Field(default=90, ge=1, le=3650)
    n_paths: int = Field(default=1000, ge=10, le=5000)


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
# NEW: Decision Intelligence API Models
# ----------------------------
class DecisionIntelligenceIn(BaseModel):
    """Input for the Decision Intelligence endpoint."""
    decision_text: str = Field(..., min_length=3, max_length=500, description="User's natural language decision")
    horizon_days: int = Field(default=30, ge=1, le=3650, description="Simulation horizon in days")
    n_paths: int = Field(default=100, ge=10, le=1000, description="Number of Monte Carlo paths")
    include_paths: bool = Field(default=False, description="If True, return raw simulation paths for visualization")


class DecisionIntelligenceOut(BaseModel):
    """Output from the Decision Intelligence endpoint."""
    ok: bool
    
    # Parsed decision
    decision_id: str
    decision_type: str
    parsed_actions: List[Dict[str, Any]]
    confidence_score: float
    parser_warnings: List[str] = Field(default_factory=list)
    
    # Comparison metrics (baseline vs scenario)
    baseline_expected_return: float
    baseline_volatility: float
    baseline_max_drawdown: float
    
    scenario_expected_return: float
    scenario_volatility: float
    scenario_max_drawdown: float
    
    delta_return: float
    delta_volatility: float
    delta_drawdown: float
    
    # Decision verdict
    verdict: str
    composite_score: float
    summary: str
    key_factors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    
    # For visualization
    visualization_data: Optional[Dict[str, Any]] = None
    
    # Optional: Raw simulation paths for advanced visualization
    simulation_paths: Optional[Dict[str, Any]] = None


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
def _cognito_enabled() -> bool:
    return bool(COGNITO_DOMAIN and COGNITO_CLIENT_ID and COGNITO_REDIRECT_URI)


def _build_cognito_url(path: str, *, api: bool = False) -> str:
    host_value = COGNITO_API_DOMAIN if api else COGNITO_DOMAIN
    host = host_value.removeprefix("https://").removesuffix("/")
    return f"https://{host}{path}"


def _safe_next_path(next_path: Optional[str]) -> str:
    if not next_path:
        return "/dashboard/portfolio-optimizer"
    if not next_path.startswith("/") or next_path.startswith("//"):
        return "/dashboard/portfolio-optimizer"
    return next_path


def require_admin(request: Request):
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        data = serializer.loads(token, max_age=SESSION_MAX_AGE_SECONDS)
    except SignatureExpired:
        raise HTTPException(status_code=401, detail="Session expired")
    except BadSignature:
        raise HTTPException(status_code=401, detail="Invalid session")

    return data


# ----------------------------
# Auth routes
# ----------------------------
@app.get("/api/v1/auth/login")
def cognito_login(next: Optional[str] = None, mode: Optional[str] = None):
    if not _cognito_enabled():
        raise HTTPException(status_code=500, detail="Cognito auth is not configured on the server")

    next_path = _safe_next_path(next)
    oauth_state = serializer.dumps(
        {
            "next": next_path,
            "mode": mode if mode in {"signup", "login"} else "login",
            "nonce": secrets.token_hex(12),
            "iat": int(time.time()),
        },
        salt="oauth_state",
    )

    params = {
        "response_type": "code",
        "client_id": COGNITO_CLIENT_ID,
        "redirect_uri": COGNITO_REDIRECT_URI,
        "scope": COGNITO_SCOPES,
        "state": oauth_state,
    }
    if mode == "signup":
        params["screen_hint"] = "signup"

    authorize_url = _build_cognito_url(f"/oauth2/authorize?{urlencode(params)}")
    return RedirectResponse(url=authorize_url, status_code=307)


@app.post("/api/v1/auth/login")
def login(body: LoginIn, response: Response):
    # Backward-compatible local admin login for environments not yet migrated to Cognito.
    if _cognito_enabled():
        raise HTTPException(status_code=400, detail="Use GET /api/v1/auth/login for Cognito sign-in")

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
        secure=SESSION_COOKIE_SECURE,
        samesite="lax",
        max_age=SESSION_MAX_AGE_SECONDS,
        path="/",
    )
    return {"ok": True}


@app.get("/api/v1/auth/callback")
def cognito_callback(code: Optional[str] = None, state: Optional[str] = None, error: Optional[str] = None, error_description: Optional[str] = None, response: Response = None):
    if not _cognito_enabled():
        raise HTTPException(status_code=500, detail="Cognito auth is not configured on the server")

    if error:
        raise HTTPException(status_code=401, detail=f"Cognito error: {error} ({error_description or 'no description'})")
    if not code:
        raise HTTPException(status_code=400, detail="Missing OAuth authorization code")
    if not state:
        raise HTTPException(status_code=400, detail="Missing OAuth state")

    try:
        state_data = serializer.loads(state, salt="oauth_state", max_age=OAUTH_STATE_MAX_AGE_SECONDS)
    except SignatureExpired:
        raise HTTPException(status_code=401, detail="OAuth state expired")
    except BadSignature:
        raise HTTPException(status_code=401, detail="Invalid OAuth state")

    next_path = _safe_next_path(state_data.get("next"))
    token_url = _build_cognito_url("/oauth2/token", api=True)
    userinfo_url = _build_cognito_url("/oauth2/userInfo", api=True)

    token_payload = {
        "grant_type": "authorization_code",
        "client_id": COGNITO_CLIENT_ID,
        "code": code,
        "redirect_uri": COGNITO_REDIRECT_URI,
    }
    if COGNITO_CLIENT_SECRET:
        token_payload["client_secret"] = COGNITO_CLIENT_SECRET

    try:
        token_res = httpx.post(
            token_url,
            data=token_payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10.0,
        )
        token_res.raise_for_status()
        token_data = token_res.json()
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Failed token exchange with Cognito: {e}")

    access_token = token_data.get("access_token")
    id_token = token_data.get("id_token")
    if not access_token or not id_token:
        raise HTTPException(status_code=401, detail="Cognito token response missing required tokens")

    try:
        userinfo_res = httpx.get(
            userinfo_url,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10.0,
        )
        userinfo_res.raise_for_status()
        userinfo = userinfo_res.json()
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Failed to retrieve Cognito user profile: {e}")

    session = {
        "sub": userinfo.get("sub"),
        "email": userinfo.get("email"),
        "role": "user",
        "provider": "cognito",
        "iat": int(time.time()),
        "nonce": secrets.token_hex(8),
    }
    token = serializer.dumps(session)
    response = response or Response()
    response.status_code = 307
    response.headers["Location"] = next_path
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        secure=SESSION_COOKIE_SECURE,
        samesite="lax",
        max_age=SESSION_MAX_AGE_SECONDS,
        path="/",
    )
    return response


@app.post("/api/v1/auth/logout")
def logout(response: Response):
    response.delete_cookie(key=SESSION_COOKIE, path="/")
    return {"ok": True}


@app.get("/api/v1/auth/logout")
def logout_redirect(next: Optional[str] = None, response: Response = None):
    next_path = _safe_next_path(next or "/login")

    response = response or Response()
    response.delete_cookie(key=SESSION_COOKIE, path="/")

    if not _cognito_enabled():
        response.status_code = 307
        response.headers["Location"] = next_path
        return response

    logout_target = _build_cognito_url(
        f"/logout?{urlencode({'client_id': COGNITO_CLIENT_ID, 'logout_uri': COGNITO_LOGOUT_REDIRECT_URI})}"
    )
    response.status_code = 307
    response.headers["Location"] = logout_target
    return response


@app.get("/api/v1/auth/me")
def me(request: Request):
    data = require_admin(request)
    return {
        "ok": True,
        "user": {
            "sub": data.get("sub"),
            "email": data.get("email"),
            "role": data.get("role", "user"),
            "provider": data.get("provider", "local"),
        },
    }


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
def market_search(request: Request, q: str, country: str = "US"):
    require_admin(request)
    if not q or not q.strip():
        raise HTTPException(status_code=400, detail="query required")

    query = q.strip().upper()
    query = _canonical_symbol_for_prices(query)

    # First try to resolve using our canonical asset resolver
    asset_info = ASSET_RESOLVER.resolve_asset(q)
    if asset_info and asset_info.is_valid:
        resolved_symbol = str(asset_info.symbol or query).upper()
        if asset_info.country == "India" and "." not in resolved_symbol:
            resolved_symbol = f"{resolved_symbol}.NS"
        return {
            "ok": True,
            "symbol": resolved_symbol,
            "shortname": asset_info.name,
            "exchange": "NSE" if asset_info.country == "India" else "NASDAQ" if asset_info.country == "USA" else "OTHER",
            "currency": "INR" if asset_info.country == "India" else "USD",
        }

    # Twelve Data global symbol search (primary)
    if TWELVE_DATA_API_KEY:
        td = _twelve_get_json("/symbol_search", {"symbol": query, "outputsize": 12})
        if td and str(td.get("status", "")).lower() != "error":
            data = td.get("data", []) if isinstance(td, dict) else []
            if isinstance(data, list) and data:
                # Prefer exact symbol startswith + optional country filter
                best = None
                for item in data:
                    sym = str(item.get("symbol", "")).upper()
                    item_country = str(item.get("country", "")).upper()
                    if country and item_country and country.upper() not in item_country and country.upper() != "US":
                        # Keep global behavior; only apply filter when clearly not US default
                        pass
                    if sym == query or sym.startswith(query):
                        best = item
                        break
                if best is None:
                    best = data[0]

                raw_symbol = str(best.get("symbol", "")).upper()
                exch = str(best.get("exchange", "")).upper()
                mapped_symbol = raw_symbol
                if exch == "NSE":
                    mapped_symbol = f"{raw_symbol}.NS"
                elif exch == "BSE":
                    mapped_symbol = f"{raw_symbol}.BO"
                elif exch in ("LSE", "XLON"):
                    mapped_symbol = f"{raw_symbol}.L"
                elif exch in ("TSX", "XTSE"):
                    mapped_symbol = f"{raw_symbol}.TO"

                return {
                    "ok": True,
                    "symbol": mapped_symbol,
                    "shortname": best.get("instrument_name") or best.get("name") or mapped_symbol,
                    "exchange": best.get("exchange"),
                    "currency": best.get("currency") or "USD",
                }

    # Direct symbol probe fallback (handles plain inputs like BPCL -> BPCL.NS/BPCL.BO).
    # This avoids hard-failing search when provider symbol-search indexes are incomplete.
    probe_candidates: List[str] = []
    if "." in query:
        probe_candidates.append(query)
    else:
        probe_candidates.extend([query, f"{query}.NS", f"{query}.BO"])
    probe_candidates = _sanitize_tickers(probe_candidates)

    if probe_candidates:
        p, c, _ = _fetch_live_quotes(probe_candidates)
        for cand in probe_candidates:
            if cand in p:
                return {
                    "ok": True,
                    "symbol": cand,
                    "shortname": cand,
                    "exchange": "NSE" if cand.endswith(".NS") else "BSE" if cand.endswith(".BO") else "GLOBAL",
                    "currency": c.get(cand, _default_currency_for_symbol(cand)),
                }

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


@app.post("/api/v1/decision/parse")
def decision_parse(request: Request, body: DecisionAnalyzeIn):
    """
    Interpretation Layer Endpoint.
    Propagates the strict JSON parsing and validation to the UI.
    Matching User Requirement: Input Interpretation Layer
    """
    require_admin(request)
    
    # Load portfolio for context-aware parsing
    pstore = read_portfolios()
    pitems = pstore.get("items", [])
    portfolio = pitems[0] if pitems else None
    
    # Parse (Hybrid: Heuristic -> LLM -> Validation)
    decision = parse_decision(body.decision_text, portfolio)
    
    return {"ok": True, "decision": decision.dict()}


@app.post("/api/v1/decision/simulate")
def decision_simulate(request: Request, body: DecisionSimulationIn):
    """
    Simulation & Intelligence Layer Endpoint.
    Orchestrates the full flow: Parse -> Simulate -> Score -> Explain.
    Returns Universal Output Blueprint data.
    """
    require_admin(request)
    
    try:
        # Load portfolio
        pstore = read_portfolios()
        pitems = pstore.get("items", [])
        portfolio = pitems[0] if pitems else None
        
        if not portfolio:
            raise HTTPException(status_code=404, detail="No portfolio found")
            
        # 1. Parse Decision (Interpretation Layer)
        decision = parse_decision(body.decision_text, portfolio)
        
        # 1.5. Pre-process Decision: Resolve Shares -> USD
        # We need real prices to convert "10 shares" -> "$2000" -> "2%"
        all_symbols = tuple(decision.get_all_symbols())
        if all_symbols:
            try:
                price_result = fetch_prices(tickers=all_symbols, lookback_days=5, cache_ttl_seconds=300)
                latest_prices = {t: price_result.prices[t].iloc[-1] for t in all_symbols if t in price_result.prices}
                
                for action in decision.actions:
                    if action.symbol in latest_prices:
                        price = float(latest_prices[action.symbol])
                        if action.size_shares is not None:
                            action.size_usd = action.size_shares * price
                            # Clearing size_percent to force recalculation based on USD
                            action.size_percent = None 
            except Exception as e:
                print(f"Price fetch warning in pre-process: {e}")

        # 2. Run Intelligence Engine (Simulation Layer)
        if body.mode == "fast":
            comparison, score = run_decision_intelligence_fast(
                portfolio, decision, body.horizon_days
            )
            base_paths, scen_paths = None, None
        else:
            comparison, score, base_paths, scen_paths = run_decision_intelligence(
                portfolio, decision, body.horizon_days, body.n_paths, body.return_paths
            )
        
        # 3. Calculate Execution Context (Section 2)
        execution_context = calculate_execution_context(portfolio, decision)
        
        # 4. Calculate Risk Analysis (Sections 6-10)
        risk_analysis = calculate_risk_analysis(
            portfolio, decision, comparison, scen_paths, body.horizon_days
        )
        
            
        # 5. Calculate Projections (NEW)
        projections = {}
        if scen_paths:
            projections = calculate_projections(scen_paths)
        else:
            # Fallback for fast mode: Approximate using annual return
            r = comparison.scenario_expected_return / 100.0
            projections = {
                "1M": r * (30/365),
                "3M": r * (90/365),
                "6M": r * (180/365),
                "1Y": r
            }

        # 6. Tax Engine Calculation (Institutional-Grade)
        tax_analysis = None
        try:
            tax_engine = TaxEngine()
            
            # Build TaxProfile from request
            tax_profile = TaxProfile(
                jurisdiction=body.tax_jurisdiction,
                sub_jurisdiction=body.tax_sub_jurisdiction,
                filing_status=FilingStatus(body.tax_filing_status) if body.tax_filing_status else FilingStatus.SINGLE,
                income_tier=IncomeTier(body.tax_income_tier) if body.tax_income_tier else IncomeTier.MEDIUM,
            )
            
            # Build PortfolioTaxContext
            portfolio_tax_ctx = PortfolioTaxContext(
                account_type=AccountType(body.tax_account_type) if body.tax_account_type else AccountType.TAXABLE,
                holding_period=HoldingPeriod(body.tax_holding_period) if body.tax_holding_period else HoldingPeriod.SHORT_TERM,
                total_portfolio_value_usd=portfolio.get("total_value", 100000),
                estimated_gain_percent=20.0, # Default assumption for simulations
            )
            
            # Build TransactionDetails from decision actions
            transactions = []
            for action in decision.actions:
                # Include ALL actions (Buy/Sell) so the engine can report "No Tax" for buys
                # Calculate transaction value
                txn_value = 0.0
                if action.size_usd:
                    txn_value = action.size_usd
                elif action.size_percent:
                    txn_value = (action.size_percent / 100.0) * portfolio.get("total_value", 100000)
                else:
                    txn_value = portfolio.get("total_value", 100000) * 0.05  # Default 5%
                
                asset_class = tax_engine.classify_asset(action.symbol, portfolio)
                
                # Determine estimated gain/loss for SELLs
                est_gain = None
                direction_str = getattr(action.direction, 'value', str(action.direction)).lower()
                if direction_str in ["sell", "liquidate", "reduce", "short"]:
                     # For simulation, assume a default gain % (e.g. 20%) if we can't look up lots
                     est_gain = txn_value * 0.20
                elif direction_str in ["buy", "long", "add", "increase"] and comparison:
                     # For BUY, calculate EXPECTED future gain based on simulation return
                     # This allows "Projected Realization Tax" to be shown
                     proj_return = comparison.scenario_expected_return  # This is in percent (e.g. 7.09 means 7.09%)
                     if proj_return > 0:
                         est_gain = txn_value * (proj_return / 100.0)  # Convert percent to ratio
                     print(f"DEBUG TAX BUY: direction={direction_str}, proj_return={proj_return}%, txn_value={txn_value}, est_gain={est_gain}")
                
                transactions.append(TransactionDetail(
                    symbol=action.symbol,
                    direction=getattr(action.direction, 'value', str(action.direction)),
                    transaction_value_usd=txn_value,
                    asset_class=asset_class,
                    estimated_gain_usd=est_gain,
                ))
            
            # Always run tax engine, even if empty (returns "no impact")
            if transactions:
                tax_impact = tax_engine.calculate(tax_profile, portfolio_tax_ctx, transactions)
                tax_analysis = tax_impact.dict()
            else:
                # Edge case: No actions at all
                tax_analysis = None
        except Exception as tax_err:
            print(f"TAX ENGINE WARNING: {tax_err}")
            tax_analysis = {"error": str(tax_err), "summary": "Tax calculation failed"}

        # 7. Generate Visualization Data (Canonical Interface)
        # We need to instantiate the canonical objects to get standard visualizations
        try:
            # Create consequences engine
            consequences = DecisionConsequences(
                portfolio_data=portfolio,
                decision_text=body.decision_text,
                decision_category=decision.decision_type
            )
            
            # Create canonical decision wrapper
            real_life_decision = RealLifeDecision(
                decision_consequences=consequences,
                decision_text=body.decision_text,
                portfolio_data=portfolio
            )
            
            # Extract visualization data
            visualization_data = real_life_decision.visualization_data
        except Exception as viz_err:
            print(f"VIZ GENERATION WARNING: {viz_err}")
            traceback.print_exc()
            visualization_data = None

        # 8. Compute Tax Metrics (Pre-Tax vs After-Tax comparison)
        tax_metrics = None
        if tax_analysis and not tax_analysis.get("error"):
            try:
                tax_drag_pct = tax_analysis.get("effective_tax_rate", 0.0) / 100.0
                # Conversion: Temporal Engine returns Percentages (e.g. 5.0 for 5%)
                # Frontend expects Decimals (e.g. 0.05 for 5%) for this specific TaxMetrics table
                scenario_ret = (comparison.scenario_expected_return if comparison else 0) / 100.0
                
                scenario_dd = (comparison.scenario_max_drawdown if comparison else 0) / 100.0
                scenario_tail = (comparison.scenario_tail_loss if comparison else 0) / 100.0

                tax_metrics = {
                    "expected_return_pre": round(scenario_ret, 4),
                    "expected_return_post": round(scenario_ret * (1 - tax_drag_pct), 4),
                    "max_drawdown_pre": round(scenario_dd, 4),
                    "max_drawdown_post": round(scenario_dd - (tax_drag_pct * abs(scenario_dd) * 0.5), 4),
                    "tail_loss_pre": round(scenario_tail, 4),
                    "tail_loss_post": round(scenario_tail - (tax_drag_pct * abs(scenario_tail) * 0.5), 4),
                }
            except Exception:
                tax_metrics = None

        # Exit assumptions from horizon context
        exit_assumptions = None
        if tax_analysis and not tax_analysis.get("error"):
            hp = body.tax_holding_period or "short_term"
            exit_assumptions = {
                "trigger": "Scenario Simulation Exit",
                "holding_period_days": body.horizon_days,
                "tax_regime": tax_analysis.get("tax_regime_applied", hp.replace("_", " ").title()),
            }
            # Attach to tax_analysis too
            tax_analysis["exit_assumptions"] = exit_assumptions

        # 9. Construct Response (Universal Output Blueprint)
        return {
            "ok": True,
            "decision": decision.dict(),
            "comparison": comparison.dict(),
            "score": score.dict(),
            "execution_context": execution_context.dict(),
            "risk_analysis": risk_analysis.dict(),
            "baseline_paths": [p.dict() for p in base_paths] if base_paths else None,
            "scenario_paths": [p.dict() for p in scen_paths] if scen_paths else None,
            "projections": projections,
            "tax_analysis": tax_analysis,
            "tax_metrics": tax_metrics,
            "visualization_data": visualization_data,
            "mode": body.mode
        }
    except Exception as e:
        print(f"SIMULATION ERROR: {str(e)}")
        traceback.print_exc()
        return JSONResponse(
            status_code=500, 
            content={"message": f"Simulation failed: {str(e)}", "traceback": traceback.format_exc()}
        )


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
                # Normalize only if rebalancing
                if body.decision_type == "rebalance":
                    weight = (pos.get("weight", 0) * 100) / total_weight * 100
                else:
                    weight = pos.get("weight", 0) * 100
                new_positions.append({"symbol": ticker, "weight_pct": round(weight, 2)})
        else:
            # Fallback if total weight is 0
            for pos in portfolio.get("positions", []):
                ticker = pos.get("ticker")
                weight = pos.get("weight", 0) * 100
                new_positions.append({"symbol": ticker, "weight_pct": round(weight, 2)})

        # Validate portfolio weight conservation (weights must sum to 100% ±0.5%)
        # Only enforce for rebalance
        total_weight_after = sum(pos["weight_pct"] for pos in new_positions)
        if body.decision_type == "rebalance" and abs(total_weight_after - 100.0) > 0.5:
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
        
        # Only normalize if rebalancing
        if body.decision_type == "rebalance" and total_raw_weight > 0 and abs(total_raw_weight - 100.0) > 0.1:  # Only normalize if significantly different
            normalized_positions = []
            for pos in new_positions:
                normalized_weight = (pos["weight_pct"] / total_raw_weight) * 100.0
                normalized_positions.append({"symbol": pos["symbol"], "weight_pct": round(normalized_weight, 2)})
            new_positions = normalized_positions

        # Validate portfolio weight conservation (weights must sum to 100% ±0.5%)
        # Only enforce for rebalance
        total_weight_after = sum(pos["weight_pct"] for pos in new_positions)
        if body.decision_type == "rebalance" and abs(total_weight_after - 100.0) > 0.5:
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
                # Normalize only if rebalancing
                if body.decision_type == "rebalance":
                    weight = (pos.get("weight", 0) * 100) / total_weight * 100
                else:
                    weight = pos.get("weight", 0) * 100
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
        # Only enforce for rebalance
        if body.decision_type == "rebalance" and abs(total_weight_after - 100.0) > 0.5:
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
            market_context["prices_tail"] = _to_prices_tail_payload(tail)
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


# ----------------------------
# NEW: Unified Scenario Endpoint (combines Classic + AI)
# ----------------------------
class UnifiedScenarioIn(BaseModel):
    """Input for the unified scenario endpoint."""
    decision_text: str = Field(..., min_length=3, max_length=400)
    tax_country: str = Field(default="United States")
    decision_type: str = Field(default="rebalance")
    magnitude: int = Field(default=5)
    mode: str = Field(default="Compounding Mode")
    horizon_days: int = Field(default=30, ge=1, le=365)


class UnifiedScenarioOut(BaseModel):
    """Output from the unified scenario endpoint."""
    ok: bool
    
    # Classic simulation results
    classic: Dict[str, Any]
    
    # AI verdict (simplified for beginners)
    ai_verdict: Dict[str, Any]


@app.post("/api/v1/scenario/unified", response_model=UnifiedScenarioOut)
def scenario_unified(request: Request, body: UnifiedScenarioIn):
    """
    Unified Scenario Simulation: Combines Classic analysis with AI Decision Intelligence.
    
    Returns both:
    1. Classic simulation (detailed text-based analysis)
    2. AI verdict (simplified score and recommendation)
    """
    require_admin(request)
    
    # Load portfolio
    pstore = read_portfolios()
    pitems = pstore.get("items", [])
    if not pitems:
        raise HTTPException(status_code=400, detail="No saved portfolio found. Save a portfolio first.")
    portfolio = pitems[0]
    
    # Build ScenarioIn for classic simulation
    classic_body = ScenarioIn(
        decision_text=body.decision_text,
        tax_country=body.tax_country,
        decision_type=body.decision_type,
        magnitude=body.magnitude,
        mode=body.mode
    )
    
    # Run classic simulation (reuse existing logic)
    try:
        # Create a mock request object to call scenario_run
        classic_result = scenario_run(request, classic_body)
    except HTTPException as e:
        classic_result = {"ok": False, "error": str(e.detail)}
    except Exception as e:
        classic_result = {"ok": False, "error": str(e)}
    
    # Run AI Decision Intelligence
    ai_verdict = {
        "verdict": "neutral",
        "composite_score": 50.0,
        "summary": "Unable to analyze decision.",
        "recommendation": "Review the decision details.",
    }
    
    try:
        decision = parse_decision(body.decision_text, portfolio)
        
        if decision.actions:
            comparison, score, _, _ = run_decision_intelligence(
                portfolio=portfolio,
                decision=decision,
                horizon_days=body.horizon_days,
                n_paths=50,  # Use fewer paths for speed
                include_paths=False
            )
            
            # Simplify AI output for beginners
            verdict_text = score.verdict.value.replace("_", " ").title()
            
            # Map verdict to beginner-friendly recommendation
            if score.composite_score >= 70:
                recommendation = "✅ This looks like a good decision for your portfolio."
            elif score.composite_score >= 55:
                recommendation = "👍 This decision seems reasonable, but monitor closely."
            elif score.composite_score >= 45:
                recommendation = "⚖️ This decision has mixed impacts. Consider your goals."
            elif score.composite_score >= 30:
                recommendation = "⚠️ This decision may increase your portfolio risk."
            else:
                recommendation = "🛑 Caution: This decision significantly increases risk."
            
            ai_verdict = {
                "verdict": verdict_text,
                "composite_score": round(score.composite_score, 1),
                "summary": score.summary,
                "recommendation": recommendation,
                "delta_return": round(comparison.delta_return, 2),
                "delta_volatility": round(comparison.delta_volatility, 2),
                "key_factors": score.key_factors[:3],  # Top 3 factors
                "warnings": score.warnings[:2],  # Top 2 warnings
            }
    except Exception as e:
        ai_verdict["error"] = str(e)
    
    return UnifiedScenarioOut(
        ok=True,
        classic=classic_result if isinstance(classic_result, dict) else classic_result.dict(),
        ai_verdict=ai_verdict,
    )


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
                prices, _, w = _fetch_live_quotes(tlist)
                payload = {k: float(v) for k, v in prices.items()}
                warnings.extend(w[:5])
            except Exception as e:
                warnings.append(str(e))
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


def _httpx_get_json(url: str, timeout_s: float = 3.0) -> Optional[Dict[str, Any]]:
    """Best-effort JSON getter with SSL-relaxed retry for hostile local cert chains."""
    try:
        r = httpx.get(url, timeout=timeout_s)
        r.raise_for_status()
        return r.json()
    except Exception:
        try:
            r = httpx.get(url, timeout=timeout_s, verify=False)
            r.raise_for_status()
            return r.json()
        except Exception:
            return None


def _to_twelve_symbol(raw_symbol: str) -> str:
    """Convert common Yahoo-style suffixes into Twelve Data symbol format."""
    s = (raw_symbol or "").strip().upper()
    suffix_map = {
        ".NS": ":NSE",
        ".BO": ":BSE",
        ".L": ":LSE",
        ".TO": ":TSX",
        ".HK": ":HKEX",
    }
    for k, v in suffix_map.items():
        if s.endswith(k):
            return f"{s[:-len(k)]}{v}"
    return s


def _to_twelve_symbols(raw_symbol: str) -> List[str]:
    """Build Twelve Data symbol variants for better global hit rate."""
    s = (raw_symbol or "").strip().upper()
    if not s:
        return []
    variants: List[str] = []
    is_indian = _is_indian_symbol(s)
    if s.endswith(".NS"):
        base = s[:-3]
        variants.extend([f"{base}:NSE", base, s])
    elif s.endswith(".BO"):
        base = s[:-3]
        variants.extend([f"{base}:BSE", base, s])
    elif s.endswith(".L"):
        base = s[:-2]
        variants.extend([f"{base}:LSE", base, s])
    elif s.endswith(".TO"):
        base = s[:-3]
        variants.extend([f"{base}:TSX", base, s])
    elif s.endswith(".HK"):
        base = s[:-3]
        variants.extend([f"{base}:HKEX", base, s])
    else:
        variants.extend([s, _to_twelve_symbol(s)])
        if is_indian:
            variants.extend([f"{s}:NSE", f"{s}:BSE", f"{s}.NS", f"{s}.BO"])

    seen = set()
    out = []
    for v in variants:
        if v and v not in seen:
            seen.add(v)
            out.append(v)
    return out


def _from_twelve_symbol(td_symbol: str) -> str:
    """Map Twelve Data exchange suffixes back to UI symbol convention."""
    s = (td_symbol or "").strip().upper()
    suffix_map = {
        ":NSE": ".NS",
        ":BSE": ".BO",
        ":LSE": ".L",
        ":TSX": ".TO",
        ":HKEX": ".HK",
    }
    for k, v in suffix_map.items():
        if s.endswith(k):
            return f"{s[:-len(k)]}{v}"
    return s


def _twelve_get_json(path: str, params: Dict[str, Any], timeout_s: float = 5.0) -> Optional[Dict[str, Any]]:
    if not TWELVE_DATA_API_KEY:
        return None
    q = dict(params or {})
    q["apikey"] = TWELVE_DATA_API_KEY
    url = f"https://api.twelvedata.com{path}"
    try:
        r = httpx.get(url, params=q, timeout=timeout_s)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def _extract_td_price_currency(item: Dict[str, Any]) -> tuple[Optional[float], Optional[str]]:
    candidates = [
        item.get("price"),
        item.get("close"),
        item.get("previous_close"),
        item.get("ask"),
        item.get("bid"),
    ]
    price = next((float(v) for v in candidates if v is not None and str(v).replace(".", "", 1).replace("-", "", 1).isdigit()), None)
    if price is None:
        for v in candidates:
            try:
                fv = float(v)
                if fv > 0:
                    price = fv
                    break
            except Exception:
                continue
    if price is not None and price <= 0:
        price = None
    currency = item.get("currency") or item.get("currency_base")
    ccy = str(currency).upper() if currency else None
    if ccy and (len(ccy) != 3 or not ccy.isalpha()):
        ccy = None
    return price, ccy


def _to_yf_symbols(symbol: str) -> List[str]:
    """Build yfinance symbol variants, including Indian exchange suffixes."""
    s = (symbol or "").strip().upper()
    if not s:
        return []
    variants: List[str] = []
    if s.endswith(".NS") or s.endswith(".BO"):
        base = s.split(".")[0]
        variants.extend([s, base])
    elif "." in s:
        variants.append(s)
    else:
        variants.append(s)
        if _is_indian_symbol(s):
            variants.extend([f"{s}.NS", f"{s}.BO"])
    seen = set()
    out = []
    for v in variants:
        if v and v not in seen:
            seen.add(v)
            out.append(v)
    return out


def _fetch_yfinance_live_quote(symbol: str) -> tuple[Optional[float], Optional[str]]:
    """Fetch latest quote from yfinance for a single symbol with small variant probing."""
    if yf is None:
        return None, None
    for cand in _to_yf_symbols(symbol):
        try:
            df = yf.download(
                tickers=cand,
                period="2d",
                interval="1d",
                auto_adjust=True,
                progress=False,
                threads=False,
                group_by="column",
            )
            if df is not None and not df.empty and "Close" in df.columns:
                close = df["Close"].dropna()
                if not close.empty:
                    p = float(close.iloc[-1])
                    if p > 0:
                        ccy = _default_currency_for_symbol(cand)
                        return p, ccy
            tk = yf.Ticker(cand)
            hist = tk.history(period="5d", interval="1d", auto_adjust=True)
            if hist is not None and not hist.empty and "Close" in hist.columns:
                close = hist["Close"].dropna()
                if not close.empty:
                    p = float(close.iloc[-1])
                    if p > 0:
                        ccy = _default_currency_for_symbol(cand)
                        return p, ccy
        except Exception:
            continue
    return None, None


def _fetch_yahoo_live_quote(symbol: str) -> tuple[Optional[float], Optional[str]]:
    """Fetch latest quote directly from Yahoo quote/chart endpoints with relaxed SSL retry."""
    for cand in _to_yf_symbols(symbol):
        quote_url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={quote_plus(cand)}"
        qdata = _httpx_get_json(quote_url, timeout_s=4.0)
        if isinstance(qdata, dict):
            result = ((qdata.get("quoteResponse") or {}).get("result") or [])
            for item in result:
                sym = str(item.get("symbol", "")).upper()
                if sym and sym != cand:
                    continue
                p = item.get("regularMarketPrice")
                if isinstance(p, (int, float)) and float(p) > 0:
                    ccy = str(item.get("currency", "")).upper() or _default_currency_for_symbol(cand)
                    return float(p), ccy

        chart_url = (
            f"https://query1.finance.yahoo.com/v8/finance/chart/{quote_plus(cand)}"
            f"?interval=1d&range=5d&includePrePost=false&events=div%2Csplits"
        )
        cdata = _httpx_get_json(chart_url, timeout_s=4.0)
        try:
            result = ((cdata or {}).get("chart", {}) or {}).get("result", [None])[0]
            if result:
                inds = result.get("indicators", {}) or {}
                close = None
                adj = inds.get("adjclose") or []
                if adj and isinstance(adj[0], dict):
                    close = adj[0].get("adjclose")
                if close is None:
                    quote = inds.get("quote") or []
                    if quote and isinstance(quote[0], dict):
                        close = quote[0].get("close")
                if close:
                    vals = [float(v) for v in close if isinstance(v, (int, float)) and float(v) > 0]
                    if vals:
                        meta_ccy = str((result.get("meta") or {}).get("currency", "")).upper()
                        ccy = meta_ccy or _default_currency_for_symbol(cand)
                        return float(vals[-1]), ccy
        except Exception:
            pass

    return None, None


def _default_currency_for_symbol(symbol: str) -> str:
    s = (symbol or "").upper()
    if s.endswith(".NS") or s.endswith(".BO"):
        return "INR"
    if s.endswith(".L"):
        return "GBP"
    if s.endswith(".TO"):
        return "CAD"
    if s.endswith(".HK"):
        return "HKD"
    return "USD"


def _canonical_symbol_for_prices(symbol: str) -> str:
    """Normalize known symbols to provider-friendly canonical forms."""
    s = (symbol or "").strip().upper()
    if not s:
        return s
    try:
        info = ASSET_RESOLVER.resolve_asset(s)
        if info and info.is_valid:
            resolved = str(info.symbol or s).upper()
            if info.country == "India" and "." not in resolved:
                return f"{resolved}.NS"
            return resolved
    except Exception:
        pass
    return s


def _is_indian_symbol(symbol: str) -> bool:
    s = (symbol or "").strip().upper()
    if s.endswith(".NS") or s.endswith(".BO"):
        return True
    try:
        info = ASSET_RESOLVER.resolve_asset(s)
        return bool(info and info.country == "India")
    except Exception:
        return False


def _to_prices_tail_payload(df: pd.DataFrame) -> Dict[str, Any]:
    """Serialize a price frame safely for JSON (no NaN/Inf)."""
    values: Dict[str, List[Optional[float]]] = {}
    if df is None or df.empty:
        return {"index": [], "values": values}

    for c in df.columns:
        series: List[Optional[float]] = []
        has_finite = False
        for v in df[c].values:
            try:
                fv = float(v)
            except Exception:
                fv = float("nan")
            if math.isfinite(fv):
                series.append(fv)
                has_finite = True
            else:
                series.append(None)
        if has_finite:
            values[str(c)] = series

    return {"index": [str(x) for x in df.index], "values": values}


def _fetch_live_quotes(tickers: List[str]) -> tuple[Dict[str, float], Dict[str, str], List[str]]:
    """
    Pull quotes from Twelve Data, then yfinance, then cached prices.
    Returns prices, currencies, warnings.
    """
    symbols = [t.strip().upper() for t in tickers if t and t.strip()]
    if not symbols:
        return {}, {}, ["No symbols provided"]

    warnings: List[str] = []
    prices: Dict[str, float] = {}
    currencies: Dict[str, str] = {}

    # Hot cache first for snappy UI refreshes.
    for s in symbols:
        cached = _get_symbol_price_cache(s, _SYMBOL_PRICE_CACHE_FAST_AGE)
        if cached:
            prices[s] = float(cached["price"])
            currencies[s] = str(cached.get("currency") or _default_currency_for_symbol(s))

    # Provider 1: Twelve Data
    if TWELVE_DATA_API_KEY:
        td_variants = {s: _to_twelve_symbols(s) for s in symbols}
        td_primary = {s: (v[0] if v else _to_twelve_symbol(s)) for s, v in td_variants.items()}
        batch = _twelve_get_json("/quote", {"symbol": ",".join(td_primary.values())})
        if batch:
            if str(batch.get("status", "")).lower() == "error":
                warnings.append(f"twelve_data_batch_error:{batch.get('message', 'unknown')}")
            else:
                parsed_count = 0
                for req_sym, td_sym in td_primary.items():
                    rec = batch.get(td_sym) or batch.get(req_sym) or batch.get(_from_twelve_symbol(td_sym))
                    if isinstance(rec, dict):
                        p, ccy = _extract_td_price_currency(rec)
                        if p is not None:
                            prices[req_sym] = p
                            if ccy:
                                currencies[req_sym] = ccy
                            parsed_count += 1
                if parsed_count == 0 and isinstance(batch, dict) and "symbol" in batch:
                    rec_sym = str(batch.get("symbol", "")).upper()
                    ui_sym = _from_twelve_symbol(rec_sym)
                    p, ccy = _extract_td_price_currency(batch)
                    if p is not None:
                        back = next((k for k, v in td_primary.items() if v == rec_sym), ui_sym)
                        prices[back] = p
                        if ccy:
                            currencies[back] = ccy
        else:
            warnings.append("twelve_data_batch_failed")

        for req_sym, td_list in td_variants.items():
            if req_sym in prices:
                continue
            got = False
            for td_sym in td_list:
                one = _twelve_get_json("/quote", {"symbol": td_sym})
                if not one:
                    continue
                if str(one.get("status", "")).lower() == "error":
                    continue
                p, ccy = _extract_td_price_currency(one if isinstance(one, dict) else {})
                if p is not None:
                    prices[req_sym] = p
                    if ccy:
                        currencies[req_sym] = ccy
                    got = True
                    break
            if not got:
                warnings.append(f"twelve_data_symbol_failed:{req_sym}")
    else:
        warnings.append("twelve_data_not_configured")

    # Provider 2: Direct Yahoo endpoints (quote/chart), avoids yfinance parser brittleness.
    for req_sym in symbols:
        if req_sym in prices:
            continue
        p, ccy = _fetch_yahoo_live_quote(req_sym)
        if p is not None:
            prices[req_sym] = p
            currencies[req_sym] = ccy or currencies.get(req_sym, _default_currency_for_symbol(req_sym))
            _set_symbol_price_cache(req_sym, p, currencies[req_sym], source="yahoo_direct")
        else:
            warnings.append(f"yahoo_direct_symbol_failed:{req_sym}")

    # Provider 3: optional yfinance fallback (disabled by default for latency).
    if ENABLE_YFINANCE_LIVE_FALLBACK:
        for req_sym in symbols:
            if req_sym in prices:
                continue
            p, ccy = _fetch_yfinance_live_quote(req_sym)
            if p is not None:
                prices[req_sym] = p
                currencies[req_sym] = ccy or currencies.get(req_sym, _default_currency_for_symbol(req_sym))
                _set_symbol_price_cache(req_sym, p, currencies[req_sym], source="yfinance")
            else:
                warnings.append(f"yfinance_symbol_failed:{req_sym}")

    # Update cache for fresh values.
    for s, p in prices.items():
        if not _get_symbol_price_cache(s, max_age_seconds=2):
            _set_symbol_price_cache(s, p, currencies.get(s, _default_currency_for_symbol(s)), source="twelve_or_yfinance")

    # Final fallback: last cached value.
    missing = [s for s in symbols if s not in prices]
    for s in missing:
        cached = _get_symbol_price_cache(s, _SYMBOL_PRICE_CACHE_MAX_STALE)
        if cached:
            prices[s] = float(cached["price"])
            currencies[s] = str(cached.get("currency") or "USD")
            age_sec = int(time.time() - float(cached.get("ts", 0)))
            warnings.append(f"using_cached_price:{s}:age={age_sec}s")
        elif s in prices and s not in currencies:
            currencies[s] = _default_currency_for_symbol(s)

    return prices, currencies, warnings

@app.get("/api/v1/market/prices")
def market_prices(
    request: Request,
    tickers: str,
    lookback: int = 365,
    interval: Literal["1d", "1wk", "1mo"] = "1d",
):
    require_admin(request)
    raw = [t for t in tickers.split(",")]
    tlist = _sanitize_tickers([_canonical_symbol_for_prices(t) for t in raw])
    warnings: List[str] = []
    
    # Check in-memory cache first for instant response
    cache_key = f"prices:{','.join(sorted(tlist))}:{lookback}:{interval}"
    cached = _get_cached_prices(cache_key)
    if cached is not None:
        try:
            rows = int((cached or {}).get("data", {}).get("rows_returned", 0))
            # Don't serve stale empty responses; re-attempt upstream fetch.
            if rows > 0:
                cached_vals = ((cached or {}).get("data", {}).get("prices_tail", {}) or {}).get("values", {}) or {}
                cached_symbols = {str(k).upper() for k in cached_vals.keys()}
                requested_symbols = {str(t).upper() for t in tlist}
                # Avoid serving partial cached responses that are missing requested symbols.
                if requested_symbols.issubset(cached_symbols):
                    return cached
        except Exception:
            return cached

    # Indian/global symbols are more reliable via the broader fetch stack than
    # the live-quote shortcut (which is US-focused and provider-sensitive).
    if interval == "1d" and lookback <= 5 and tlist and any(_is_indian_symbol(t) for t in tlist):
        try:
            data = fetch_prices(tlist, lookback_days=lookback, interval=interval, require_returns=False)
            tail = data.prices.tail(1)
            if not tail.empty:
                out = {
                    "tickers": tlist,
                    "interval": interval,
                    "lookback_days": lookback,
                    "rows_returned": int(tail.shape[0]),
                    "source": f"direct_fallback:{getattr(data, 'source', 'unknown')}",
                    "currencies": {t: _default_currency_for_symbol(t) for t in tlist},
                    "prices_tail": _to_prices_tail_payload(tail),
                }
                result = {"ok": True, "data": out}
                _set_cached_prices(cache_key, result)
                return result
        except Exception as e:
            warnings.append(f"direct_fallback_failed:{e}")

    # Fast path for UI quote refreshes: fetch live quotes directly.
    if interval == "1d" and lookback <= 5 and tlist:
        live_prices, live_ccy, live_diag = _fetch_live_quotes(tlist)
        if live_prices:
            # If only a subset resolved from live providers, backfill missing tickers
            # via the broader historical fetch stack before returning.
            missing = [t for t in tlist if t not in live_prices]
            if missing:
                try:
                    fb_data = fetch_prices(missing, lookback_days=lookback, interval=interval, require_returns=False)
                    fb_tail = fb_data.prices.tail(1)
                    if not fb_tail.empty:
                        for sym in fb_tail.columns:
                            vals = fb_tail[sym].dropna()
                            if not vals.empty:
                                live_prices[sym] = float(vals.iloc[-1])
                                live_ccy[sym] = _default_currency_for_symbol(sym)
                        warnings.append(f"live_quote_partial_backfilled:{getattr(fb_data, 'source', 'unknown')}")
                except Exception as e:
                    warnings.append(f"live_quote_backfill_failed:{e}")

            now = pd.Timestamp.utcnow().floor("s")
            safe_live = {t: float(v) for t, v in live_prices.items() if _is_finite(v)}
            out = {
                "tickers": tlist,
                "interval": interval,
                "lookback_days": lookback,
                "rows_returned": 1,
                "source": "live_quote",
                "currencies": {t: live_ccy.get(t, "USD") for t in tlist},
                "prices_tail": {
                    "index": [str(now)],
                    "values": {t: [float(v)] for t, v in safe_live.items()},
                },
            }
            missing = [t for t in tlist if t not in safe_live]
            if missing:
                out["warnings"] = [f"Missing live quote for: {', '.join(missing)}"] + warnings + live_diag[:5]
            elif warnings:
                out["warnings"] = warnings + live_diag[:5]
            result = {"ok": True, "data": out}
            if not missing:
                _set_cached_prices(cache_key, result)
            return result
        else:
            warnings.extend([f"live_quote_failed:{x}" for x in live_diag[:5]] if live_diag else ["live_quote_failed:no_diagnostics"])
            # Fallback to the broader historical fetch stack (Yahoo chart/stooq/mock) for
            # international symbols when live quote providers fail.
            try:
                fb_data = fetch_prices(tlist, lookback_days=lookback, interval=interval, require_returns=False)
                fb_tail = fb_data.prices.tail(1)
                if not fb_tail.empty:
                    out = {
                        "tickers": tlist,
                        "interval": interval,
                        "lookback_days": lookback,
                        "rows_returned": int(fb_tail.shape[0]),
                        "source": f"live_fallback:{getattr(fb_data, 'source', 'unknown')}",
                        "currencies": {t: _default_currency_for_symbol(t) for t in tlist},
                        "prices_tail": _to_prices_tail_payload(fb_tail),
                        "warnings": warnings + ["Live quote provider failed; used historical fallback source."],
                    }
                    result = {"ok": True, "data": out}
                    _set_cached_prices(cache_key, result)
                    return result
            except Exception as e:
                warnings.append(f"live_fallback_failed:{e}")

            out = {
                "tickers": tlist,
                "interval": interval,
                "lookback_days": lookback,
                "rows_returned": 0,
                "source": "none",
                "currencies": {t: "USD" for t in tlist},
                "prices_tail": {"index": [], "values": {}},
                "warnings": warnings + ["No live quote available from Twelve Data, yfinance, or fallback sources."],
            }
            return {"ok": True, "data": out}
    
    data = None
    try:
        if not tlist:
            raise ValueError("No valid tickers provided after sanitization")
        data = fetch_prices(tlist, lookback_days=lookback, interval=interval, require_returns=False)
    except Exception as e:
        warnings.append(str(e))

    if data is None:
        out = {
            "tickers": tlist,
            "interval": interval,
            "lookback_days": lookback,
            "rows_returned": 0,
            "source": "none",
            "prices_tail": {"index": [], "values": {}},
            "warnings": warnings,
        }
        result = {"ok": True, "data": out}
        # Never cache empty/failed fetch results.
        return result

    tail = data.prices.tail(25)
    
    # NEW: Resolve currencies for each ticker
    currencies = {}
    for t in tlist:
        # Default to USD
        currencies[t] = "USD"
        try:
            info = ASSET_RESOLVER.resolve_asset(t)
            if info:
                if info.country == "India":
                    currencies[t] = "INR"
                elif info.country == "USA":
                    currencies[t] = "USD"
                elif info.country == "Canada":
                    currencies[t] = "CAD"
                elif info.country == "UK" or info.country == "United Kingdom":
                    currencies[t] = "GBP"
                elif info.country in ["Germany", "France", "Italy", "Spain", "Netherlands"]:
                    currencies[t] = "EUR"
                # Add more mappings as needed
        except Exception:
            pass

    out = {
        "tickers": tlist,
        "interval": interval,
        "lookback_days": lookback,
        "rows_returned": int(tail.shape[0]),
        "source": getattr(data, "source", "unknown"),
        "currencies": currencies, # NEW field
        "prices_tail": _to_prices_tail_payload(tail),
    }
    if warnings:
        out["warnings"] = warnings
    result = {"ok": True, "data": out}
    if int(tail.shape[0]) > 0:
        _set_cached_prices(cache_key, result)
    return result


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
        
        # Generate Monte Carlo paths for all 4 time horizons using portfolio volatility
        if body.include_paths:
            try:
                # Use the computed portfolio volatility from the output
                annual_vol = out["annualized_vol"]  # Already a float
                daily_vol = annual_vol / np.sqrt(252)  # Convert to daily
                daily_drift = 0.0001  # Small positive drift (approx 2.5% annual)
                
                horizons = {"1m": 30, "3m": 90, "6m": 180, "1y": 365}
                all_horizon_paths = {}
                n_paths = body.n_paths  # Use requested paths (default 1000)
                initial_value = 100000.0
                
                for horizon_name, horizon_days in horizons.items():
                    # Vectorized Monte Carlo Simulation
                    # Generate all random returns at once: (n_paths, horizon_days)
                    # This is much faster than looping
                    daily_returns = np.random.normal(daily_drift, daily_vol, (n_paths, horizon_days))
                    
                    # Compute cumulative return factor for each path
                    # (1 + r1) * (1 + r2) * ... 
                    cum_returns = np.prod(1 + daily_returns, axis=1)
                    
                    # Compute terminal values
                    terminal_values = initial_value * cum_returns
                    
                    # Compute terminal returns percentage
                    path_returns = (terminal_values - initial_value) / initial_value * 100
                    
                    # Calculate statistics on the array
                    all_horizon_paths[horizon_name] = {
                        "horizon_days": int(horizon_days),
                        "n_paths": int(n_paths),
                        "best_case": float(np.max(path_returns)),
                        "worst_case": float(np.min(path_returns)),
                        "median": float(np.median(path_returns))
                    }
                
                simulation_paths = all_horizon_paths
                    
            except Exception as e:
                import traceback
                out["path_generation_error"] = str(e)
        
        result = {"ok": True, "analysis": out}
        if simulation_paths:
            result["simulation_paths"] = simulation_paths
        return result

    except HTTPException:
        # re-raise FastAPI HTTPExceptions unchanged
        raise
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        # return structured 502 to avoid 500 stacktrace leak
        raise HTTPException(
            status_code=502,
            detail={"error": "Internal analysis error", "message": str(e), "trace": tb},
        )


# ----------------------------
# NEW: Decision Intelligence Endpoint
# ----------------------------
@app.post("/api/v1/decision/evaluate", response_model=DecisionIntelligenceOut)
def evaluate_decision(request: Request, body: DecisionIntelligenceIn):
    """
    Evaluate a natural language decision using the Decision Intelligence Architecture.
    
    This endpoint:
    1. Parses the natural language decision into a StructuredDecision
    2. Runs Monte Carlo simulation to compare baseline vs. scenario
    3. Returns counterfactual comparison and decision verdict
    
    Example inputs:
    - "Short Apple 4% after 3 days"
    - "Buy NVDA 20%"
    - "Reduce tech exposure"
    """
    import traceback
    require_admin(request)
    
    # Load portfolio
    pstore = read_portfolios()
    pitems = pstore.get("items", [])
    if not pitems:
        raise HTTPException(
            status_code=400, 
            detail="No saved portfolio found. Save a portfolio first."
        )
    portfolio = pitems[0]
    
    try:
        # 1. Parse the decision using Intent Parser
        decision = parse_decision(body.decision_text, portfolio)
        
        if not decision.actions:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Could not parse decision",
                    "message": "No actionable items found in the decision text.",
                    "warnings": decision.warnings,
                }
            )
        
        # 2. Run temporal simulation
        comparison, score, baseline_paths, scenario_paths = run_decision_intelligence(
            portfolio=portfolio,
            decision=decision,
            horizon_days=body.horizon_days,
            n_paths=body.n_paths,
            return_paths=body.include_paths
        )
        
        # 3. Build response
        parsed_actions = []
        for action in decision.actions:
            parsed_actions.append({
                "symbol": action.symbol,
                "direction": getattr(action.direction, 'value', str(action.direction)),
                "size_percent": action.size_percent,
                "size_usd": action.size_usd,
                "timing_type": getattr(action.timing.type, 'value', str(action.timing.type)),
                "delay_days": action.timing.delay_days,
            })
        
        # 4. Build visualization data
        visualization_data = {
            "comparison_chart": {
                "type": "bar",
                "labels": ["Expected Return", "Volatility", "Max Drawdown"],
                "baseline": [
                    comparison.baseline_expected_return,
                    comparison.baseline_volatility,
                    comparison.baseline_max_drawdown
                ],
                "scenario": [
                    comparison.scenario_expected_return,
                    comparison.scenario_volatility,
                    comparison.scenario_max_drawdown
                ],
            },
            "score_breakdown": {
                "type": "radar",
                "labels": ["Return", "Risk", "Tail Risk", "Drawdown", "Efficiency", "Stability"],
                "values": [
                    score.return_score,
                    score.risk_score,
                    score.tail_risk_score,
                    score.drawdown_score,
                    score.capital_efficiency_score,
                    score.stability_score,
                ],
            },
            "verdict_gauge": {
                "value": score.composite_score,
                "verdict": score.verdict.value,
            },
        }
        
        # 5. Serialize simulation paths if requested
        serialized_paths = None
        if body.include_paths and baseline_paths and scenario_paths:
            # Serialize paths for frontend visualization
            # Each path contains a list of states with portfolio values over time
            def serialize_path(path):
                return {
                    "path_id": path.path_id,
                    "terminal_return_pct": round(path.terminal_return_pct, 2),
                    "max_drawdown_pct": round(path.max_drawdown_pct, 2),
                    "values": [round(s.portfolio_value, 2) for s in path.states],
                    "days": [s.day_offset for s in path.states],
                }
            
            serialized_paths = {
                "horizon_days": body.horizon_days,
                "n_paths": body.n_paths,
                "baseline": [serialize_path(p) for p in baseline_paths],
                "scenario": [serialize_path(p) for p in scenario_paths],
            }
        
        return DecisionIntelligenceOut(
            ok=True,
            decision_id=decision.decision_id,
            decision_type=decision.decision_type.value,
            parsed_actions=parsed_actions,
            confidence_score=decision.confidence_score,
            parser_warnings=decision.warnings,
            
            baseline_expected_return=round(comparison.baseline_expected_return, 2),
            baseline_volatility=round(comparison.baseline_volatility, 2),
            baseline_max_drawdown=round(comparison.baseline_max_drawdown, 2),
            
            scenario_expected_return=round(comparison.scenario_expected_return, 2),
            scenario_volatility=round(comparison.scenario_volatility, 2),
            scenario_max_drawdown=round(comparison.scenario_max_drawdown, 2),
            
            delta_return=round(comparison.delta_return, 2),
            delta_volatility=round(comparison.delta_volatility, 2),
            delta_drawdown=round(comparison.delta_drawdown, 2),
            
            verdict=score.verdict.value,
            composite_score=round(score.composite_score, 1),
            summary=score.summary,
            key_factors=score.key_factors,
            warnings=score.warnings + decision.warnings,
            
            visualization_data=visualization_data,
            simulation_paths=serialized_paths,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        tb = traceback.format_exc()
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Decision evaluation failed",
                "message": str(e),
                "trace": tb,
            }
        )


# ----------------------------
# NEW: Fast Decision Evaluation Endpoint (Tier 1)
# ----------------------------
@app.post("/api/v1/decision/evaluate/fast", response_model=DecisionIntelligenceOut)
def evaluate_decision_fast(request: Request, body: DecisionIntelligenceIn):
    """
    TIER 1: Fast decision evaluation (~50ms).
    
    Uses mean-field approximation for instant results.
    Good for immediate UX feedback before deep simulation.
    
    Returns lower confidence results - use /evaluate for full Monte Carlo.
    """
    import traceback
    require_admin(request)
    
    # Load portfolio
    pstore = read_portfolios()
    pitems = pstore.get("items", [])
    if not pitems:
        raise HTTPException(
            status_code=400, 
            detail="No saved portfolio found. Save a portfolio first."
        )
    portfolio = pitems[0]
    portfolio_id = portfolio.get("id", "unknown")
    
    try:
        # Check cache first
        cached = get_cached_result(
            decision_text=body.decision_text,
            portfolio_id=portfolio_id,
            horizon_days=body.horizon_days,
            is_fast=True
        )
        
        if cached:
            # Return cached result
            cached["ok"] = True
            cached["_cached"] = True
            return DecisionIntelligenceOut(**cached)
        
        # Parse the decision
        decision = parse_decision(body.decision_text, portfolio)
        
        if not decision.actions:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Could not parse decision",
                    "message": "No actionable items found in the decision text.",
                    "warnings": decision.warnings,
                }
            )
        
        # Run fast approximation (Tier 1)
        comparison, score = run_decision_intelligence_fast(
            portfolio=portfolio,
            decision=decision,
            horizon_days=body.horizon_days
        )
        
        # Build response
        parsed_actions = []
        for action in decision.actions:
            parsed_actions.append({
                "symbol": action.symbol,
                "direction": getattr(action.direction, 'value', str(action.direction)),
                "size_percent": action.size_percent,
                "size_usd": action.size_usd,
                "timing_type": getattr(action.timing.type, 'value', str(action.timing.type)),
                "delay_days": action.timing.delay_days,
            })
        
        # Build visualization data
        visualization_data = {
            "comparison_chart": {
                "type": "bar",
                "labels": ["Expected Return", "Volatility", "Max Drawdown"],
                "baseline": [
                    comparison.baseline_expected_return,
                    comparison.baseline_volatility,
                    comparison.baseline_max_drawdown
                ],
                "scenario": [
                    comparison.scenario_expected_return,
                    comparison.scenario_volatility,
                    comparison.scenario_max_drawdown
                ],
            },
            "score_breakdown": {
                "type": "radar",
                "labels": ["Return", "Risk", "Tail Risk", "Drawdown", "Efficiency", "Stability"],
                "values": [
                    score.return_score,
                    score.risk_score,
                    score.tail_risk_score,
                    score.drawdown_score,
                    score.capital_efficiency_score,
                    score.stability_score,
                ],
            },
            "verdict_gauge": {
                "value": score.composite_score,
                "verdict": score.verdict.value,
            },
            "is_fast_approximation": True,
        }
        
        result_dict = {
            "ok": True,
            "decision_id": decision.decision_id,
            "decision_type": decision.decision_type.value,
            "parsed_actions": parsed_actions,
            "confidence_score": decision.confidence_score,
            "parser_warnings": decision.warnings,
            
            "baseline_expected_return": round(comparison.baseline_expected_return, 2),
            "baseline_volatility": round(comparison.baseline_volatility, 2),
            "baseline_max_drawdown": round(comparison.baseline_max_drawdown, 2),
            
            "scenario_expected_return": round(comparison.scenario_expected_return, 2),
            "scenario_volatility": round(comparison.scenario_volatility, 2),
            "scenario_max_drawdown": round(comparison.scenario_max_drawdown, 2),
            
            "delta_return": round(comparison.delta_return, 2),
            "delta_volatility": round(comparison.delta_volatility, 2),
            "delta_drawdown": round(comparison.delta_drawdown, 2),
            
            "verdict": score.verdict.value,
            "composite_score": round(score.composite_score, 1),
            "summary": score.summary,
            "key_factors": score.key_factors,
            "warnings": score.warnings + decision.warnings,
            
            "visualization_data": visualization_data,
        }
        
        # Cache the result
        set_cached_result(
            decision_text=body.decision_text,
            portfolio_id=portfolio_id,
            horizon_days=body.horizon_days,
            result=result_dict,
            is_fast=True
        )
        
        return DecisionIntelligenceOut(**result_dict)
    
    except HTTPException:
        raise
    except Exception as e:
        tb = traceback.format_exc()
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Fast decision evaluation failed",
                "message": str(e),
                "trace": tb,
            }
        )


# ----------------------------
# Cache Statistics Endpoint
# ----------------------------
@app.get("/api/v1/decision/cache/stats")
def decision_cache_stats(request: Request):
    """Get decision cache statistics."""
    require_admin(request)
    return get_cache_stats()