"""
GLOQONT Tax Engine — Data Models

Institutional-grade tax modeling requires understanding:
1. Jurisdiction (Country + Sub-jurisdiction)
2. Investor Profile (Income, Filing Status)
3. Account Wrapper (Taxable, Tax-Deferred, Tax-Free)
4. Asset Classification (Equity, Debt, Crypto, Options, ETF, REIT)
5. Holding Period (Short-Term vs Long-Term)
6. Transaction Type (Sale, Dividend, Interest, Distribution)
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ─────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────

class AssetClass(str, Enum):
    """Asset classification for tax treatment routing."""
    EQUITY_DOMESTIC = "equity_domestic"
    EQUITY_FOREIGN = "equity_foreign"
    DEBT_FUND = "debt_fund"
    BOND = "bond"
    MUNICIPAL_BOND = "municipal_bond"
    CRYPTO = "crypto"
    OPTIONS = "options"
    FUTURES = "futures"
    ETF = "etf"
    REIT = "reit"
    GOLD = "gold"
    REAL_ESTATE = "real_estate"
    UNKNOWN = "unknown"


class AccountType(str, Enum):
    """Account wrapper determines tax treatment."""
    # Universal
    TAXABLE = "taxable"
    # USA
    IRA_TRADITIONAL = "ira_traditional"       # Tax-deferred
    IRA_ROTH = "ira_roth"                     # Tax-free withdrawal
    ACCOUNT_401K = "401k"                     # Tax-deferred
    HSA = "hsa"                               # Tax-advantaged
    # Canada
    TFSA = "tfsa"                             # Tax-Free Savings Account
    RRSP = "rrsp"                             # Registered Retirement Savings Plan
    RESP = "resp"                             # Registered Education Savings Plan
    # India
    NPS = "nps"                               # National Pension System
    PPF = "ppf"                               # Public Provident Fund
    ELSS = "elss"                             # Equity Linked Savings Scheme
    DEMAT = "demat"                           # Standard Demat (Taxable)
    # UK
    ISA = "isa"                               # Individual Savings Account
    SIPP = "sipp"                             # Self-Invested Personal Pension


class HoldingPeriod(str, Enum):
    """Simulated holding period for tax rate determination."""
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"


class FilingStatus(str, Enum):
    """Tax filing status (primarily US, but applicable elsewhere)."""
    SINGLE = "single"
    MARRIED_JOINT = "married_joint"
    MARRIED_SEPARATE = "married_separate"
    HEAD_OF_HOUSEHOLD = "head_of_household"
    # India
    INDIVIDUAL = "individual"
    HUF = "huf"
    # Generic
    OTHER = "other"


class IncomeTier(str, Enum):
    """Simplified income tier for demo purposes.
    Maps to actual brackets in each jurisdiction's strategy."""
    LOW = "low"           # Bottom bracket
    MEDIUM = "medium"     # Middle bracket
    HIGH = "high"         # Top bracket
    VERY_HIGH = "very_high"  # Subject to surcharges (NIIT, etc.)


# ─────────────────────────────────────────────
# Jurisdiction Registry
# ─────────────────────────────────────────────

SUPPORTED_JURISDICTIONS = {
    "US": {
        "name": "United States",
        "sub_jurisdictions": {
            "CA": "California",
            "NY": "New York",
            "TX": "Texas",
            "FL": "Florida",
            "WA": "Washington",
            "IL": "Illinois",
            "NJ": "New Jersey",
            "MA": "Massachusetts",
            "PA": "Pennsylvania",
            "OH": "Ohio",
            "NONE": "No State Tax",
        },
    },
    "IN": {
        "name": "India",
        "sub_jurisdictions": {},  # Uniform central tax
    },
    "CA": {
        "name": "Canada",
        "sub_jurisdictions": {
            "ON": "Ontario",
            "QC": "Quebec",
            "AB": "Alberta",
            "BC": "British Columbia",
            "MB": "Manitoba",
            "SK": "Saskatchewan",
        },
    },
    "DE": {
        "name": "Germany",
        "sub_jurisdictions": {},
    },
    "FR": {
        "name": "France",
        "sub_jurisdictions": {},
    },
    "GB": {
        "name": "United Kingdom",
        "sub_jurisdictions": {},
    },
    "NL": {
        "name": "Netherlands",
        "sub_jurisdictions": {},
    },
}


# ─────────────────────────────────────────────
# Input Models
# ─────────────────────────────────────────────

class TaxProfile(BaseModel):
    """Investor-level tax profile."""
    jurisdiction: str = Field(
        default="US",
        description="ISO country code: US, IN, CA, DE, FR, GB, NL"
    )
    sub_jurisdiction: Optional[str] = Field(
        default=None,
        description="State/Province code: CA, NY, ON, QC, etc."
    )
    filing_status: FilingStatus = Field(default=FilingStatus.SINGLE)
    income_tier: IncomeTier = Field(default=IncomeTier.MEDIUM)
    # For cross-border modeling (future)
    source_country: Optional[str] = Field(
        default=None,
        description="Country where the asset is domiciled (for withholding/DTAA)"
    )


