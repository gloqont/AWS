"use client";

import { useEffect, useMemo, useState } from "react";
import { apiFetch } from "@/lib/api";
import { useTutorial } from "@/components/tutorial/TutorialContext";
import { TAX_ADVISOR_TUTORIAL } from "@/components/tutorial/tutorialContent";
import { useSearchParams } from "next/navigation";

type RiskSignal = {
  title: string;
  severity: "LOW" | "MEDIUM" | "HIGH";
  mechanism: string;
  expected_return_drag_pct?: number | null;
  tail_loss_delta_pct?: number | null;
  volatility_impact_pct?: number | null;
  available_offset_usd?: number | null;
  risk_dampening_potential_pct?: number | null;
};

type RiskResponse = {
  ok: boolean;
  portfolio_id: string;
  portfolio_value: number;
  base_currency: string;
  tax_country: string;
  state_province?: string | null;
  account_type?: string | null;
  income_bracket?: string | null;
  decision_id?: string | null;
  decision_text?: string | null;
  signals: RiskSignal[];
  moat_time_travel?: any;
  moat_tax_harvest?: any;
};

type PortfolioCurrent = {
  ok: boolean;
  portfolio: null | {
    id: string;
    name: string;
    risk_budget: string;
    total_value: number;
    base_currency: string;
  };
};

type DecisionLast = {
  ok: boolean;
  decision: null | {
    id: string;
    decision_text: string;
    tax_country: string;
    created_at: string;
  };
};

function fmtMoney(n: number) {
  return n.toLocaleString(undefined, { maximumFractionDigits: 0 });
}

function getCurrencySymbol(currency: string) {
  switch (currency?.toUpperCase()) {
    case "EUR": return "€";
    case "GBP": return "£";
    case "INR": return "₹";
    case "JPY": return "¥";
    case "CAD": return "C$";
    case "AUD": return "A$";
    case "USD":
    default: return "$";
  }
}

