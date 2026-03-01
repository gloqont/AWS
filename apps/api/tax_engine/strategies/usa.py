"""
GLOQONT Tax Engine — USA Strategy

Federal + State + NIIT multi-layer tax model.

Federal Capital Gains:
- Short-term (<1yr): Ordinary income rates (10%-37%)
- Long-term (>1yr): 0%, 15%, or 20% depending on income

NIIT: +3.8% for high earners (AGI > $200k single / $250k married)

State: Varies (CA up to 13.3%, NY ~10.9%, TX/FL/WA = 0%)

Special:
- Section 1256 contracts (options/futures): 60% LT / 40% ST blend
- REIT dividends: Ordinary income
- Municipal bonds: Often exempt
- Wash Sale: 30-day repurchase warning
"""

from typing import List
from tax_engine.core import AbstractTaxStrategy
from tax_engine.models import (
    TaxLayer, HoldingPeriod, AssetClass, AccountType, IncomeTier,
    FilingStatus, RiskSignal, RiskSignalSeverity, TaxImpact
)


# ─────────────────────────────────────────────
# Federal Rates
# ─────────────────────────────────────────────

# Long-term CG rates by income tier
FEDERAL_LTCG_RATES = {
    IncomeTier.LOW: 0.0,          # 0% (taxable income < ~$44k single)
    IncomeTier.MEDIUM: 0.15,      # 15% (up to ~$492k single)
    IncomeTier.HIGH: 0.20,        # 20% (above ~$492k)
    IncomeTier.VERY_HIGH: 0.20,   # 20% (+ NIIT)
}

# Short-term CG = ordinary income rates (simplified by tier)
FEDERAL_STCG_RATES = {
    IncomeTier.LOW: 0.12,         # 12% bracket
    IncomeTier.MEDIUM: 0.22,      # 22% bracket
    IncomeTier.HIGH: 0.32,        # 32% bracket
    IncomeTier.VERY_HIGH: 0.37,   # 37% bracket
}

# NIIT threshold check (applied if income > threshold)
NIIT_RATE = 0.038  # 3.8%
NIIT_APPLIES_TO = {IncomeTier.HIGH, IncomeTier.VERY_HIGH}

# ─────────────────────────────────────────────
# State CG Tax Rates (top marginal)
# ─────────────────────────────────────────────

STATE_CG_RATES = {
    "CA": {"rate": 0.133, "name": "California"},
    "NY": {"rate": 0.109, "name": "New York"},
    "NJ": {"rate": 0.1075, "name": "New Jersey"},
    "MA": {"rate": 0.09, "name": "Massachusetts"},
    "IL": {"rate": 0.0495, "name": "Illinois"},
    "PA": {"rate": 0.0307, "name": "Pennsylvania"},
    "OH": {"rate": 0.04, "name": "Ohio"},
    # 0% states
    "TX": {"rate": 0.0, "name": "Texas"},
    "FL": {"rate": 0.0, "name": "Florida"},
    "WA": {"rate": 0.07, "name": "Washington"},  # 7% on LT CG > $250k (new)
    "NONE": {"rate": 0.0, "name": "No State Tax"},
}


