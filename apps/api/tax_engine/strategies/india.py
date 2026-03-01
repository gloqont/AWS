"""
GLOQONT Tax Engine — India Strategy

Income Tax Act + STT + GST modeling

Capital Gains:
- Equity (STT paid): STCG 15%, LTCG 10% (above ₹1L, no indexation)
- Debt Funds: Slab rate (post-2023, no indexation)
- F&O: Business income at slab rate
- Gold/Real Estate: LTCG with indexation (simplified)

Transaction Taxes:
- STT: Varies by instrument and side
- GST: 18% on brokerage (not on gains)
- Stamp Duty: ~0.015% on buy side
"""

from typing import List
from tax_engine.core import AbstractTaxStrategy
from tax_engine.models import (
    TaxProfile, PortfolioTaxContext, TransactionDetail,
    TaxLayer, HoldingPeriod, AssetClass, AccountType, IncomeTier,
    RiskSignal, RiskSignalSeverity, TaxImpact
)


# ─────────────────────────────────────────────
# India Slab Rates (FY 2024-25, New Regime)
# ─────────────────────────────────────────────
INDIA_SLAB_RATES = {
    IncomeTier.LOW: 0.05,         # 5% (Up to ₹7L effective zero due to rebate, ~5% blended)
    IncomeTier.MEDIUM: 0.20,      # 20% bracket
    IncomeTier.HIGH: 0.30,        # 30% bracket
    IncomeTier.VERY_HIGH: 0.30,   # 30% + surcharge (simplified)
}

# ─────────────────────────────────────────────
# STT Rates
# ─────────────────────────────────────────────
STT_RATES = {
    AssetClass.EQUITY_DOMESTIC: {
        "delivery_buy": 0.001,     # 0.1% on buy
        "delivery_sell": 0.001,    # 0.1% on sell
        "intraday_sell": 0.00025,  # 0.025% on sell side
    },
    AssetClass.ETF: {
        "delivery_buy": 0.001,
        "delivery_sell": 0.001,
    },
    AssetClass.FUTURES: {
        "sell": 0.0001,            # 0.01% on sell side
    },
    AssetClass.OPTIONS: {
        "sell": 0.0005,            # 0.05% on sell side (on premium)
    },
}

STAMP_DUTY_RATE = 0.00015  # 0.015% on buy side (uniform)


