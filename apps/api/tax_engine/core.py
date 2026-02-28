"""
GLOQONT Tax Engine — Core Dispatcher

TaxEngine is the single entry point. It:
1. Receives TaxProfile + PortfolioTaxContext + list of TransactionDetails
2. Routes to the correct jurisdiction strategy
3. Aggregates per-transaction TaxImpact into a combined result
"""

from typing import List, Dict, Optional, Any
from abc import ABC, abstractmethod

from tax_engine.models import (
    TaxProfile,
    PortfolioTaxContext,
    TransactionDetail,
    TaxImpact,
    TaxLayer,
    AccountType,
    HoldingPeriod,
    AssetClass,
    SUPPORTED_JURISDICTIONS,
    RiskSignal,
    RiskSignalSeverity,
)


# ─────────────────────────────────────────────
# Abstract Strategy
# ─────────────────────────────────────────────

class AbstractTaxStrategy(ABC):
    """Base class for jurisdiction-specific tax logic."""

    JURISDICTION_CODE: str = ""
    JURISDICTION_NAME: str = ""

    # Tax-exempt account types for this jurisdiction
    TAX_EXEMPT_ACCOUNTS: set = set()
    TAX_DEFERRED_ACCOUNTS: set = set()

    @abstractmethod
    def calculate_transaction_taxes(self, txn: TransactionDetail, profile: TaxProfile) -> List[TaxLayer]:
        """
        Calculate taxes that apply immediately upon execution (Buy OR Sell).
        Examples: STT, Stamp Duty, Brokerage, GST, Exchange Fees.
        These are "sunk costs" and apply regardless of profit/loss.
        """
        pass

    @abstractmethod
    def calculate_realization_taxes(self, txn: TransactionDetail, profile: TaxProfile, holding_period: HoldingPeriod, gain: float) -> List[TaxLayer]:
        """
        Calculate taxes that apply ONLY on realization of profit (Sell).
        Examples: Capital Gains Tax (STCG, LTCG), Withholding Tax.
        These depend on the gain/loss amount and holding period.
        """
        pass

    def generate_signals(
        self,
        profile: TaxProfile,
        portfolio_ctx: PortfolioTaxContext,
        transactions: List[TransactionDetail],
        tax_impact: TaxImpact,
    ) -> List[RiskSignal]:
        """
        Generate quantified risk signals (expected return drag, tail loss delta, etc.)
        based on the transaction context and calculated tax impact.
        Override in jurisdiction strategies.
        """
        signals: List[RiskSignal] = []
        eff_rate = tax_impact.effective_tax_rate / 100.0
        
        # Generic fallback signal (if no jurisdiction-specific logic catches it)
        if eff_rate > 0:
            signals.append(RiskSignal(
                title=f"{self.JURISDICTION_NAME} Tax Drag",
                severity="MEDIUM" if eff_rate > 0.05 else "LOW",
                expected_return_drag_pct=round(-eff_rate * 100, 2),
                mechanism=f"Blended Tax Rate ({self.JURISDICTION_NAME})"
            ))
            
        return signals

    def calculate(
        self,
        profile: TaxProfile,
        portfolio_ctx: PortfolioTaxContext,
        transactions: List[TransactionDetail],
    ) -> TaxImpact:
        """
        Calculate total tax impact across all transactions.
        Handles account-type short-circuits before delegating to per-txn logic.

        CRITICAL RULE:
        - BUY events → transaction taxes ONLY (STT, Stamp Duty, SDRT, etc.)
        - SELL events → transaction taxes + realization taxes (CGT)
        - Capital gains tax is NEVER applied on a buy event.
        """
        # ── Account-type short circuit ──
        if portfolio_ctx.account_type in self.TAX_EXEMPT_ACCOUNTS:
            return self._build_exempt_result(
                profile, portfolio_ctx, transactions, deferred=False
            )
        if portfolio_ctx.account_type in self.TAX_DEFERRED_ACCOUNTS:
            return self._build_exempt_result(
                profile, portfolio_ctx, transactions, deferred=True
            )

        all_layers: List[TaxLayer] = []
        total_txn_value = 0.0
        total_estimated_gain = 0.0
        
        # Track event types
        has_sells = any(
            t.direction.lower() in {"sell", "reduce", "liquidate", "short", "cover"}
            for t in transactions
        )
        is_buy_only = not has_sells

        for txn in transactions:
            total_txn_value += txn.transaction_value_usd
            
            # 1. TRANSACTION TAXES (Immediate Friction — applies to BUY and SELL)
            txn_layers = self.calculate_transaction_taxes(txn, profile)
            for l in txn_layers:
                l.category = "transaction"
            all_layers.extend(txn_layers)

            # 2. REALIZATION TAXES (ONLY on sell/liquidation events)
            direction = txn.direction.lower()
            
            if direction in {"sell", "reduce", "liquidate", "short", "cover"}:
                # ── Realized Event — CGT applies ──
                holding = txn.holding_period or portfolio_ctx.holding_period
                gain = txn.estimated_gain_usd
                if gain is None:
                    gain = txn.transaction_value_usd * (portfolio_ctx.estimated_gain_percent / 100.0)
                
                total_estimated_gain += gain
                
                real_layers = self.calculate_realization_taxes(txn, profile, holding, gain)
                for l in real_layers:
                    l.category = "realization"
                all_layers.extend(real_layers)

            else:
                # BUY events: Calculate PROJECTED realization tax if estimated gain is provided.
                # This shows what the user would owe if they exit within the scenario horizon.
                gain = txn.estimated_gain_usd
                if gain is not None and gain > 0:
                    holding = txn.holding_period or portfolio_ctx.holding_period
                    total_estimated_gain += gain
                    real_layers = self.calculate_realization_taxes(txn, profile, holding, gain)
                    for l in real_layers:
                        l.category = "realization"
                    all_layers.extend(real_layers)

        # ── Aggregate ──
        total_tax = sum(l.amount for l in all_layers)
        
        # Effective rates
        eff_rate = (total_tax / total_txn_value * 100) if total_txn_value > 0 else 0.0
        
        # Consolidate layers with same name
        consolidated = self._consolidate_layers(all_layers)

        # Determine tax regime label
        holding = portfolio_ctx.holding_period
        if self.JURISDICTION_CODE == "NL":
            regime_label = "Wealth Tax (Box 3 Deemed Return)"
        elif holding == HoldingPeriod.SHORT_TERM:
            regime_label = "Short-Term Capital Gains"
        else:
            regime_label = "Long-Term Capital Gains"

        return TaxImpact(
            total_tax_liability=round(total_tax, 2),
            effective_tax_rate=round(eff_rate, 2),
            effective_gain_tax_rate=0.0,
            layers=consolidated,
            transaction_value_usd=round(total_txn_value, 2),
            estimated_gain_usd=round(total_estimated_gain, 2),
            net_proceeds_after_tax=round(total_txn_value - total_tax, 2),
            tax_drag_on_return_pct=round(eff_rate, 2),
            jurisdiction=self.JURISDICTION_CODE,
            jurisdiction_name=self.JURISDICTION_NAME,
            account_type=portfolio_ctx.account_type.value,
            holding_period=portfolio_ctx.holding_period.value,
            asset_class=transactions[0].asset_class.value if transactions else "unknown",
            is_buy_only=is_buy_only,
            tax_regime_applied=regime_label,
            summary=self._generate_summary(
                total_tax, total_txn_value, total_estimated_gain, consolidated,
                is_projected=False,
            ),
        )

    # ── Helpers ──

    def _build_exempt_result(
        self,
        profile: TaxProfile,
        ctx: PortfolioTaxContext,
        transactions: List[TransactionDetail],
        deferred: bool,
    ) -> TaxImpact:
        total_val = sum(t.transaction_value_usd for t in transactions)
        label = "tax-deferred" if deferred else "tax-exempt"
        return TaxImpact(
            total_tax_liability=0.0,
            effective_tax_rate=0.0,
            effective_gain_tax_rate=0.0,
            transaction_value_usd=round(total_val, 2),
            net_proceeds_after_tax=round(total_val, 2),
            jurisdiction=self.JURISDICTION_CODE,
            jurisdiction_name=self.JURISDICTION_NAME,
            account_type=ctx.account_type.value,
            holding_period=ctx.holding_period.value,
            is_tax_exempt=not deferred,
            is_tax_deferred=deferred,
            summary=f"Account type '{ctx.account_type.value}' is {label}. No immediate tax liability.",
        )

    def _consolidate_layers(self, layers: List[TaxLayer]) -> List[TaxLayer]:
        """Merge layers with the same name."""
        merged: Dict[str, TaxLayer] = {}
        for layer in layers:
            if layer.name in merged:
                merged[layer.name].amount = round(merged[layer.name].amount + layer.amount, 2)
            else:
                merged[layer.name] = layer.model_copy()
        return list(merged.values())

    def _generate_summary(
        self, total_tax: float, total_val: float, total_gain: float,
        layers: List[TaxLayer], is_projected: bool = False,
    ) -> str:
        prefix = "[Projected] " if is_projected else ""
        parts = [f"{prefix}Estimated tax liability: ${total_tax:,.2f}"]
        if total_val > 0:
            parts.append(f"on ${total_val:,.2f} transaction value")
        if total_gain > 0:
            parts.append(f"(est. gain: ${total_gain:,.2f})")
        parts.append("— Breakdown:")
        for l in layers:
            parts.append(f"  {l.name}: ${l.amount:,.2f} ({l.rate:.1f}%)")
        if is_projected:
            parts.append("| This is the projected tax when you eventually sell these holdings.")
        return " ".join(parts)