export default function TaxAdvisorPage() {
  const searchParams = useSearchParams();
  const [portfolio, setPortfolio] = useState<PortfolioCurrent["portfolio"]>(null);
  const [decision, setDecision] = useState<DecisionLast["decision"]>(null);

  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [advice, setAdvice] = useState<RiskResponse | null>(null);

  const { startTutorial, isTutorialActive } = useTutorial();

  // Start the tax advisor tutorial when the page loads
  useEffect(() => {
    const tutorialParam = searchParams.get("tutorial");
    const hasShownTaxAdvisorTutorial = localStorage.getItem("has_shown_tax_advisor_tutorial");

    if (
      (tutorialParam === "tax-advisor" && !isTutorialActive) ||
      (!tutorialParam && !isTutorialActive && !hasShownTaxAdvisorTutorial)
    ) {
      const timer = setTimeout(() => {
        localStorage.setItem("has_shown_tax_advisor_tutorial", "true");
        startTutorial(TAX_ADVISOR_TUTORIAL);
      }, 500); // Small delay to ensure DOM is ready

      return () => clearTimeout(timer);
    }
  }, [searchParams, startTutorial, isTutorialActive]);

  useEffect(() => {
    (async () => {
      try {
        const p = (await apiFetch("/api/v1/portfolio/current")) as PortfolioCurrent;
        setPortfolio(p.portfolio);

        const d = (await apiFetch("/api/v1/decisions/last")) as DecisionLast;
        setDecision(d.decision);
      } catch (e: any) {
        setErr(e.message || "Failed to load portfolio/decision.");
      }
    })();
  }, []);

  async function runAdvisor() {
    setErr(null);
    setLoading(true);
    try {
      // Read the user's country from localStorage (set by questionnaire/tax wizard)
      let userCountry: string | null = null;
      try {
        const taxProfile = localStorage.getItem("gloqont_tax_profile");
        if (taxProfile) {
          const parsed = JSON.parse(taxProfile);
          userCountry = parsed.taxCountry || null;
        }
        if (!userCountry) {
          const userProfile = localStorage.getItem("gloqont_user_profile");
          if (userProfile) {
            const parsed = JSON.parse(userProfile);
            userCountry = parsed.country || null;
          }
        }
      } catch { /* ignore parse errors */ }

      const res = (await apiFetch("/api/v1/tax/advice", {
        method: "POST",
        body: JSON.stringify({ tax_country: userCountry }),
      })) as RiskResponse;
      setAdvice(res);
    } catch (e: any) {
      setErr(e.message || "Tax advisor failed.");
      setAdvice(null);
    } finally {
      setLoading(false);
    }
  }

  const severityStyle = useMemo(() => {
    return (sev: RiskSignal["severity"]) => {
      if (sev === "HIGH") return "border-red-500/30 bg-red-500/10 text-red-200";
      if (sev === "MEDIUM") return "border-amber-500/30 bg-amber-500/10 text-amber-200";
      return "border-white/10 bg-white/5 text-white/80";
    };
  }, []);

  return (
    <div className="min-h-screen px-6 py-8">
      <div className="mx-auto max-w-6xl">
        <div className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur p-6">
          <div className="text-sm text-white/60">GLOQONT</div>
          <h1 className="text-3xl font-semibold tracking-tight mt-1">After-Tax Risk Signals</h1>
          <p className="text-sm text-white/60 mt-2">
            Mathematical risk transformation based on jurisdictional tax drag applied to your portfolio.
          </p>
        </div>


        {/* Context */}
        <div className="mt-6 grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur p-5">
            <div className="text-sm text-white/60">Portfolio Context</div>
            {!portfolio ? (
              <div className="mt-2 text-sm text-white/60">No portfolio saved yet.</div>
            ) : (
              <>
                <div className="mt-2 text-sm text-white">{portfolio.name}</div>
                <div className="mt-1 text-xs text-white/50">
                  Value: {getCurrencySymbol(portfolio.base_currency)}{fmtMoney(portfolio.total_value)}
                </div>
                <div className="mt-1 text-xs text-white/50">Risk budget: {portfolio.risk_budget}</div>
              </>
            )}
          </div>

          <div className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur p-5">
            <div className="text-sm text-white/60">Execution Context</div>
            {!decision ? (
              <div className="mt-2 text-sm text-white/60">
                Generic portfolio-level liquidation scenario assumed.
              </div>
            ) : (
              <>
                <div className="mt-2 text-sm text-white break-words">{decision.decision_text}</div>
                <div className="mt-2 text-xs text-white/50">Saved: {new Date(decision.created_at).toLocaleString()}</div>
              </>
            )}
          </div>

          <div id="tax-country-selector" className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur p-5 flex flex-col justify-between">
            <div>
              <div className="text-sm text-white/60">Jurisdiction & Tier</div>
              <div className="mt-2 text-sm text-white">
                {advice ? `${advice.tax_country} ${advice.state_province ? `(${advice.state_province})` : ""}` : "Fetches from profile..."}
              </div>
              {advice && (
                <div className="mt-1 text-xs text-white/50">
                  Acct: {advice.account_type || "Taxable"} • Tier: {advice.income_bracket || "High"}
                </div>
              )}
            </div>

            <button
              id="generate-advice-button"
              onClick={runAdvisor}
              disabled={loading}
              className="mt-3 w-full rounded-xl bg-white text-black font-medium py-2.5 hover:opacity-90 disabled:opacity-60"
            >
              {loading ? "Running..." : "Generate Risk Signals"}
            </button>
          </div>
        </div>

        {err && (
          <div className="mt-6 text-sm rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-red-200">
            {err}
          </div>
        )}

        {/* Advice / Signals */}
        <div className="mt-6">
          {!advice ? (
            <div id="recommendations-section" className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur p-6 text-sm text-white/60">
              Click <span className="text-white">Generate Risk Signals</span> to calculate after-tax transformations.
            </div>
          ) : (
            <>
              <div id="recommendations-section" className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur p-6">
                <div className="text-lg font-semibold">After-Tax Adjustments</div>
                <div className="text-sm text-white/60 mt-1">
                  Baseline shifts isolated to current jurisdiction regime
                </div>
              </div>

              {advice.signals.length === 0 ? (
                <div className="mt-4 rounded-2xl border border-white/10 bg-white/5 p-5 text-sm text-white/50">
                  No significant tax risk signals generated for this scenario.
                </div>
              ) : (
                <div className="mt-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {advice.signals.map((it, idx) => (
                    <div
                      key={idx}
                      className={[
                        "rounded-2xl border backdrop-blur p-5 flex flex-col",
                        severityStyle(it.severity),
                      ].join(" ")}
                    >
                      <div className="flex items-center justify-between gap-3 mb-3">
                        <div className="text-sm font-semibold text-white">{it.title}</div>
                        <div className="text-[10px] uppercase font-bold px-2 py-0.5 rounded-full border border-white/10 bg-black/20 text-white/80">
                          {it.severity}
                        </div>
                      </div>

                      <div className="text-xs text-white/60 mb-4">{it.mechanism}</div>

                      <div className="grid grid-cols-2 gap-2 mt-auto">
                        {it.expected_return_drag_pct !== undefined && it.expected_return_drag_pct !== null && (
                          <div className="rounded bg-black/20 p-2">
                            <div className="text-[10px] text-white/50 uppercase">ER Drag</div>
                            <div className="text-sm font-mono text-white mt-0.5">{it.expected_return_drag_pct > 0 ? "+" : ""}{it.expected_return_drag_pct}%</div>
                          </div>
                        )}
                        {it.tail_loss_delta_pct !== undefined && it.tail_loss_delta_pct !== null && (
                          <div className="rounded bg-black/20 p-2">
                            <div className="text-[10px] text-white/50 uppercase">Tail Loss Δ</div>
                            <div className="text-sm font-mono text-white mt-0.5">{it.tail_loss_delta_pct > 0 ? "+" : ""}{it.tail_loss_delta_pct}%</div>
                          </div>
                        )}
                        {it.volatility_impact_pct !== undefined && it.volatility_impact_pct !== null && (
                          <div className="rounded bg-black/20 p-2">
                            <div className="text-[10px] text-white/50 uppercase">Vol Δ</div>
                            <div className="text-sm font-mono text-white mt-0.5">{it.volatility_impact_pct > 0 ? "+" : ""}{it.volatility_impact_pct}%</div>
                          </div>
                        )}
                        {it.available_offset_usd !== undefined && it.available_offset_usd !== null && (
                          <div className="rounded bg-black/20 p-2">
                            <div className="text-[10px] text-white/50 uppercase">Buffer USD</div>
                            <div className="text-sm font-mono text-white mt-0.5">${fmtMoney(it.available_offset_usd)}</div>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* ── MOAT: Time-Travel Trade Optimizer ── */}
              {advice.moat_time_travel?.applicable && (() => {
                const tt = advice.moat_time_travel;
                return (
                  <div className="mt-6">
                    <div className="text-lg font-semibold mb-4 text-[#D4A853]">Future Taxes Optimizer</div>
                    <div className="bg-gradient-to-r from-blue-500/10 to-cyan-500/10 border border-cyan-500/20 rounded-xl p-5">
                      <div className="text-sm text-cyan-300 font-medium mb-4">{tt.message}</div>
                      <div className="grid grid-cols-3 gap-4">
                        <div className="text-center">
                          <div className="text-xs text-white/40 uppercase tracking-wider mb-1">Today ({tt.current_rate_label})</div>
                          <div className="text-xl font-mono text-red-400 font-bold">{getCurrencySymbol(advice.base_currency)}{fmtMoney(tt.current_tax)}</div>
                        </div>
                        <div className="text-center flex flex-col items-center justify-center">
                          <div className="text-xs text-white/40 uppercase tracking-wider mb-1">Wait</div>
                          <div className="text-xl font-mono text-cyan-400 font-bold">{tt.wait_days} days</div>
                          <div className="text-[10px] text-white/30 mt-1">→ {tt.optimized_rate_label}</div>
                        </div>
                        <div className="text-center">
                          <div className="text-xs text-white/40 uppercase tracking-wider mb-1">Optimized Tax</div>
                          <div className="text-xl font-mono text-emerald-400 font-bold">{getCurrencySymbol(advice.base_currency)}{fmtMoney(tt.optimized_tax)}</div>
                        </div>
                      </div>
                      <div className="mt-4 text-center bg-emerald-500/10 border border-emerald-500/20 rounded-lg py-2.5 px-4">
                        <span className="text-xs text-white/50 uppercase tracking-wider mr-2">You Save</span>
                        <span className="text-lg font-mono font-bold text-emerald-400">{getCurrencySymbol(advice.base_currency)}{fmtMoney(tt.savings)}</span>
                      </div>
                    </div>
                  </div>
                );
              })()}

              {/* ── MOAT: Tax-Loss Harvest Offset ── */}
              {advice.moat_tax_harvest?.applicable && (() => {
                const th = advice.moat_tax_harvest;
                return (
                  <div className="mt-6">
                    <div className="text-lg font-semibold mb-4 text-[#D4A853]">Tax-Loss Harvest Offset</div>
                    <div className="bg-gradient-to-r from-amber-500/10 to-orange-500/10 border border-amber-500/20 rounded-xl p-5">
                      <div className="text-sm text-amber-300 font-medium mb-4">{th.message}</div>
                      <div className="grid grid-cols-2 gap-4 mb-4">
                        <div>
                          <div className="text-xs text-white/40 uppercase tracking-wider mb-1">Capital Gain</div>
                          <div className="text-xl font-mono text-red-400 font-bold">{getCurrencySymbol(advice.base_currency)}{fmtMoney(th.trade_gain)}</div>
                        </div>
                        <div>
                          <div className="text-xs text-white/40 uppercase tracking-wider mb-1">Available Offset</div>
                          <div className="text-xl font-mono text-emerald-400 font-bold">-{getCurrencySymbol(advice.base_currency)}{fmtMoney(th.total_offset)}</div>
                        </div>
                      </div>
                      <div className="bg-black/30 rounded-lg overflow-hidden border border-white/5">
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="text-white/40 uppercase tracking-wider text-[10px] border-b border-white/5">
                              <th className="px-3 py-2 text-left">Asset</th>
                              <th className="px-3 py-2 text-right">Return</th>
                              <th className="px-3 py-2 text-right">Est. Loss</th>
                              <th className="px-3 py-2 text-right">Offset</th>
                            </tr>
                          </thead>
                          <tbody>
                            {th.offset_candidates.map((c: any, i: number) => (
                              <tr key={i} className="border-b border-white/5">
                                <td className="px-3 py-2 text-white font-mono font-bold">{c.symbol}</td>
                                <td className="px-3 py-2 text-right text-red-400 font-mono">{c.return_pct.toFixed(1)}%</td>
                                <td className="px-3 py-2 text-right text-white/70 font-mono">{getCurrencySymbol(advice.base_currency)}{fmtMoney(c.estimated_loss)}</td>
                                <td className="px-3 py-2 text-right text-emerald-400 font-mono">{getCurrencySymbol(advice.base_currency)}{fmtMoney(c.offset_amount)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                      <div className="mt-4 flex justify-between items-center bg-emerald-500/10 border border-emerald-500/20 rounded-lg py-2.5 px-4">
                        <span className="text-xs text-white/50 uppercase tracking-wider">Tax Savings</span>
                        <span className="text-lg font-mono font-bold text-emerald-400">{getCurrencySymbol(advice.base_currency)}{fmtMoney(th.savings)}</span>
                      </div>
                    </div>
                  </div>
                );
              })()}

            </>
          )}
        </div>

        <div className="mt-6 text-xs text-white/30">
          * Mathematically generated signals based strictly on transaction properties.
        </div>
      </div>
    </div>
  );
}