class IndiaTaxStrategy(AbstractTaxStrategy):
    """India tax strategy: STT + Capital Gains + Slab rates."""

    JURISDICTION_CODE = "IN"
    JURISDICTION_NAME = "India"

    TAX_EXEMPT_ACCOUNTS = {AccountType.PPF}
    TAX_DEFERRED_ACCOUNTS = {AccountType.NPS}

    def calculate_transaction_taxes(self, txn: TransactionDetail, profile: TaxProfile) -> List[TaxLayer]:
        """
        India Transaction Taxes:
        - STT (Securities Transaction Tax) on both Buy and Sell (Equity/F&O)
        - Stamp Duty on Buy
        - GST on Brokerage (Not modeled yet as brokerage is variable, but good to note)
        """
        layers: List[TaxLayer] = []
        asset = txn.asset_class
        direction = txn.direction.lower()
        
        # 1. STT
        # STT applies on Buy (Equity Delivery) and Sell (Equity Delivery, Intraday, F&O)
        # Our helper _calc_stt handles direction logic
        stt_layer = self._calc_stt(asset, txn.transaction_value_usd, direction)
        if stt_layer:
            layers.append(stt_layer)

        # 2. Stamp Duty
        # Generally applies on Buy side (0.015% for delivery)
        if direction in {"buy", "increase", "add", "long"}:
            stamp = txn.transaction_value_usd * STAMP_DUTY_RATE
            if stamp > 0:
                layers.append(TaxLayer(
                    name="Stamp Duty",
                    rate=STAMP_DUTY_RATE * 100,
                    amount=round(stamp, 2),
                    description="Stamp duty on buy-side securities transaction",
                    applies_to="transaction_value",
                ))
        
        return layers

    def calculate_realization_taxes(self, txn: TransactionDetail, profile: TaxProfile, holding: HoldingPeriod, gain: float) -> List[TaxLayer]:
        """
        India Realization Taxes (Capital Gains):
        - STCG (15%) / LTCG (10% > 1L) for Equity
        - Slab Rate for Debt/Intraday
        - Business Income for F&O
        """
        layers: List[TaxLayer] = []
        asset = txn.asset_class
        
        # We rely on the gain passed in. If gain <= 0, no tax (usually).
        # Note: In India, STCG losses can be set off, but for this layer we just calculate liability on *this* transaction.
        if gain <= 0:
            return layers

        cg_layer = self._calc_capital_gains(asset, holding, gain, profile.income_tier)
        if cg_layer:
            layers.append(cg_layer)
            
        return layers

    def _calc_capital_gains(
        self,
        asset: AssetClass,
        holding: HoldingPeriod,
        gain: float,
        income_tier: IncomeTier,
    ) -> TaxLayer | None:
        if gain <= 0:
            return None

        # ── Equity (STT paid) ──
        if asset in (AssetClass.EQUITY_DOMESTIC, AssetClass.ETF):
            if holding == HoldingPeriod.LONG_TERM:
                # LTCG: 10% on gains above ₹1 lakh (~$1,200 approx)
                exemption = 1200.0  # ₹1L ≈ $1,200
                taxable = max(0, gain - exemption)
                rate = 0.10
                return TaxLayer(
                    name="Equity LTCG",
                    rate=rate * 100,
                    amount=round(taxable * rate, 2),
                    description=f"10% on gains above ₹1L exemption (taxable: ${taxable:,.0f})",
                    applies_to="realized_gain",
                )
            else:
                # STCG: 15%
                rate = 0.15
                return TaxLayer(
                    name="Equity STCG",
                    rate=rate * 100,
                    amount=round(gain * rate, 2),
                    description="15% short-term capital gains (equity, STT paid)",
                    applies_to="realized_gain",
                )

        # ── Debt Funds (post-2023) ──
        elif asset in (AssetClass.DEBT_FUND, AssetClass.BOND):
            slab_rate = INDIA_SLAB_RATES.get(income_tier, 0.30)
            return TaxLayer(
                name="Debt Fund Tax (Slab)",
                rate=slab_rate * 100,
                amount=round(gain * slab_rate, 2),
                description=f"Debt fund gains taxed at slab rate ({slab_rate*100:.0f}%), no indexation (post-2023)",
                applies_to="realized_gain",
            )

        # ── F&O (Business Income) ──
        elif asset in (AssetClass.FUTURES, AssetClass.OPTIONS):
            slab_rate = INDIA_SLAB_RATES.get(income_tier, 0.30)
            return TaxLayer(
                name="F&O Business Income",
                rate=slab_rate * 100,
                amount=round(gain * slab_rate, 2),
                description=f"F&O treated as business income, taxed at slab rate ({slab_rate*100:.0f}%)",
                applies_to="realized_gain",
            )

        # ── Crypto ──
        elif asset == AssetClass.CRYPTO:
            rate = 0.30
            return TaxLayer(
                name="Crypto Tax",
                rate=rate * 100,
                amount=round(gain * rate, 2),
                description="Flat 30% on crypto gains (Section 115BBH), no loss set-off",
                applies_to="realized_gain",
            )

        # ── Gold ──
        elif asset == AssetClass.GOLD:
            if holding == HoldingPeriod.LONG_TERM:
                rate = 0.20  # With indexation (simplified)
                return TaxLayer(
                    name="Gold LTCG",
                    rate=rate * 100,
                    amount=round(gain * rate, 2),
                    description="20% LTCG with indexation on gold (>3 years)",
                    applies_to="realized_gain",
                )
            else:
                slab_rate = INDIA_SLAB_RATES.get(income_tier, 0.30)
                return TaxLayer(
                    name="Gold STCG (Slab)",
                    rate=slab_rate * 100,
                    amount=round(gain * slab_rate, 2),
                    description=f"Gold STCG taxed at slab rate ({slab_rate*100:.0f}%)",
                    applies_to="realized_gain",
                )

        # ── Default: slab rate ──
        else:
            slab_rate = INDIA_SLAB_RATES.get(income_tier, 0.30)
            return TaxLayer(
                name="Capital Gains (Slab)",
                rate=slab_rate * 100,
                amount=round(gain * slab_rate, 2),
                description=f"Gains taxed at income slab rate ({slab_rate*100:.0f}%)",
                applies_to="realized_gain",
            )

    def _calc_stt(self, asset: AssetClass, txn_value: float, direction: str) -> TaxLayer | None:
        """Calculate Securities Transaction Tax based on direction (buy/sell)."""
        rates = STT_RATES.get(asset)
        if not rates:
            return None

        # Normalize direction
        d = direction.lower()
        if d in {"buy", "increase", "add", "long"}:
            rate = rates.get("delivery_buy", 0)
        else:
            # Assume delivery sell for simplicity unless we know it's intraday
            # The context doesn't explicitly track intraday vs delivery yet, 
            # but we can default to delivery sell which covers most investor cases.
            rate = rates.get("delivery_sell", rates.get("sell", 0))

        if rate <= 0:
            return None

        amount = txn_value * rate
        return TaxLayer(
            name="STT",
            rate=rate * 100,
            amount=round(amount, 2),
            description=f"Securities Transaction Tax on {direction} ({rate*100:.3f}%)",
            applies_to="transaction_value",
        )

    def generate_signals(
        self,
        profile: TaxProfile,
        portfolio_ctx: PortfolioTaxContext,
        transactions: List[TransactionDetail],
        tax_impact: TaxImpact,
    ) -> List[RiskSignal]:
        signals: List[RiskSignal] = []
        if tax_impact.total_tax_liability <= 0 and not tax_impact.layers:
            return signals

        # 1. Short-Term Turnover Drag
        has_short_term = portfolio_ctx.holding_period == HoldingPeriod.SHORT_TERM
        gain = tax_impact.estimated_gain_usd
        if has_short_term and gain > 0:
            # 15% STCG vs 10% LTCG for equity
            spread = 0.05
            tail_delta = round(spread * 100 * 0.05, 2)
            expected_drag = round(tax_impact.effective_tax_rate, 2)
            
            signals.append(RiskSignal(
                title="Higher Short-Term Tax Rate",
                severity=RiskSignalSeverity.MEDIUM if expected_drag > 0.15 else RiskSignalSeverity.LOW,
                tail_loss_delta_pct=tail_delta,
                expected_return_drag_pct=-expected_drag,
                mechanism="Selling under 1 year triggers 15% tax instead of 10% Long-Term rate."
            ))

        # 2. Execution Friction Density
        stt_stamp_layers = [l for l in tax_impact.layers if l.category == "transaction"]
        if stt_stamp_layers:
            total_friction_rate = sum(l.rate for l in stt_stamp_layers) / 100.0
            if total_friction_rate > 0.001:  # > 0.1% friction
                signals.append(RiskSignal(
                    title="High Transaction Costs (STT)",
                    severity=RiskSignalSeverity.MEDIUM if total_friction_rate > 0.002 else RiskSignalSeverity.LOW,
                    volatility_impact_pct=round(total_friction_rate * 100 * 0.5, 2),  # heuristic Vol drag
                    mechanism="You are paying Securities Transaction Tax (STT) and Stamp Duty on this trade."
                ))

        # 3. LTCG Threshold Utilization
        # If long term equity, and gain is under 1L INR (~1200 USD)
        if not has_short_term and gain > 0:
            is_equity = any(t.asset_class in (AssetClass.EQUITY_DOMESTIC, AssetClass.ETF) for t in transactions)
            if is_equity:
                exemption_usd = 1200.0
                if gain < exemption_usd:
                    buffer_left = exemption_usd - gain
                    signals.append(RiskSignal(
                        title="Tax-Free Allowance Available",
                        severity=RiskSignalSeverity.LOW,
                        available_offset_usd=round(buffer_left, 2),
                        risk_dampening_potential_pct=10.0,
                        mechanism="You still have room in your ₹1 Lakh tax-free limit for this year."
                    ))

        # 4. Slab Exposure (Debt / F&O)
        has_slab_exposure = any(t.asset_class in (AssetClass.DEBT_FUND, AssetClass.BOND, AssetClass.FUTURES, AssetClass.OPTIONS) for t in transactions)
        if has_slab_exposure and gain > 0:
            slab_rate = INDIA_SLAB_RATES.get(profile.income_tier, 0.30)
            signals.append(RiskSignal(
                title="High Tax Slab Penalty",
                severity=RiskSignalSeverity.HIGH if slab_rate >= 0.30 else RiskSignalSeverity.MEDIUM,
                tail_loss_delta_pct=round(slab_rate * 100 * 0.1, 2),
                mechanism=f"These gains are taxed at your full income bracket rate ({slab_rate * 100:.0f}%) with no indexation benefits."
            ))

        return signals

