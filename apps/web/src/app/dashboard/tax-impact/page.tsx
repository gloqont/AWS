"use client";

import { useEffect, useMemo, useState } from "react";
import { apiFetch } from "@/lib/api";
import { useTutorial } from "@/components/tutorial/TutorialContext";
import { TAX_IMPACT_TUTORIAL } from "@/components/tutorial/tutorialContent";
import { useSearchParams } from "next/navigation";

type TaxCountry = "United States" | "India" | "United Kingdom" | "Europe (Generic)" | "Other";

const TAX_RULES: Record<
  string,
  {
    long_term_capital_gains: number;
    short_term_capital_gains: number;
    crypto: number;
    transaction_tax: number;
    fx_drag: number;
  }
> = {
  "United States": {
    long_term_capital_gains: 0.15,
    short_term_capital_gains: 0.3,
    crypto: 0.3,
    transaction_tax: 0.0,
    fx_drag: 0.005,
  },
  India: {
    long_term_capital_gains: 0.1,
    short_term_capital_gains: 0.15,
    crypto: 0.3,
    transaction_tax: 0.001,
    fx_drag: 0.01,
  },
  "United Kingdom": {
    long_term_capital_gains: 0.2,
    short_term_capital_gains: 0.2,
    crypto: 0.2,
    transaction_tax: 0.005,
    fx_drag: 0.008,
  },
  "Europe (Generic)": {
    long_term_capital_gains: 0.25,
    short_term_capital_gains: 0.25,
    crypto: 0.25,
    transaction_tax: 0.002,
    fx_drag: 0.01,
  },
};

const COUNTRIES: TaxCountry[] = ["United States", "India", "United Kingdom", "Europe (Generic)", "Other"];

type Portfolio = {
  id: string;
  name: string;
  risk_budget: "LOW" | "MEDIUM" | "HIGH";
  total_value: number;
  base_currency: string;
  positions: { ticker: string; weight: number }[];
  created_at: string;
};

type Decision = {
  id: string;
  decision_text: string;
  tax_country: string;
  portfolio_id: string;
  portfolio_value: number;
  expected_before_tax_pct: number;
  worst_case_pct: number;
  best_case_pct: number;
  confidence: string;
  notes: string[];
  created_at: string;
};

function fmtMoney(n: number) {
  try {
    return new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(n);
  } catch {
    return String(Math.round(n));
  }
}

