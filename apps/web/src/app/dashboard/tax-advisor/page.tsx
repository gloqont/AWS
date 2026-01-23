"use client";

import { useEffect, useMemo, useState } from "react";
import { apiFetch } from "@/lib/api";
import { useTutorial } from "@/components/tutorial/TutorialContext";
import { TAX_ADVISOR_TUTORIAL } from "@/components/tutorial/tutorialContent";
import { useSearchParams } from "next/navigation";

type AdviceItem = {
  title: string;
  severity: "LOW" | "MEDIUM" | "HIGH";
  why: string;
  est_savings_usd: number;
  next_step: string;
};

type AdviceResponse = {
  ok: boolean;
  portfolio_id: string;
  portfolio_value: number;
  base_currency: string;
  tax_country: string;
  decision_id?: string | null;
  decision_text?: string | null;
  items: AdviceItem[];
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

export default function TaxAdvisorPage() {
  const searchParams = useSearchParams();
  const [country, setCountry] = useState("United States");
  const [portfolio, setPortfolio] = useState<PortfolioCurrent["portfolio"]>(null);
  const [decision, setDecision] = useState<DecisionLast["decision"]>(null);

  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [advice, setAdvice] = useState<AdviceResponse | null>(null);

  const { startTutorial, isTutorialActive } = useTutorial();

  // Start the tax advisor tutorial when the page loads with tutorial param and no tutorial is active
  useEffect(() => {
    const tutorialParam = searchParams.get('tutorial');
    if (tutorialParam === 'tax-advisor' && !isTutorialActive) {
      const timer = setTimeout(() => {
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
        if (d.decision?.tax_country) setCountry(d.decision.tax_country);
      } catch (e: any) {
        setErr(e.message || "Failed to load portfolio/decision.");
      }
    })();
  }, []);

  async function runAdvisor() {
    setErr(null);
    setLoading(true);
    try {
      const res = (await apiFetch("/api/v1/tax/advice", {
        method: "POST",
        body: JSON.stringify({ tax_country: country }),
      })) as AdviceResponse;
      setAdvice(res);
    } catch (e: any) {
      setErr(e.message || "Tax advisor failed.");
      setAdvice(null);
    } finally {
      setLoading(false);
    }
  }

  const severityStyle = useMemo(() => {
    return (sev: AdviceItem["severity"]) => {
      if (sev === "HIGH") return "border-red-500/30 bg-red-500/10 text-red-200";
      if (sev === "MEDIUM") return "border-amber-500/30 bg-amber-500/10 text-amber-200";
      return "border-white/10 bg-white/5 text-white/80";
    };
  }, []);

  return (
    <div className="min-h-screen px-6 py-8">
      <div className="mx-auto max-w-6xl">
        <div className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur p-6">
          <div className="text-sm text-white/60">Advisor Dashboard</div>
          <h1 className="text-3xl font-semibold tracking-tight mt-1">Tax Advisor</h1>
          <p className="text-sm text-white/60 mt-2">
            Action-focused suggestions based on your latest saved portfolio + last scenario decision.
          </p>
        </div>


        {/* Context */}
        <div className="mt-6 grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur p-5">
            <div className="text-sm text-white/60">Portfolio</div>
            {!portfolio ? (
              <div className="mt-2 text-sm text-white/60">No portfolio saved yet.</div>
            ) : (
              <>
                <div className="mt-2 text-sm text-white">{portfolio.name}</div>
                <div className="mt-1 text-xs text-white/50">
                  Value: ${fmtMoney(portfolio.total_value)} {portfolio.base_currency}
                </div>
                <div className="mt-1 text-xs text-white/50">Risk budget: {portfolio.risk_budget}</div>
              </>
            )}
          </div>

          <div className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur p-5">
            <div className="text-sm text-white/60">Last Decision</div>
            {!decision ? (
              <div className="mt-2 text-sm text-white/60">
                None yet. Run Scenario Simulation first (optional, but helps).
              </div>
            ) : (
              <>
                <div className="mt-2 text-sm text-white break-words">{decision.decision_text}</div>
                <div className="mt-2 text-xs text-white/50">Saved: {new Date(decision.created_at).toLocaleString()}</div>
              </>
            )}
          </div>

          <div id="tax-country-selector" className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur p-5">
            <div className="text-sm text-white/60">Tax Residency</div>
            <select
              className="mt-2 w-full rounded-xl border border-white/10 bg-black/20 px-3 py-2 outline-none focus:border-white/25"
              value={country}
              onChange={(e) => setCountry(e.target.value)}
            >
              <option>United States</option>
              <option>India</option>
              <option>United Kingdom</option>
              <option>Europe (Generic)</option>
              <option>Other</option>
            </select>

            <button
              id="generate-advice-button"
              onClick={runAdvisor}
              disabled={loading}
              className="mt-3 w-full rounded-xl bg-white text-black font-medium py-2.5 hover:opacity-90 disabled:opacity-60"
            >
              {loading ? "Running..." : "Generate Advice"}
            </button>

            <div className="mt-2 text-xs text-white/50">
              Tip: Save a portfolio and run Scenario Simulation for more relevant advice.
            </div>
          </div>
        </div>

        {err && (
          <div className="mt-6 text-sm rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-red-200">
            {err}
          </div>
        )}

        {/* Advice */}
        <div className="mt-6">
          {!advice ? (
            <div id="recommendations-section" className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur p-6 text-sm text-white/60">
              Click <span className="text-white">Generate Advice</span> to see recommendations.
            </div>
          ) : (
            <>
              <div id="recommendations-section" className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur p-6">
                <div className="text-lg font-semibold">Recommendations</div>
                <div className="text-sm text-white/60 mt-1">
                  Portfolio: ${fmtMoney(advice.portfolio_value)} {advice.base_currency} • Country: {advice.tax_country}
                </div>
              </div>

              <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                {advice.items.map((it, idx) => (
                  <div
                    key={idx}
                    className={[
                      "rounded-2xl border backdrop-blur p-5",
                      severityStyle(it.severity),
                    ].join(" ")}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div className="text-sm font-semibold text-white">{it.title}</div>
                      <div className="text-[11px] px-2 py-1 rounded-full border border-white/10 bg-black/20">
                        {it.severity}
                      </div>
                    </div>

                    <div className="mt-2 text-sm text-white/80">{it.why}</div>

                    <div className="mt-3 text-xs text-white/60">
                      Est. savings:{" "}
                      <span className="text-white">
                        ${fmtMoney(Math.max(0, it.est_savings_usd || 0))}
                      </span>
                    </div>

                    <div className="mt-3 rounded-xl border border-white/10 bg-black/20 p-3 text-xs text-white/70">
                      <div className="text-white/80 font-medium mb-1">Next step</div>
                      {it.next_step}
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>

        <div className="mt-6 text-xs text-white/50">
          Not tax advice. This is a rules-based MVP advisor; next upgrade is adding cost basis + lot-level data to make
          harvesting and timing recommendations precise.
        </div>
      </div>
    </div>
  );
}