class USATaxStrategy(AbstractTaxStrategy):
    """USA tax strategy: Federal + State + NIIT, with asset-class routing."""

    JURISDICTION_CODE = "US"
    JURISDICTION_NAME = "United States"

    TAX_EXEMPT_ACCOUNTS = {AccountType.IRA_ROTH, AccountType.HSA}
    TAX_DEFERRED_ACCOUNTS = {AccountType.IRA_TRADITIONAL, AccountType.ACCOUNT_401K}

    def calculate_transaction_taxes(self, txn: TransactionDetail, profile: TaxProfile) -> List[TaxLayer]:
        """
        USA Transaction Taxes:
        - Generally $0 for standard equities (commission-free brokerage assumed).
        - SEC fees are negligible ($0.000008 rate), so ignored for high-level sim.
        """
        return []

    def calculate_realization_taxes(self, txn: TransactionDetail, profile: TaxProfile, holding: HoldingPeriod, gain: float) -> List[TaxLayer]:
        """
        USA Realization Taxes (Capital Gains):
        - Federal: STCG (ord inc) / LTCG (0/15/20%)
        - NIIT: 3.8%
        - State: Varies
        - Special: §1256, REIT, Muni
        """
        layers: List[TaxLayer] = []
        if gain <= 0:
            return layers

        asset = txn.asset_class

        # ── Asset-class special routing ──

        # Municipal bonds: Tax exempt
        if asset == AssetClass.MUNICIPAL_BOND:
            layers.append(TaxLayer(
                name="Federal CG (Exempt)",
                rate=0.0,
                amount=0.0,
                description="Municipal bond interest/gains are generally federal tax exempt",
                applies_to="realized_gain",
            ))
            return layers

        # Section 1256 contracts (futures, index options): 60% LT / 40% ST blend
        if asset in (AssetClass.FUTURES, AssetClass.OPTIONS):
            layers.extend(
                self._calc_section_1256(profile, gain)
            )
            # NIIT
            niit = self._calc_niit(profile, gain)
            if niit:
                layers.append(niit)
            # State
            state = self._calc_state(profile, gain)
            if state:
                layers.append(state)
            return layers

        # REIT dividends: Taxed as ordinary income
        if asset == AssetClass.REIT:
            rate = FEDERAL_STCG_RATES.get(profile.income_tier, 0.22)
            layers.append(TaxLayer(
                name="REIT Income Tax",
                rate=rate * 100,
                amount=round(gain * rate, 2),
                description=f"REIT distributions taxed as ordinary income ({rate*100:.0f}%)",
                applies_to="realized_gain",
            ))
            niit = self._calc_niit(profile, gain)
            if niit:
                layers.append(niit)
            state = self._calc_state(profile, gain)
            if state:
                layers.append(state)
            return layers

        # Crypto: No special treatment (CG rules apply)
        # Equity / ETF / Bonds / Default: Standard CG

        # ── 1. Federal Capital Gains ──
        if holding == HoldingPeriod.LONG_TERM:
            rate = FEDERAL_LTCG_RATES.get(profile.income_tier, 0.15)
            layers.append(TaxLayer(
                name="Federal LTCG",
                rate=rate * 100,
                amount=round(gain * rate, 2),
                description=f"Long-term capital gains ({rate*100:.0f}%)",
                applies_to="realized_gain",
            ))
        else:
            rate = FEDERAL_STCG_RATES.get(profile.income_tier, 0.22)
            layers.append(TaxLayer(
                name="Federal STCG",
                rate=rate * 100,
                amount=round(gain * rate, 2),
                description=f"Short-term capital gains taxed as ordinary income ({rate*100:.0f}%)",
                applies_to="realized_gain",
            ))

        # ── 2. NIIT ──
        niit = self._calc_niit(profile, gain)
        if niit:
            layers.append(niit)

        # ── 3. State Tax ──
        state = self._calc_state(profile, gain)
        if state:
            layers.append(state)

        return layers

    def _calc_niit(self, profile: TaxProfile, gain: float) -> TaxLayer | None:
        """Net Investment Income Tax: 3.8% for high earners."""
        if profile.income_tier in NIIT_APPLIES_TO:
            return TaxLayer(
                name="NIIT",
                rate=NIIT_RATE * 100,
                amount=round(gain * NIIT_RATE, 2),
                description="Net Investment Income Tax (3.8%) for high-income investors",
                applies_to="realized_gain",
            )
        return None

    def _calc_state(self, profile: TaxProfile, gain: float) -> TaxLayer | None:
        """State capital gains tax."""
        state_code = profile.sub_jurisdiction or "NONE"
        state_info = STATE_CG_RATES.get(state_code, STATE_CG_RATES["NONE"])
        rate = state_info["rate"]
        name = state_info["name"]

        if rate <= 0:
            return None

        return TaxLayer(
            name=f"State CG ({name})",
            rate=rate * 100,
            amount=round(gain * rate, 2),
            description=f"{name} state capital gains tax ({rate*100:.1f}%)",
            applies_to="realized_gain",
        )

    def _calc_section_1256(self, profile: TaxProfile, gain: float) -> List[TaxLayer]:
        """Section 1256: 60% long-term / 40% short-term blend."""
        lt_portion = gain * 0.60
        st_portion = gain * 0.40

        lt_rate = FEDERAL_LTCG_RATES.get(profile.income_tier, 0.15)
        st_rate = FEDERAL_STCG_RATES.get(profile.income_tier, 0.22)

        blended_rate = (0.60 * lt_rate + 0.40 * st_rate)

        return [
            TaxLayer(
                name="§1256 Federal CG (Blended)",
                rate=blended_rate * 100,
                amount=round(lt_portion * lt_rate + st_portion * st_rate, 2),
                description=f"Section 1256: 60% LT ({lt_rate*100:.0f}%) + 40% ST ({st_rate*100:.0f}%)",
                applies_to="realized_gain",
            )
        ]

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

        # 1. Short-Term Realization Risk
        # Triggered if holding period is short term and there's capital gains
        has_short_term = portfolio_ctx.holding_period == HoldingPeriod.SHORT_TERM
        gain = tax_impact.estimated_gain_usd
        if has_short_term and gain > 0:
            # Approximate the drag from the higher tax rate vs long-term
            lt_rate = FEDERAL_LTCG_RATES.get(profile.income_tier, 0.15)
            st_rate = FEDERAL_STCG_RATES.get(profile.income_tier, 0.22)
            spread = max(0, st_rate - lt_rate)
            
            # Additional tail loss delta approx based on the tax spread compressing upside while
            # leaving downside unhedged before year-end. 
            tail_delta = round(spread * 100 * 0.05, 2)  # heuristic representation
            expected_drag = round(tax_impact.effective_tax_rate, 2)
            
            # Severity mapping based on actual drag
            drag_val = abs(expected_drag)
            if drag_val > 0.30:
                sev = RiskSignalSeverity.HIGH
            elif drag_val > 0.10:
                sev = RiskSignalSeverity.MEDIUM
            else:
                sev = RiskSignalSeverity.LOW

            signals.append(RiskSignal(
                title="Extra Short-Term Tax Penalty",
                severity=sev,
                tail_loss_delta_pct=tail_delta,
                expected_return_drag_pct=-expected_drag,
                mechanism=f"Because you haven't held this for a year, you pay higher ordinary income rates."
            ))

        # 2. State Amplification Signal
        state_code = profile.sub_jurisdiction or "NONE"
        state_info = STATE_CG_RATES.get(state_code, STATE_CG_RATES["NONE"])
        rate = state_info["rate"]
        if rate > 0.05:
            # High state tax amplifies drag
            vol_impact = round(rate * 100 * 0.1, 2) # heuristic volatility impact penalty
            signals.append(RiskSignal(
                title="High State Tax Impact",
                severity=RiskSignalSeverity.MEDIUM if rate < 0.10 else RiskSignalSeverity.HIGH,
                expected_return_drag_pct=-round(rate * 100, 2),
                volatility_impact_pct=vol_impact,
                mechanism=f"Your state ({state_code}) charges an additional {rate*100:.1f}% tax on this gain."
            ))

        # 3. NIIT Threshold Exposure
        if profile.income_tier in NIIT_APPLIES_TO:
            signals.append(RiskSignal(
                title="High-Income Surcharge (NIIT)",
                severity=RiskSignalSeverity.HIGH,
                expected_return_drag_pct=-round(NIIT_RATE * 100, 2),
                mechanism="Your income bracket triggers a mandatory 3.8% Medicare investment tax."
            ))
            
        return signals