export default function TaxImpactPage() {
  const searchParams = useSearchParams();
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [decision, setDecision] = useState<Decision | null>(null);

  const [country, setCountry] = useState<TaxCountry>("United States");

  const [loading, setLoading] = useState(true);
  const [countrySaving, setCountrySaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const { startTutorial, isTutorialActive } = useTutorial();

  // Start the tax impact tutorial when the page loads with tutorial param and no tutorial is active
  useEffect(() => {
    const tutorialParam = searchParams.get('tutorial');
    if (tutorialParam === 'tax-impact' && !isTutorialActive) {
      const timer = setTimeout(() => {
        startTutorial(TAX_IMPACT_TUTORIAL);
      }, 500); // Small delay to ensure DOM is ready

      return () => clearTimeout(timer);
    }
  }, [searchParams, startTutorial, isTutorialActive]);

  // Load portfolio + last decision from backend
  useEffect(() => {
    let mounted = true;
    (async () => {
      setErr(null);
      setLoading(true);
      try {
        const [p, d] = await Promise.all([
          apiFetch("/api/v1/portfolio/current", { method: "GET" }),
          apiFetch("/api/v1/decisions/last", { method: "GET" }),
        ]);
        if (!mounted) return;

        setPortfolio(p.portfolio ?? null);
        setDecision(d.decision ?? null);

        // Default country from last decision if it matches our list; otherwise keep US
        const lastCountry = (d.decision?.tax_country || "") as TaxCountry;
        if (COUNTRIES.includes(lastCountry)) setCountry(lastCountry);
      } catch (e: any) {
        if (!mounted) return;
        setErr(e.message || "Failed to load data for Tax Impact.");
      } finally {
        if (!mounted) return;
        setLoading(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  // When user changes country, re-run decisions/analyze with same decision_text so backend stores updated country
  async function applyCountryChange(next: TaxCountry) {
    setCountry(next);

    if (!decision) return; // nothing to persist yet

    setCountrySaving(true);
    setErr(null);
    try {
      const updated = await apiFetch("/api/v1/decisions/analyze", {
        method: "POST",
        body: JSON.stringify({
          decision_text: decision.decision_text,
          tax_country: next,
        }),
      });
      setDecision(updated as Decision);
    } catch (e: any) {
      setErr(e.message || "Failed to update tax country.");
    } finally {
      setCountrySaving(false);
    }
  }

  const computed = useMemo(() => {
    if (!portfolio || !decision) return null;

    const rules = TAX_RULES[country] ?? TAX_RULES["United States"];
    const portfolioValue = portfolio.total_value;

    const estimatedTax =
      portfolioValue *
      (rules.short_term_capital_gains * 0.4 +
        rules.long_term_capital_gains * 0.4 +
        rules.transaction_tax +
        rules.fx_drag);

    const effectiveRatePct = (estimatedTax / portfolioValue) * 100;

    const expectedBeforeTaxPct = decision.expected_before_tax_pct || 0;
    const afterTaxImpactPct = expectedBeforeTaxPct - effectiveRatePct / 10;
    const taxDragPct = Math.abs(afterTaxImpactPct - expectedBeforeTaxPct);

    return {
      rules,
      portfolioValue,
      estimatedTax,
      effectiveRatePct,
      afterTaxImpactPct,
      taxDragPct,
    };
  }, [portfolio, decision, country]);

  return (
    <div className="min-h-screen px-6 py-8">
      <div className="mx-auto max-w-6xl">
        <div className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur p-6">
          <div className="text-sm text-white/60">Advisor Dashboard</div>
          <h1 className="text-3xl font-semibold tracking-tight mt-1">Tax Impact</h1>
          <p className="text-sm text-white/60 mt-2">
            Post-decision tax drag estimate based on residency assumptions. Not tax advice.
          </p>
        </div>


        {loading ? (
          <div className="mt-6 rounded-2xl border border-white/10 bg-white/5 backdrop-blur p-6 text-sm text-white/70">
            Loading…
          </div>
        ) : !decision || !portfolio ? (
          <div className="mt-6 rounded-2xl border border-white/10 bg-white/5 backdrop-blur p-6">
            <div className="text-lg font-semibold">Missing data</div>
            {!portfolio ? (
              <p className="text-sm text-white/60 mt-2">
                No saved portfolio found. Go to <span className="text-white">Portfolio Optimizer</span> and click{" "}
                <span className="text-white">Save</span>.
              </p>
            ) : null}
            {!decision ? (
              <p className="text-sm text-white/60 mt-2">
                No decision found. Run a decision in <span className="text-white">Scenario Simulation</span> first,
                then come back here.
              </p>
            ) : null}
          </div>
        ) : (
          <>
            {/* Controls */}
            <div className="mt-6 grid grid-cols-1 lg:grid-cols-3 gap-4">
              <div id="tax-decision-info" className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur p-5">
                <div className="text-sm text-white/60">Decision</div>
                <div className="mt-2 text-sm text-white break-words">{decision.decision_text}</div>
                <div className="mt-3 text-xs text-white/50">
                  Saved: {new Date(decision.created_at).toLocaleString()}
                </div>
              </div>

              <div id="tax-residency-selector" className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur p-5">
                <div className="text-sm text-white/60">Tax Residency</div>
                <select
                  className="mt-2 w-full rounded-xl border border-white/10 bg-black/20 px-3 py-2 outline-none focus:border-white/25"
                  value={country}
                  onChange={(e) => applyCountryChange(e.target.value as TaxCountry)}
                  disabled={countrySaving}
                >
                  {COUNTRIES.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
                <div className="mt-2 text-xs text-white/50">
                  Used for estimate only. {countrySaving ? "Saving…" : " "}
                </div>
              </div>

              <div id="portfolio-value-display" className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur p-5">
                <div className="text-sm text-white/60">Portfolio Value</div>
                <div className="mt-2 text-3xl font-semibold tabular-nums">
                  ${fmtMoney(portfolio.total_value)}
                </div>
                <div className="mt-2 text-xs text-white/50">
                  Expected (before tax): {decision.expected_before_tax_pct ? decision.expected_before_tax_pct.toFixed(2) + '%' : 'N/A'}
                </div>
              </div>
            </div>

            {/* Metrics */}
            <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
              <div id="estimated-tax-payable" className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur p-5">
                <div className="text-sm text-white/60">Estimated Tax Payable</div>
                <div className="mt-2 text-3xl font-semibold tabular-nums">
                  ${fmtMoney(computed?.estimatedTax ?? 0)}
                </div>
              </div>

              <div id="effective-tax-rate" className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur p-5">
                <div className="text-sm text-white/60">Effective Tax Rate</div>
                <div className="mt-2 text-3xl font-semibold tabular-nums">
                  {(computed?.effectiveRatePct ?? 0).toFixed(1)}%
                </div>
              </div>

              <div id="after-tax-impact" className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur p-5">
                <div className="text-sm text-white/60">After-Tax Impact</div>
                <div className="mt-2 text-3xl font-semibold tabular-nums">
                  {(computed?.afterTaxImpactPct ?? 0).toFixed(2)}%
                </div>
                <div className="mt-2 text-xs text-white/50">
                  Tax drag: {(computed?.taxDragPct ?? 0).toFixed(2)}%
                </div>
              </div>
            </div>

            {/* Table */}
            <div className="mt-6 rounded-2xl border border-white/10 bg-white/5 backdrop-blur p-6">
              <div className="text-lg font-semibold">Where the Tax Comes From</div>
              <div className="mt-1 text-sm text-white/60">
                Blended assumption: 40% short-term, 40% long-term, plus transaction + FX drag.
              </div>

              <div className="mt-4 overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="text-white/60">
                    <tr className="border-b border-white/10">
                      <th className="text-left py-2">Source</th>
                      <th className="text-left py-2">Amount</th>
                      <th className="text-left py-2">Reason</th>
                    </tr>
                  </thead>
                  <tbody>
                    {computed ? (
                      <>
                        <tr className="border-b border-white/5">
                          <td className="py-2">Capital gains (Equity)</td>
                          <td className="py-2">
                            ${fmtMoney(computed.portfolioValue * computed.rules.short_term_capital_gains * 0.4)}
                          </td>
                          <td className="py-2 text-white/70">Long-term sale</td>
                        </tr>
                        <tr className="border-b border-white/5">
                          <td className="py-2">Short-term gains</td>
                          <td className="py-2">
                            ${fmtMoney(computed.portfolioValue * computed.rules.long_term_capital_gains * 0.4)}
                          </td>
                          <td className="py-2 text-white/70">Partial rebalance</td>
                        </tr>
                        <tr className="border-b border-white/5">
                          <td className="py-2">Transaction taxes</td>
                          <td className="py-2">${fmtMoney(computed.portfolioValue * computed.rules.transaction_tax)}</td>
                          <td className="py-2 text-white/70">Region-specific</td>
                        </tr>
                        <tr>
                          <td className="py-2">FX tax drag</td>
                          <td className="py-2">${fmtMoney(computed.portfolioValue * computed.rules.fx_drag)}</td>
                          <td className="py-2 text-white/70">Cross-border exposure</td>
                        </tr>
                      </>
                    ) : null}
                  </tbody>
                </table>
              </div>

              <div className="mt-5 rounded-xl border border-white/10 bg-black/20 p-4 text-xs text-white/60 leading-relaxed">
                <div className="font-medium text-white mb-1">Evidence & assumptions</div>
                • Residency-based estimates only<br />
                • No deductions/exemptions/harvesting modeled<br />
                • Not tax advice
              </div>
            </div>

            {/* Error */}
            {err && (
              <div className="mt-6 text-sm rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-red-200">
                {err}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
