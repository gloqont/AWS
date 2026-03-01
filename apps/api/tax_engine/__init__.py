"""
GLOQONT Tax Engine — Institutional-Grade, Multi-Jurisdiction Tax Intelligence

Architecture:
- TaxEngine: Factory that dispatches to jurisdiction-specific strategies
- TaxProfile: Investor residency, income, filing status
- PortfolioTaxContext: Account type, holding period simulation
- TaxImpact: Calculated result with layered breakdown
"""

from tax_engine.models import (
    TaxProfile,
    PortfolioTaxContext,
    TaxImpact,
    TaxLayer,
    AssetClass,
    AccountType,
    HoldingPeriod,
    FilingStatus,
    IncomeTier,
)
from tax_engine.core import TaxEngine

__all__ = [
    "TaxEngine",
    "TaxProfile",
    "PortfolioTaxContext",
    "TaxImpact",
    "TaxLayer",
    "AssetClass",
    "AccountType",
    "HoldingPeriod",
    "FilingStatus",
    "IncomeTier",
]
