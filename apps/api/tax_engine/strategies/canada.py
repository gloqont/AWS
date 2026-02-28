"""
GLOQONT Tax Engine — Canada Strategy

Federal + Provincial, with 50% inclusion rate.

Capital Gains:
- Only 50% of the gain is taxable ("inclusion rate")
- Taxed at combined federal + provincial marginal rate

Dividends:
- Eligible: Gross-up + tax credit mechanism
- Non-eligible: Different rate (simplified)

Accounts:
- TFSA: Tax-free
- RRSP: Tax-deferred
- RESP: Education savings
"""

from typing import List
from tax_engine.core import AbstractTaxStrategy
from tax_engine.models import (
    TaxProfile, PortfolioTaxContext, TransactionDetail,
    TaxLayer, HoldingPeriod, AssetClass, AccountType, IncomeTier,
    RiskSignal, RiskSignalSeverity, TaxImpact
)


# ─────────────────────────────────────────────
# Canada Rates
# ─────────────────────────────────────────────

INCLUSION_RATE = 0.50  # Only 50% of capital gain is taxable

# Combined Federal + Provincial marginal rates (simplified by tier)
# Federal top rate: 33%, Provincial varies
COMBINED_MARGINAL_RATES = {
    # Province -> {income_tier -> combined rate}
    "ON": {  # Ontario
        IncomeTier.LOW: 0.2005,
        IncomeTier.MEDIUM: 0.2965,
        IncomeTier.HIGH: 0.4616,
        IncomeTier.VERY_HIGH: 0.5353,
    },
    "QC": {  # Quebec
        IncomeTier.LOW: 0.2753,
        IncomeTier.MEDIUM: 0.3752,
        IncomeTier.HIGH: 0.4997,
        IncomeTier.VERY_HIGH: 0.5331,
    },
    "AB": {  # Alberta
        IncomeTier.LOW: 0.25,
        IncomeTier.MEDIUM: 0.305,
        IncomeTier.HIGH: 0.41,
        IncomeTier.VERY_HIGH: 0.48,
    },
    "BC": {  # British Columbia
        IncomeTier.LOW: 0.2006,
        IncomeTier.MEDIUM: 0.2885,
        IncomeTier.HIGH: 0.408,
        IncomeTier.VERY_HIGH: 0.5350,
    },
    "MB": {  # Manitoba
        IncomeTier.LOW: 0.2580,
        IncomeTier.MEDIUM: 0.2780,
        IncomeTier.HIGH: 0.4340,
        IncomeTier.VERY_HIGH: 0.5040,
    },
    "SK": {  # Saskatchewan
        IncomeTier.LOW: 0.2550,
        IncomeTier.MEDIUM: 0.2800,
        IncomeTier.HIGH: 0.4050,
        IncomeTier.VERY_HIGH: 0.4750,
    },
}

# Default (if province not specified)
DEFAULT_MARGINAL_RATES = {
    IncomeTier.LOW: 0.20,
    IncomeTier.MEDIUM: 0.30,
    IncomeTier.HIGH: 0.43,
    IncomeTier.VERY_HIGH: 0.50,
}


class CanadaTaxStrategy(AbstractTaxStrategy):
    """Canada tax strategy: 50% inclusion rate, Federal + Provincial."""

    JURISDICTION_CODE = "CA"
    JURISDICTION_NAME = "Canada"

    TAX_EXEMPT_ACCOUNTS = {AccountType.TFSA}
    TAX_DEFERRED_ACCOUNTS = {AccountType.RRSP, AccountType.RESP}

    def calculate_transaction_taxes(self, txn: TransactionDetail, profile: TaxProfile) -> List[TaxLayer]:
        """
        Canada Transaction Taxes:
        - Generally none for standard trading on major exchanges.
        """
        return []

    def calculate_realization_taxes(self, txn: TransactionDetail, profile: TaxProfile, holding: HoldingPeriod, gain: float) -> List[TaxLayer]:
        """
        Canada Realization Taxes (Capital Gains):
        - 50% inclusion rate (only 50% of gain is taxable)
        - Taxed at marginal rate (Federal + Provincial)
        """
        layers: List[TaxLayer] = []
        if gain <= 0:
            return layers

        # ── 1. Apply Inclusion Rate ──
        taxable_gain = gain * INCLUSION_RATE

        # ── 2. Get combined marginal rate ──
        province = profile.sub_jurisdiction or "ON"  # Default Ontario
        province_rates = COMBINED_MARGINAL_RATES.get(province, DEFAULT_MARGINAL_RATES)
        marginal_rate = province_rates.get(profile.income_tier, 0.30)

        # ── 3. Effective rate = inclusion × marginal ──
        effective_rate = INCLUSION_RATE * marginal_rate
        tax_amount = gain * effective_rate # or taxable_gain * marginal_rate

        province_name = {
            "ON": "Ontario", "QC": "Quebec", "AB": "Alberta",
            "BC": "British Columbia", "MB": "Manitoba", "SK": "Saskatchewan",
        }.get(province, province)

        layers.append(TaxLayer(
            name=f"Capital Gains ({province_name})",
            rate=effective_rate * 100,
            amount=round(tax_amount, 2),
            description=(
                f"50% inclusion rate × {marginal_rate*100:.1f}% combined marginal rate "
                f"(Federal + {province_name}). Effective CG rate: {effective_rate*100:.1f}%"
            ),
            applies_to="realized_gain",
        ))

        return layers

    def generate_signals(
        self,
        profile: TaxProfile,
        portfolio_ctx: PortfolioTaxContext,
        transactions: List[TransactionDetail],
        tax_impact: TaxImpact,
    ) -> List[RiskSignal]:
        signals: List[RiskSignal] = []
        if tax_impact.total_tax_liability <= 0:
            return signals

        # 1. Inclusion Cushion Signal
        # Because only 50% of the gain is taxable, after-tax volatility forms a milder dampening effect
        # compared to 100% inclusion regimes (like US short-term).
        province = profile.sub_jurisdiction or "ON"
        province_rates = COMBINED_MARGINAL_RATES.get(province, DEFAULT_MARGINAL_RATES)
        marginal_rate = province_rates.get(profile.income_tier, 0.30)
        
        expected_drag = round(tax_impact.effective_tax_rate, 2)

        signals.append(RiskSignal(
            title="Inclusion Cushion Signal",
            severity=RiskSignalSeverity.LOW,
            expected_return_drag_pct=-expected_drag,
            tail_loss_delta_pct=round(expected_drag * 0.5, 2), # 50% inclusion softens the blow
            mechanism="50% Inclusion Rate dampens after-tax volatility"
        ))

        # 2. Provincial Amplification
        if marginal_rate > 0.45:
            signals.append(RiskSignal(
                title="Provincial Amplification",
                severity=RiskSignalSeverity.MEDIUM,
                expected_return_drag_pct=-round(marginal_rate * INCLUSION_RATE * 100, 2),
                mechanism=f"High provincial marginal rate ({province})"
            ))

        return signals