# ─────────────────────────────────────────────
# Engine (Factory / Dispatcher)
# ─────────────────────────────────────────────

class TaxEngine:
    """
    Main entry point for tax calculations.
    Routes to jurisdiction-specific strategies.
    """

    _strategies: Dict[str, AbstractTaxStrategy] = {}

    def __init__(self):
        # Lazy-import strategies to avoid circular imports
        from tax_engine.strategies.usa import USATaxStrategy
        from tax_engine.strategies.india import IndiaTaxStrategy
        from tax_engine.strategies.canada import CanadaTaxStrategy
        from tax_engine.strategies.europe import (
            GermanyTaxStrategy,
            FranceTaxStrategy,
            UKTaxStrategy,
            NetherlandsTaxStrategy,
        )

        self._strategies = {
            "US": USATaxStrategy(),
            "IN": IndiaTaxStrategy(),
            "CA": CanadaTaxStrategy(),
            "DE": GermanyTaxStrategy(),
            "FR": FranceTaxStrategy(),
            "GB": UKTaxStrategy(),
            "NL": NetherlandsTaxStrategy(),
        }

    def calculate(
        self,
        profile: TaxProfile,
        portfolio_ctx: PortfolioTaxContext,
        transactions: List[TransactionDetail],
    ) -> TaxImpact:
        """Calculate tax impact using the appropriate jurisdiction strategy."""
        strategy = self._strategies.get(profile.jurisdiction)
        if not strategy:
            return TaxImpact(
                jurisdiction=profile.jurisdiction,
                summary=f"Unsupported jurisdiction: {profile.jurisdiction}. Supported: {list(self._strategies.keys())}",
                warnings=[f"No tax strategy for '{profile.jurisdiction}'."],
            )
        return strategy.calculate(profile, portfolio_ctx, transactions)

    def get_supported_jurisdictions(self) -> Dict[str, Any]:
        """Return supported jurisdictions and their sub-jurisdictions."""
        return SUPPORTED_JURISDICTIONS

    def classify_asset(self, symbol: str, portfolio: Optional[Dict] = None) -> AssetClass:
        """
        Heuristic asset classification from symbol.
        In production this would use a security master database.
        """
        s = symbol.upper()

        # Crypto
        if any(c in s for c in ["BTC", "ETH", "SOL", "DOGE", "ADA", "-USD"]):
            return AssetClass.CRYPTO

        # Indian market suffixes
        if s.endswith(".NS") or s.endswith(".BO"):
            return AssetClass.EQUITY_DOMESTIC  # From India perspective

        # ETFs
        ETF_TICKERS = {"SPY", "QQQ", "IWM", "VOO", "VTI", "AGG", "TLT", "GLD", "EEM", "VWO"}
        if s in ETF_TICKERS:
            return AssetClass.ETF

        # Bonds / Fixed income ETFs
        BOND_TICKERS = {"AGG", "BND", "TLT", "IEF", "LQD", "HYG", "TIP"}
        if s in BOND_TICKERS:
            return AssetClass.BOND

        # REITs
        REIT_TICKERS = {"VNQ", "O", "AMT", "PLD", "SPG", "WELL", "DLR"}
        if s in REIT_TICKERS:
            return AssetClass.REIT

        # Gold
        if s in {"GLD", "IAU", "GOLD", "XAUUSD"}:
            return AssetClass.GOLD

        # Default: domestic equity
        return AssetClass.EQUITY_DOMESTIC