class PortfolioTaxContext(BaseModel):
    """Portfolio-level tax context."""
    account_type: AccountType = Field(default=AccountType.TAXABLE)
    holding_period: HoldingPeriod = Field(
        default=HoldingPeriod.SHORT_TERM,
        description="Simulated holding period (conservative default)"
    )
    total_portfolio_value_usd: float = Field(default=100000.0)
    # Simulated cost basis parameters
    estimated_gain_percent: float = Field(
        default=50.0,
        description="Estimated % of transaction value that is gain (heuristic when no history)"
    )


class TransactionDetail(BaseModel):
    """Per-action transaction detail for tax calculation."""
    symbol: str
    direction: str  # "sell", "buy", etc.
    transaction_value_usd: float = Field(default=0.0)
    asset_class: AssetClass = Field(default=AssetClass.EQUITY_DOMESTIC)
    holding_period: Optional[HoldingPeriod] = Field(
        default=None,
        description="Override per-asset holding period"
    )
    estimated_gain_usd: Optional[float] = Field(
        default=None,
        description="If known, the actual gain"
    )


# ─────────────────────────────────────────────
# Output Models
# ─────────────────────────────────────────────

class TaxLayer(BaseModel):
    """A single layer of tax (e.g., Federal, State, STT, NIIT)."""
    name: str = Field(..., description="Layer name: Federal CG, State CG, STT, NIIT, Soli, etc.")
    rate: float = Field(default=0.0, description="Effective rate applied")
    amount: float = Field(default=0.0, description="Tax amount in USD/local currency")
    description: str = Field(default="", description="Human-readable explanation")
    applies_to: str = Field(
        default="realized_gain",
        description="What base: realized_gain, transaction_value, deemed_return, portfolio_value"
    )
    category: str = Field(
        default="realization",
        description="Category: 'transaction' (friction) or 'realization' (profit-based)"
    )


class TaxImpact(BaseModel):
    """Complete tax impact calculation result."""
    # Totals
    total_tax_liability: float = Field(default=0.0)
    effective_tax_rate: float = Field(default=0.0, description="Total tax / transaction value")
    effective_gain_tax_rate: float = Field(default=0.0, description="Total tax / estimated gain")

    # Layered breakdown
    layers: List[TaxLayer] = Field(default_factory=list)

    # Before/After metrics
    transaction_value_usd: float = Field(default=0.0)
    estimated_gain_usd: float = Field(default=0.0)
    net_proceeds_after_tax: float = Field(default=0.0)
    tax_drag_on_return_pct: float = Field(
        default=0.0,
        description="How much tax reduces the decision's return (percentage points)"
    )

    # Context
    jurisdiction: str = Field(default="")
    jurisdiction_name: str = Field(default="")
    account_type: str = Field(default="taxable")
    holding_period: str = Field(default="short_term")
    asset_class: str = Field(default="equity_domestic")

    # Flags
    is_tax_exempt: bool = Field(default=False, description="True if account type = tax-free")
    is_tax_deferred: bool = Field(default=False, description="True if account type = tax-deferred")
    is_buy_only: bool = Field(default=False, description="True if all actions are BUY — no realization tax applies")
    wash_sale_warning: bool = Field(default=False)
    cross_border_withholding: bool = Field(default=False)

    # Tax regime context
    tax_regime_applied: str = Field(
        default="",
        description="Human-readable regime: 'Short-Term CG', 'Long-Term CG', 'Wealth Tax (Box 3)', etc."
    )
    exit_assumptions: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Exit assumptions when scenario projects realization: trigger, exit_price, holding_period_days, tax_regime"
    )

    # Human summary
    summary: str = Field(default="")
    warnings: List[str] = Field(default_factory=list)


class RiskSignalSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

class RiskSignal(BaseModel):
    """
    Quantified risk signals representing how tax transforms portfolio distributions.
    Replaces qualitative advice.
    """
    title: str = Field(..., description="E.g. 'Realization Sensitivity' or 'Execution Friction Density'")
    severity: RiskSignalSeverity = Field(default=RiskSignalSeverity.LOW)
    
    # Specific quantitative deltas 
    tail_loss_delta_pct: Optional[float] = Field(default=None, description="E.g. 0.18 for +0.18%")
    expected_return_drag_pct: Optional[float] = Field(default=None, description="E.g. -0.25 for -0.25%")
    volatility_impact_pct: Optional[float] = Field(default=None, description="E.g. 0.05 for +0.05%")
    
    mechanism: str = Field(..., description="E.g. 'Short-Term Federal + State Layer'")
    
    # For cushion buffers (e.g. UK allowances, NL wealth tax floors, Canadian TFSA buffers)
    available_offset_usd: Optional[float] = Field(default=None)
    risk_dampening_potential_pct: Optional[float] = Field(default=None)
