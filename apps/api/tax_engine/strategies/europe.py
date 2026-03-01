"""
GLOQONT Tax Engine — European Strategies

Per-country modeling (NOT "Europe" as one regime).

Germany: Flat 25% + 5.5% Solidarity Surcharge ≈ 26.375%
France:  Flat 30% (12.8% income tax + 17.2% social charges)
UK:      CGT allowance, then 10%/20% based on income
Netherlands: Box 3 "deemed return" wealth tax (unique model)
"""

from typing import List
from tax_engine.core import AbstractTaxStrategy
from tax_engine.models import (
    TaxProfile, PortfolioTaxContext, TransactionDetail,
    TaxLayer, HoldingPeriod, AssetClass, AccountType, IncomeTier,
    RiskSignal, RiskSignalSeverity, TaxImpact
)


# ═══════════════════════════════════════════════
# 🇩🇪 GERMANY
# ═══════════════════════════════════════════════

GERMANY_FLAT_RATE = 0.25
GERMANY_SOLI_RATE = 0.055  # 5.5% of the tax (not of gains)
# Church tax: ~8-9% of tax (optional, ignored for demo)
# Effective = 25% + (25% × 5.5%) = 26.375%
GERMANY_EFFECTIVE_RATE = GERMANY_FLAT_RATE * (1 + GERMANY_SOLI_RATE)  # ~26.375%

# Saver's allowance (Sparerpauschbetrag): €1,000 single / €2,000 married
GERMANY_ALLOWANCE_SINGLE = 1100.0  # ~$1,100 (€1,000)
GERMANY_ALLOWANCE_MARRIED = 2200.0


class GermanyTaxStrategy(AbstractTaxStrategy):
    """Germany: Flat 25% + Solidarity Surcharge. No holding period benefit."""

    JURISDICTION_CODE = "DE"
    JURISDICTION_NAME = "Germany"
    TAX_EXEMPT_ACCOUNTS = set()
    TAX_DEFERRED_ACCOUNTS = set()

    def calculate_transaction_taxes(self, txn: TransactionDetail, profile: TaxProfile) -> List[TaxLayer]:
        return []

    def calculate_realization_taxes(self, txn: TransactionDetail, profile: TaxProfile, holding: HoldingPeriod, gain: float) -> List[TaxLayer]:
        layers: List[TaxLayer] = []
        if gain <= 0:
            return layers

        # Apply Saver's Allowance
        from tax_engine.models import FilingStatus
        allowance = (
            GERMANY_ALLOWANCE_MARRIED
            if profile.filing_status == FilingStatus.MARRIED_JOINT
            else GERMANY_ALLOWANCE_SINGLE
        )
        taxable = max(0, gain - allowance)

        if taxable <= 0:
            layers.append(TaxLayer(
                name="Abgeltungssteuer (Exempt)",
                rate=0.0,
                amount=0.0,
                description=f"Gain of ${gain:,.0f} within Sparerpauschbetrag (€1,000 allowance)",
                applies_to="realized_gain",
            ))
            return layers

        # Flat tax
        flat_tax = taxable * GERMANY_FLAT_RATE
        layers.append(TaxLayer(
            name="Abgeltungssteuer",
            rate=GERMANY_FLAT_RATE * 100,
            amount=round(flat_tax, 2),
            description=f"Flat 25% capital gains tax on ${taxable:,.0f} (after €1K allowance)",
            applies_to="realized_gain",
        ))

        # Solidarity surcharge on the tax
        soli = flat_tax * GERMANY_SOLI_RATE
        layers.append(TaxLayer(
            name="Solidaritätszuschlag",
            rate=round(GERMANY_SOLI_RATE * GERMANY_FLAT_RATE * 100, 2),
            amount=round(soli, 2),
            description=f"5.5% solidarity surcharge on tax amount",
            applies_to="tax_amount",
        ))

        return layers


# ═══════════════════════════════════════════════
# 🇫🇷 FRANCE
# ═══════════════════════════════════════════════

FRANCE_INCOME_TAX_RATE = 0.128     # 12.8%
FRANCE_SOCIAL_CHARGES_RATE = 0.172  # 17.2%
FRANCE_FLAT_TAX = FRANCE_INCOME_TAX_RATE + FRANCE_SOCIAL_CHARGES_RATE  # 30%


class FranceTaxStrategy(AbstractTaxStrategy):
    """France: Prélèvement Forfaitaire Unique (PFU) — Flat 30%."""

    JURISDICTION_CODE = "FR"
    JURISDICTION_NAME = "France"
    TAX_EXEMPT_ACCOUNTS = set()
    TAX_DEFERRED_ACCOUNTS = set()

    def calculate_transaction_taxes(self, txn: TransactionDetail, profile: TaxProfile) -> List[TaxLayer]:
        return []

    def calculate_realization_taxes(self, txn: TransactionDetail, profile: TaxProfile, holding: HoldingPeriod, gain: float) -> List[TaxLayer]:
        layers: List[TaxLayer] = []
        if gain <= 0:
            return layers

        # Income tax component
        income_tax = gain * FRANCE_INCOME_TAX_RATE
        layers.append(TaxLayer(
            name="PFU — Income Tax",
            rate=FRANCE_INCOME_TAX_RATE * 100,
            amount=round(income_tax, 2),
            description="Prélèvement Forfaitaire Unique income tax component (12.8%)",
            applies_to="realized_gain",
        ))

        # Social charges
        social = gain * FRANCE_SOCIAL_CHARGES_RATE
        layers.append(TaxLayer(
            name="PFU — Social Charges",
            rate=FRANCE_SOCIAL_CHARGES_RATE * 100,
            amount=round(social, 2),
            description="Prélèvements sociaux (CSG + CRDS) at 17.2%",
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

        # 1. Linear Tax Compression
        signals.append(RiskSignal(
            title="Flat Tax Impact",
            severity=RiskSignalSeverity.MEDIUM,
            expected_return_drag_pct=-round(FRANCE_FLAT_TAX * 100, 2),
            tail_loss_delta_pct=round(FRANCE_FLAT_TAX * 100 * 0.1, 2),
            mechanism="France applies a flat 30% tax (PFU) on your gains."
        ))

        # 2. High Social Charge Drag
        signals.append(RiskSignal(
            title="High Social Security Contributions",
            severity=RiskSignalSeverity.MEDIUM,
            expected_return_drag_pct=-round(FRANCE_SOCIAL_CHARGES_RATE * 100, 2),
            mechanism="A large portion of your tax (17.2%) goes to social charges (CSG/CRDS)."
        ))

        return signals

# ═══════════════════════════════════════════════
# 🇬🇧 UNITED KINGDOM
# ═══════════════════════════════════════════════

# Annual CGT Allowance (2024-25: £3,000 ≈ $3,800)
UK_CGT_ALLOWANCE = 3800.0

# CGT rates depend on income band
UK_CGT_RATES = {
    IncomeTier.LOW: 0.10,        # Basic rate
    IncomeTier.MEDIUM: 0.10,     # Basic rate
    IncomeTier.HIGH: 0.20,       # Higher rate
    IncomeTier.VERY_HIGH: 0.20,  # Additional rate
}

# UK SDRT
UK_SDRT_RATE = 0.005 # 0.5% on buy

class UKTaxStrategy(AbstractTaxStrategy):
    """UK: Annual CGT allowance, then 10%/20% based on income."""

    JURISDICTION_CODE = "GB"
    JURISDICTION_NAME = "United Kingdom"

    TAX_EXEMPT_ACCOUNTS = {AccountType.ISA}
    TAX_DEFERRED_ACCOUNTS = {AccountType.SIPP}
    
    def calculate_transaction_taxes(self, txn: TransactionDetail, profile: TaxProfile) -> List[TaxLayer]:
        """
        UK Transaction Taxes:
        - Stamp Duty Reserve Tax (SDRT): 0.5% on Buy for UK shares.
        """
        layers = []
        if txn.direction.lower() in {"buy", "increase", "add", "long"}:
             # Apply SDRT
             sdrt = txn.transaction_value_usd * UK_SDRT_RATE
             layers.append(TaxLayer(
                 name="SDRT",
                 rate=UK_SDRT_RATE * 100,
                 amount=round(sdrt, 2),
                 description="Stamp Duty Reserve Tax on UK share purchases",
                 applies_to="transaction_value"
             ))
        return layers

    def calculate_realization_taxes(self, txn: TransactionDetail, profile: TaxProfile, holding: HoldingPeriod, gain: float) -> List[TaxLayer]:
        layers: List[TaxLayer] = []
        if gain <= 0:
            return layers

        # Annual exempt amount (simplified: applied to this txn if valid, strictly should track YTD)
        taxable = max(0, gain - UK_CGT_ALLOWANCE)

        if taxable <= 0:
            layers.append(TaxLayer(
                name="CGT (Within Allowance)",
                rate=0.0,
                amount=0.0,
                description=f"Gain of ${gain:,.0f} within annual CGT allowance (£3,000)",
                applies_to="realized_gain",
            ))
            return layers

        rate = UK_CGT_RATES.get(profile.income_tier, 0.20)
        layers.append(TaxLayer(
            name="Capital Gains Tax",
            rate=rate * 100,
            amount=round(taxable * rate, 2),
            description=(
                f"UK CGT at {rate*100:.0f}% on ${taxable:,.0f} "
                f"(after £3,000 annual allowance)"
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
        
        # 1. Allowance Utilization
        gain = tax_impact.estimated_gain_usd
        if gain > 0:
            if gain < UK_CGT_ALLOWANCE:
                buffer_left = UK_CGT_ALLOWANCE - gain
                signals.append(RiskSignal(
                    title="Tax-Free Allowance Available",
                    severity=RiskSignalSeverity.LOW,
                    available_offset_usd=round(buffer_left, 2),
                    risk_dampening_potential_pct=100.0,
                    mechanism="You still have room in your £3,000 tax-free Capital Gains limit."
                ))

            # 2. Income Band Sensitivity
            cg_rate = UK_CGT_RATES.get(profile.income_tier, 0.20)
            if cg_rate > 0.10:
                signals.append(RiskSignal(
                    title="Higher Capital Gains Bracket",
                    severity=RiskSignalSeverity.MEDIUM,
                    expected_return_drag_pct=-round(cg_rate * 100, 2),
                    mechanism="Your income pushes your Capital Gains Tax rate from 10% up to 20%."
                ))

        # 3. Stamp Duty Friction
        sdrt_layers = [l for l in tax_impact.layers if l.name == "SDRT"]
        if sdrt_layers:
            signals.append(RiskSignal(
                title="Stamp Duty Reserve Tax (SDRT)",
                severity=RiskSignalSeverity.LOW,
                expected_return_drag_pct=-round(UK_SDRT_RATE * 100, 2),
                volatility_impact_pct=0.1,
                mechanism="You lose 0.5% automatically just for buying UK shares."
            ))

        return signals

# ═══════════════════════════════════════════════
# 🇳🇱 NETHERLANDS
# ═══════════════════════════════════════════════

# Box 3: Deemed return taxation (wealth tax, not actual gains)
# As of 2024: Tax on distribution of assets across categories
# Savings: deemed return ~0.36%, Investments: ~6.17%
# Tax rate on deemed return: 36%

NL_DEEMED_RETURN_INVESTMENT = 0.0617  # 6.17% deemed return on investments
NL_DEEMED_RETURN_SAVINGS = 0.0036     # 0.36% on savings
NL_BOX3_TAX_RATE = 0.36              # 36% tax on deemed return
NL_EXEMPT_THRESHOLD = 57000.0         # ~€57,000 exempt (single) ≈ $62,000
NL_EXEMPT_THRESHOLD_PARTNER = 114000.0


class NetherlandsTaxStrategy(AbstractTaxStrategy):
    """Netherlands: Box 3 deemed return (wealth tax), NOT actual gains tax.
    
    This is fundamentally different from other jurisdictions.
    Tax = Box3Rate × DeemedReturn × InvestmentValue
    """

    JURISDICTION_CODE = "NL"
    JURISDICTION_NAME = "Netherlands"
    TAX_EXEMPT_ACCOUNTS = set()
    TAX_DEFERRED_ACCOUNTS = set()

    def calculate_transaction_taxes(self, txn: TransactionDetail, profile: TaxProfile) -> List[TaxLayer]:
        return []

    def calculate_realization_taxes(self, txn: TransactionDetail, profile: TaxProfile, holding: HoldingPeriod, gain: float) -> List[TaxLayer]:
        # NOTE: NL taxes PORTFOLIO VALUE, not realized gains.
        # However, for the "realization" hook, we might return 0 or re-calculate Box 3 based on txn value.
        # But wait, Box 3 is annual. 
        # For a "Sell" event, there is NO tax triggered. It is "wealth tax" measured on Jan 1.
        # So Realization Tax = 0.
        
        # But we want to show the user the *ongoing* cost.
        # In abstract strategy, we separated Transaction vs Realization.
        # Box 3 is neither typical transaction nor realization. It's holding cost.
        # But we can model it as a realization cost for simulation purposes (annualized) or just show it 
        # as a "Wealth Tax" layer that applies pro-rata.
        
        # Let's keep the logic we had: use transaction value (portfolio proxy) to estimate Box 3 impact.
        # And since it triggers on "Holding", maybe we return it here? 
        # Or better: The base class `calculate` calls `calculate_realization_taxes` on SELL.
        # If we sell, we don't pay tax.
        
        # However, if we BUY, we increase wealth -> increase annual tax.
        # If we SELL, we just convert Inv -> Cash. If Cash deemed return is lower, tax decreases.
        
        # For simplicity in this engine which focuses on "Tax Liability of this Trade",
        # let's show the Box 3 liability as an "Annual Holding Cost" regardless.
        
        # Use txn.transaction_value_usd to mean "Asset Value Involved".
        
        layers: List[TaxLayer] = []
        
        # Reuse existing logic but adapt to new method signature
        # We need portfolio value but we only have txn.
        # We will assume txn.total_value represents the chunk we are analyzing.
        
        # Check exemption
        from tax_engine.models import FilingStatus
        threshold = (
            NL_EXEMPT_THRESHOLD_PARTNER
            if profile.filing_status == FilingStatus.MARRIED_JOINT
            else NL_EXEMPT_THRESHOLD
        )
        
        # Simplified: We treat the transaction amount as marginal wealth added/removed.
        # So we ignore threshold for the *marginal* calculation unless we know total portfolio.
        # Assuming user is above threshold for conservative estimate.
        
        deemed_return = txn.transaction_value_usd * NL_DEEMED_RETURN_INVESTMENT
        tax = deemed_return * NL_BOX3_TAX_RATE
        
        layers.append(TaxLayer(
            name="Box 3 Wealth Tax (Annual)",
            rate=round(NL_DEEMED_RETURN_INVESTMENT * NL_BOX3_TAX_RATE * 100, 2),
            amount=round(tax, 2),
            description=(
                f"Est. Annual Box 3 Tax on this asset value: "
                f"${tax:,.2f} ({NL_DEEMED_RETURN_INVESTMENT*100:.2f}% deemed return × 36% tax)"
            ),
            applies_to="portfolio_value",
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

        eff_rate = NL_DEEMED_RETURN_INVESTMENT * NL_BOX3_TAX_RATE
        
        # 1. Wealth Floor Risk
        signals.append(RiskSignal(
            title="Annual Wealth Tax (Box 3)",
            severity=RiskSignalSeverity.HIGH,
            tail_loss_delta_pct=round(eff_rate * 100, 2), # increases baseline drawdown
            mechanism="You are taxed every year on your total investments in the Netherlands, even if you never sell."
        ))

        signals.append(RiskSignal(
            title="High Assumed Returns Tax",
            severity=RiskSignalSeverity.MEDIUM,
            expected_return_drag_pct=-round(eff_rate * 100, 2),
            mechanism="The tax office assumes you make 6.17% on investments and taxes that imaginary gain at 36%."
        ))

        return signals
