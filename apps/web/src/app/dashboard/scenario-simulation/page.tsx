"use client";

import { useEffect, useMemo, useState } from "react";
import { apiFetch } from "@/lib/api";

import { useTutorial } from "@/components/tutorial/TutorialContext";
import { SCENARIO_SIMULATION_TUTORIAL } from "@/components/tutorial/tutorialContent";

import { useSearchParams } from "next/navigation";

import { JURISDICTIONS, INCOME_TIERS, COUNTRY_ACCOUNT_TYPES, DEFAULT_ACCOUNT_TYPES } from "@/components/TaxProfileWizard";
import { EmberCard } from "@/components/dashboard/ui/EmberCard";

// Map old ACCOUNT_TYPES if needed, or just use the imported one if compatible. 
// The TaxProfileWizard exports COUNTRY_ACCOUNT_TYPES, let's use that logic or keep the local mapping if it's cleaner for now, 
// BUT we MUST use the shared JURISDICTIONS to get the correct currency.

// ... existing code expects JURISDICTIONS to have currency ...
// TaxProfileWizard's JURISDICTIONS doesn't seem to have 'currency' field in the file I viewed earlier!
// Let's check `TaxProfileWizard.tsx` again.
// The viewer showed: "US": { label: "United States", code: "US", flag: "🇺🇸", states: ... },
// It MISSES 'currency'. 
// I need to ADD 'currency' to TaxProfileWizard.tsx FIRST.


// Horizon Categories for simulation
const HORIZON_CATEGORIES = {
  day_trade: {
    label: "Day Trade",
    description: "Intraday positions, 1-24 hours",
    min: 1,
    max: 24,
    default: 8,
    unit: "hours",
    unitLabel: "Hours"
  },
  swing_trade: {
    label: "Swing Trade",
    description: "Short-term, 2-7 days",
    min: 2,
    max: 7,
    default: 3,
    unit: "days",
    unitLabel: "Days"
  },
  position_trade: {
    label: "Position Trade",
    description: "Medium-term, 1-26 weeks",
    min: 1,
    max: 26,
    default: 4,
    unit: "weeks",
    unitLabel: "Weeks"
  },
  long_term: {
    label: "Long-Term Hold",
    description: "Investing, 6-60 months",
    min: 6,
    max: 60,
    default: 12,
    unit: "months",
    unitLabel: "Months"
  }
} as const;

type HorizonCategory = keyof typeof HORIZON_CATEGORIES;

type Portfolio = {
  id: string;
  name: string;
  risk_budget: "LOW" | "MEDIUM" | "HIGH";
  total_value: number;
  base_currency: string;
  positions: { ticker: string; weight: number }[]; // weights are decimals (0.5)
  created_at: string;
};

import { fmtMoney, APPROX_FX_RATES } from "@/lib/currencyUtils";

function fmtPct(n: number) {
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(2)}%`;
}

export default function ScenarioSimulationPage() {
  const searchParams = useSearchParams();
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [decisionText, setDecisionText] = useState("");
  const [taxCountry, setTaxCountry] = useState("US");
  const [taxSubJurisdiction, setTaxSubJurisdiction] = useState<string | null>(null);
  const [taxAccountType, setTaxAccountType] = useState("taxable");
  const [taxHoldingPeriod, setTaxHoldingPeriod] = useState("short_term");
  const [taxIncomeTier, setTaxIncomeTier] = useState("medium");
  const [taxFilingStatus, setTaxFilingStatus] = useState("single");

  const [marketContext, setMarketContext] = useState<any | null>(null);

  // Unified Result State (replaces legacy states)
  const [unifiedResult, setUnifiedResult] = useState<any | null>(null);
  const [unifiedLoading, setUnifiedLoading] = useState(false);

  // Interpretation Gate State -- SIMPLIFIED: Auto-run
  const [parsedDecision, setParsedDecision] = useState<any | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  // Horizon Selection State
  const [showHorizonSelector, setShowHorizonSelector] = useState(false);
  const [horizonCategory, setHorizonCategory] = useState<HorizonCategory | null>(null);
  const [horizonValue, setHorizonValue] = useState<number>(30);
  const [skipHorizonSelector, setSkipHorizonSelector] = useState(false);

  // Error State
  const [err, setErr] = useState<string | null>(null);

  const { startTutorial, isTutorialActive } = useTutorial();

  // Tax Profile Persistence (NEW)
  useEffect(() => {
    // Try to load GLOBAL profile first
    const globalProfile = localStorage.getItem("gloqont_user_profile");
    if (globalProfile) {
      try {
        const p = JSON.parse(globalProfile);
        setTaxCountry(p.country || "US");
        // Reset sub-jurisdiction as it might not be in global profile yet
        setTaxSubJurisdiction(null);
      } catch (e) {
        console.error("Failed to parse global profile", e);
      }
      return;
    }

    // Fallback to old tax profile
    const saved = localStorage.getItem("gloqont_tax_profile");
    if (saved) {
      try {
        const p = JSON.parse(saved);
        setTaxCountry(p.taxCountry);
        setTaxSubJurisdiction(p.taxSubJurisdiction);
        setTaxAccountType(p.taxAccountType);
        setTaxIncomeTier(p.taxIncomeTier);
        setTaxFilingStatus(p.taxFilingStatus);
        setTaxHoldingPeriod(p.taxHoldingPeriod || "short_term");
      } catch (e) {
        console.error("Failed to parse tax profile", e);
      }
    }
  }, []);



  // Start the scenario simulation tutorial when the page loads
  useEffect(() => {
    const tutorialParam = searchParams.get("tutorial");
    const hasCompletedTutorial = localStorage.getItem("hasCompletedTutorial_v2");

    // Auto-start if requested explicitly OR if first time user
    if (
      (tutorialParam === "scenario" && !isTutorialActive) ||
      (!tutorialParam && !isTutorialActive && !hasCompletedTutorial)
    ) {
      const timer = setTimeout(() => {
        startTutorial(SCENARIO_SIMULATION_TUTORIAL);
      }, 500);

      return () => clearTimeout(timer);
    }
  }, [searchParams, startTutorial, isTutorialActive]);

  // Load current portfolio on page load
  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const res = await apiFetch("/api/v1/portfolio/current", { method: "GET" });
        if (!mounted) return;
        setPortfolio(res.portfolio ?? null);
      } catch (e: any) {
        if (!mounted) return;
        setErr(e.message || "Failed to load current portfolio.");
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  // subscribe to server-sent price updates for portfolio tickers
  useEffect(() => {
    if (!portfolio?.positions?.length) return;
    const tickers = portfolio.positions.map((p) => p.ticker).join(",");
    const es = new EventSource(`/api/v1/market/stream?tickers=${encodeURIComponent(tickers)}`);
    es.onmessage = (ev) => {
      try {
        const d = JSON.parse(ev.data);
        setMarketContext((prev: any) => ({ ...prev, latest_prices: d.prices, ts: d.ts }));
      } catch (err) {
        // ignore
      }
    };
    es.onerror = () => {
      es.close();
    };
    return () => {
      es.close();
    };
  }, [portfolio?.positions?.length]);

  const positionsSummary = useMemo(() => {
    if (!portfolio?.positions?.length) return "";
    return portfolio.positions
      .map((p) => `${p.ticker} ${(p.weight * 100).toFixed(0)}%`)
      .join(" • ");
  }, [portfolio]);

  // Helper: Check if decision should skip horizon selector
  function shouldSkipHorizonSelector(decision: any): boolean {
    const text = decisionText.toLowerCase();
    // Rebalance or sell-all decisions are immediate
    const immediatePatterns = [
      /rebalance/i,
      /sell\s+(my\s+)?(entire|whole|all)/i,
      /liquidate/i,
      /close\s+(all|my)/i
    ];
    if (immediatePatterns.some(p => p.test(text))) return true;

    // Check if any action has explicit timing (delay)
    if (decision?.actions?.length > 0) {
      const hasExplicitTiming = decision.actions.some((a: any) =>
        a.timing?.type === "delay" && (a.timing?.delay_days > 0 || a.timing?.delay_hours > 0)
      );
      if (hasExplicitTiming) return true;
    }

    // Check if decision has market shocks (Auto-run scenarios)
    if (decision?.market_shocks?.length > 0) return true;

    return false;
  }

  // Helper: Extract timing from decision and determine appropriate horizon
  function getTimingFromDecision(decision: any): { category: HorizonCategory; value: number } | null {
    // Default for macro scenarios (market shocks) -> Position Trade (1 Month)
    if (decision?.market_shocks?.length > 0) {
      return { category: "position_trade", value: 4 }; // 4 weeks = ~1 month
    }

    if (!decision?.actions?.length) return null;

    for (const action of decision.actions) {
      if (action.timing?.type === "delay") {
        const delayHours = action.timing.delay_hours || 0;
        const delayDays = action.timing.delay_days || 0;

        if (delayHours > 0 && delayDays === 0) {
          // Hours only -> Day Trade
          return { category: "day_trade", value: Math.min(Math.max(delayHours, 1), 24) };
        } else if (delayDays > 0 && delayDays <= 7) {
          // 1-7 days -> Swing Trade
          return { category: "swing_trade", value: delayDays };
        } else if (delayDays > 7 && delayDays <= 180) {
          // 1 week - 6 months -> Position Trade (in weeks)
          return { category: "position_trade", value: Math.max(1, Math.round(delayDays / 7)) };
        } else if (delayDays > 180) {
          // 6+ months -> Long-Term (in months)
          return { category: "long_term", value: Math.max(6, Math.round(delayDays / 30)) };
        }
      }
    }
    return null;
  }

  // Helper: Convert horizon value to days for API
  function getHorizonInDays(): number {
    if (!horizonCategory) return 30;
    const cat = HORIZON_CATEGORIES[horizonCategory];
    switch (cat.unit) {
      case "hours": return Math.max(1, Math.ceil(horizonValue / 24));
      case "days": return horizonValue;
      case "weeks": return horizonValue * 7;
      case "months": return horizonValue * 30;
      default: return 30;
    }
  }

  // Helper: Get horizon in native units for display
  function getHorizonDisplay(): string {
    if (!horizonCategory) return "30 days";
    const cat = HORIZON_CATEGORIES[horizonCategory];
    return `${horizonValue} ${cat.unitLabel.toLowerCase()}`;
  }

  // NEW: Analyze Decision (Interpretation Layer) - Now shows horizon selector
  async function analyzeDecision() {
    setErr(null);
    setParsedDecision(null);
    setUnifiedResult(null);
    setShowHorizonSelector(false);
    setHorizonCategory(null);

    const text = decisionText.trim();
    if (text.length < 3) {
      setErr("Type a decision first (at least a few words).");
      return;
    }

    setIsAnalyzing(true);
    try {
      // 1. Call Interpretation Layer
      const data = await apiFetch("/api/v1/decision/parse", {
        method: "POST",
        body: JSON.stringify({
          decision_text: text,
          tax_country: taxCountry,
        }),
      });

      setParsedDecision(data.decision);

      // VALIDATION GATE: Check for low confidence or critical warnings
      if (data.decision.confidence_score < 0.4 || (data.decision.warnings && data.decision.warnings.some((w: string) => w.includes("not recognized")))) {
        setUnifiedResult(null);
        return;
      }

      // Check if we should skip horizon selector (rebalance/sell all OR explicit timing)
      if (shouldSkipHorizonSelector(data.decision)) {
        // Try to extract timing from the decision
        const extractedTiming = getTimingFromDecision(data.decision);

        if (extractedTiming) {
          // Use the timing specified in the decision
          setHorizonCategory(extractedTiming.category);
          setHorizonValue(extractedTiming.value);
          setSkipHorizonSelector(true);
          runSimulationWithHorizon(extractedTiming.category, extractedTiming.value);
        } else {
          // No timing found, default to Day Trade (for rebalance/sell all)
          setHorizonCategory("day_trade");
          setHorizonValue(HORIZON_CATEGORIES.day_trade.default);
          setSkipHorizonSelector(true);
          runSimulationWithHorizon("day_trade", HORIZON_CATEGORIES.day_trade.default);
        }
      } else {
        // Show horizon selector for user to choose
        setShowHorizonSelector(true);
      }

    } catch (e: any) {
      setErr(e.message || "Failed to analyze decision.");
    } finally {
      setIsAnalyzing(false);
    }
  }

  // Run simulation with specific horizon
  async function runSimulationWithHorizon(category: HorizonCategory, value: number) {
    setUnifiedLoading(true);
    setShowHorizonSelector(false);

    // Calculate horizon in days based on category
    const cat = HORIZON_CATEGORIES[category];
    let horizonDays: number;
    switch (cat.unit) {
      case "hours": horizonDays = Math.max(1, Math.ceil(value / 24)); break;
      case "days": horizonDays = value; break;
      case "weeks": horizonDays = value * 7; break;
      case "months": horizonDays = value * 30; break;
      default: horizonDays = 30;
    }

    try {
      console.log("Sending simulation request...", { horizonDays, category, value });
      const data = await apiFetch("/api/v1/decision/simulate", {
        method: "POST",
        body: JSON.stringify({
          decision_text: decisionText.trim(),
          mode: "full",
          horizon_days: horizonDays,
          horizon_unit: cat.unit,
          horizon_value: value,
          n_paths: 1000,
          return_paths: true,
          tax_jurisdiction: taxCountry,
          tax_sub_jurisdiction: taxSubJurisdiction,
          tax_account_type: taxAccountType,
          tax_holding_period: taxHoldingPeriod,
          tax_income_tier: taxIncomeTier,
          tax_filing_status: taxFilingStatus,
        }),
      });

      console.log("Simulation Result:", data);

      // Add horizon info to result for display
      data.horizonCategory = category;
      data.horizonValue = value;
      data.horizonUnit = cat.unit;
      data.horizonDays = horizonDays;

      setUnifiedResult(data);
      console.log("Unified Result Set");

    } catch (e: any) {
      console.error("Simulation Error:", e);
      setErr(e.message || "Failed to run simulation.");
    } finally {
      setUnifiedLoading(false);
    }
  }

  // Handler when user selects a horizon category
  function handleHorizonCategorySelect(category: HorizonCategory) {
    setHorizonCategory(category);
    setHorizonValue(HORIZON_CATEGORIES[category].default);
  }

  // Handler to run simulation after horizon selection
  function handleRunWithHorizon() {
    if (!horizonCategory) return;
    runSimulationWithHorizon(horizonCategory, horizonValue);
  }

  // Re-typing return to fix potential hidden chars
  const taxAnalysis = unifiedResult?.tax_analysis || null;

  // Helper: Get horizon constraints based on country and category
  function getHorizonConstraints(category: HorizonCategory): { max: number; hint?: string } {
    const defaultMax = HORIZON_CATEGORIES[category].max;

    // Only apply custom constraints for "Day Trade"
    if (category !== "day_trade") {
      return { max: defaultMax };
    }

    // Market Hours Logic
    // India: 9:15 AM - 3:30 PM = 6h 15m (~6.5h) -> Cap at 6 hours for simplicity or 7
    // US: 9:30 AM - 4:00 PM = 6h 30m (~6.5h) -> Cap at 7 hours

    if (taxCountry === "IN") {
      return {
        max: 6,
        hint: "Market Hours: 9:15 AM - 3:30 PM (IST)"
      };
    } else if (taxCountry === "US") {
      return {
        max: 7,
        hint: "Market Hours: 9:30 AM - 4:00 PM (ET)"
      };
    }

    return { max: defaultMax, hint: "Intraday" };
  }

  const horizonConstraints = horizonCategory ? getHorizonConstraints(horizonCategory) : { max: 24 };

  return (
    <div className="min-h-screen px-6 py-8">
      <div className="mx-auto max-w-5xl">

        <div className="mb-8">
          <div className="text-sm text-white/50">GLOQONT</div>
          <h1 className="text-3xl font-semibold tracking-tight text-white">Scenario Simulation</h1>
        </div>

        {/* Top Controls: Portfolio & Tax */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <EmberCard title="Active Portfolio" id="scenario-portfolio-summary">
            <div className="text-sm text-white/50 mb-1">Current Holdings</div>
            {portfolio ? (
              <div>
                <div className="text-xl font-bold text-white tracking-wide">
                  {portfolio.name}
                </div>
                <div className="text-2xl font-mono text-[#D4A853] mt-1 tabular-nums drop-shadow-[0_0_8px_rgba(212,168,83,0.3)]">
                  {fmtMoney(portfolio.total_value, JURISDICTIONS[taxCountry]?.currency)}
                </div>
              </div>
            ) : (
              <div className="text-red-400 text-sm italic">No portfolio selected</div>
            )}
          </EmberCard>

          <EmberCard title="Tax Jurisdiction" id="tax-country-and-actions">
            <div className="text-sm text-white/50 mb-1">Fiscal Residency</div>
            <div className="flex items-center gap-4 mt-1">
              <div className="text-4xl filter drop-shadow-[0_0_10px_rgba(255,255,255,0.1)]">{JURISDICTIONS[taxCountry]?.flag || "🏳️"}</div>
              <div>
                <div className="text-xl font-bold text-white">{JURISDICTIONS[taxCountry]?.label || taxCountry}</div>
                <div className="text-xs text-[#D4A853]/60 uppercase tracking-wider font-mono">Global Profile Active</div>
              </div>
            </div>
          </EmberCard>
        </div>

        {/* Input Area */}
        <div className="mb-10">
          <EmberCard title="Simulation Control" subtitle="Describe your trade" className="relative">
            <div className="relative" id="decision-input">
              <textarea
                value={decisionText}
                onChange={(e) => setDecisionText(e.target.value)}
                placeholder="Describe your decision (e.g., 'Increase tech exposure by 12%' or 'Sell Apple and buy Microsoft')..."
                className="w-full rounded-xl border border-[#D4A853]/20 bg-black/40 p-6 text-xl text-white placeholder-white/20 outline-none focus:border-[#D4A853]/50 focus:shadow-[0_0_15px_rgba(212,168,83,0.1)] min-h-[160px] resize-none transition-all font-sans"
              />
              <div className="absolute bottom-4 right-4 flex items-center gap-4">
                {err && (
                  <div className="text-red-200 text-xs max-w-lg bg-red-900/40 p-2 rounded border border-red-500/30 overflow-auto max-h-32 backdrop-blur-md">
                    <pre className="whitespace-pre-wrap font-mono">{err}</pre>
                  </div>
                )}
                <button
                  id="run-scenario-button"
                  onClick={() => analyzeDecision()}
                  disabled={isAnalyzing || unifiedLoading || !decisionText}
                  className="rounded-lg bg-[#D4A853] text-black px-6 py-3 font-bold hover:bg-[#C9963B] disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center gap-2 shadow-[0_0_20px_rgba(212,168,83,0.2)] hover:shadow-[0_0_30px_rgba(212,168,83,0.4)] uppercase tracking-wider text-sm"
                >
                  {isAnalyzing || unifiedLoading ? (
                    <>
                      <svg className="animate-spin h-4 w-4 text-black" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Simulating...
                    </>
                  ) : (
                    "Init Simulation"
                  )}
                </button>
              </div>
            </div>
          </EmberCard>
        </div>

        {/* Horizon Selection UI */}
        {/* Horizon Selection UI */}
        {showHorizonSelector && parsedDecision && (
          <div className="mb-10 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <EmberCard title="Investment Horizon" subtitle="How long do you plan to hold?">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                {(Object.entries(HORIZON_CATEGORIES) as [HorizonCategory, typeof HORIZON_CATEGORIES[HorizonCategory]][]).map(([key, cat]) => (
                  <button
                    key={key}
                    onClick={() => handleHorizonCategorySelect(key)}
                    className={`p-4 rounded-xl border transition-all text-left ${horizonCategory === key
                      ? "border-[#D4A853] bg-[#D4A853]/20 shadow-[0_0_15px_rgba(212,168,83,0.1)]"
                      : "border-[#D4A853]/10 bg-black/40 hover:border-[#D4A853]/30 hover:bg-[#D4A853]/5"
                      }`}
                  >
                    <div className={`font-bold ${horizonCategory === key ? "text-[#D4A853]" : "text-white"}`}>{cat.label}</div>
                    <div className="text-xs text-white/40 mt-1 font-mono">{cat.description}</div>
                  </button>
                ))}
              </div>

              {/* Slider for fine-tuning */}
              {horizonCategory && (
                <div className="bg-black/40 rounded-xl p-5 mb-8 animate-in fade-in duration-300 border border-[#D4A853]/10">
                  <div className="flex justify-between items-center mb-3">
                    <span className="text-sm text-white/50">
                      Fine-tune your horizon
                      {horizonConstraints.hint && <span className="ml-2 text-[#D4A853]/80">({horizonConstraints.hint})</span>}
                    </span>
                    <span className="text-lg font-bold text-[#D4A853] tabular-nums">
                      {horizonValue} {HORIZON_CATEGORIES[horizonCategory].unitLabel}
                    </span>
                  </div>
                  <input
                    type="range"
                    min={HORIZON_CATEGORIES[horizonCategory].min}
                    max={horizonConstraints.max}
                    value={Math.min(horizonValue, horizonConstraints.max)}
                    onChange={(e) => setHorizonValue(parseInt(e.target.value))}
                    className="w-full h-2 bg-[#D4A853]/20 rounded-lg appearance-none cursor-pointer accent-[#D4A853]"
                  />
                  <div className="flex justify-between text-xs text-white/30 mt-2 font-mono">
                    <span>{HORIZON_CATEGORIES[horizonCategory].min} {HORIZON_CATEGORIES[horizonCategory].unitLabel.toLowerCase()}</span>
                    <span>{horizonConstraints.max} {HORIZON_CATEGORIES[horizonCategory].unitLabel.toLowerCase()}</span>
                  </div>
                </div>
              )}

              {/* Run Button */}
              <div className="flex justify-end">
                <button
                  onClick={handleRunWithHorizon}
                  disabled={!horizonCategory || unifiedLoading}
                  className="rounded-lg bg-[#D4A853] text-black px-8 py-3 font-bold hover:bg-[#C9963B] disabled:opacity-50 transition-all flex items-center gap-2 shadow-[0_0_20px_rgba(212,168,83,0.2)] hover:shadow-[0_0_30px_rgba(212,168,83,0.4)] uppercase tracking-wider text-sm"
                >
                  {unifiedLoading ? (
                    <>
                      <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Running Simulation...
                    </>
                  ) : (
                    <>
                      Analyze for {horizonCategory ? `${Math.min(horizonValue, horizonConstraints.max)} ${HORIZON_CATEGORIES[horizonCategory].unitLabel.toLowerCase()}` : "selected horizon"}
                    </>
                  )}
                </button>
              </div>
            </EmberCard>
          </div>
        )}

        {/* Invalid / Clarification State - Only show when NOT showing horizon selector */}
        {parsedDecision && !showHorizonSelector && (!unifiedResult && !unifiedLoading) && (
          <div className="rounded-2xl border border-[#D4A853]/20 bg-[#D4A853]/5 p-8 text-center animate-in fade-in zoom-in-95 backdrop-blur-xl shadow-[0_0_30px_rgba(212,168,83,0.05)]">
            <div className="mx-auto w-12 h-12 bg-[#D4A853]/20 rounded-full flex items-center justify-center mb-4 shadow-[0_0_15px_rgba(212,168,83,0.2)]">
              <svg className="w-6 h-6 text-[#D4A853]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h3 className="text-xl font-bold text-white mb-2 uppercase tracking-wide">Clarification Needed</h3>
            <p className="text-[#D4A853]/80 max-w-lg mx-auto mb-6 font-mono text-sm leading-relaxed">
              {parsedDecision.warnings && parsedDecision.warnings.length > 0
                ? parsedDecision.warnings[0]
                : "We couldn't quite understand your decision. Please try specifying a ticker (e.g. AAPL) and an action (Buy/Sell)."
              }
            </p>
            <div className="flex flex-wrap justify-center gap-3">
              <button onClick={() => setDecisionText("Buy AAPL 5%")} className="px-4 py-2 rounded-lg bg-[#D4A853]/10 hover:bg-[#D4A853]/20 border border-[#D4A853]/20 text-sm text-[#D4A853] transition font-bold uppercase tracking-wider">Buy AAPL 5%</button>
              <button onClick={() => setDecisionText("Sell my whole portfolio")} className="px-4 py-2 rounded-lg bg-[#D4A853]/10 hover:bg-[#D4A853]/20 border border-[#D4A853]/20 text-sm text-[#D4A853] transition font-bold uppercase tracking-wider">Sell All</button>
            </div>
          </div>
        )}

        {/* ═════════════════════════════════════ Results Analysis ═════════════════════════════════════ */}
        {unifiedResult && (() => {
          const dec = unifiedResult.decision;
          const cmp = unifiedResult.comparison;
          const scr = unifiedResult.score;
          const exc = unifiedResult.execution_context;
          const rsk = unifiedResult.risk_analysis;
          const prj = unifiedResult.projections;
          const tax = unifiedResult.tax_analysis;

          // Compute transaction value from actions
          const totalValue = exc?.total_value_usd ?? portfolio?.total_value ?? 0;
          const actions = dec?.actions ?? [];
          const tradeValue = actions.reduce((sum: number, a: any) => {
            if (a.size_usd) return sum + a.size_usd;
            if (a.size_percent) return sum + (a.size_percent / 100) * totalValue;
            return sum;
          }, 0);

          // Tax layer split
          const taxLayers = tax?.layers ?? [];
          const txnLayers = taxLayers.filter((l: any) => l.category === "transaction");
          const realLayers = taxLayers.filter((l: any) => l.category === "realization");
          const totalTxnTax = txnLayers.reduce((s: number, l: any) => s + (l.amount ?? 0), 0);
          const totalRealTax = realLayers.reduce((s: number, l: any) => s + (l.amount ?? 0), 0);

          // Horizon label from state
          const horizonLabel = `${horizonValue} ${horizonCategory === "day_trade" ? "hours" : horizonCategory === "swing_trade" ? "days" : horizonCategory === "position_trade" ? "weeks" : "months"}`;

          return (
            <div className="animate-in fade-in slide-in-from-bottom-8 duration-700 space-y-6">

              {/* ── 1. Decision Interpretation ── */}
              {dec && (
                <EmberCard title="Decision Interpretation">
                  {actions.map((a: any, i: number) => (
                    <div key={i} className="flex items-center gap-3 text-lg font-medium">
                      <span className={`px-2 py-0.5 rounded text-xs font-bold uppercase tracking-wider ${a.direction?.toLowerCase() === "buy" || a.direction?.toLowerCase() === "cover" ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30" : "bg-red-500/20 text-red-400 border border-red-500/30"
                        }`}>{a.direction}</span>
                      <span className="text-white font-bold">{a.symbol}</span>
                      <span className="text-[#D4A853]/40">—</span>
                      <span className="text-[#D4A853] font-mono">
                        {a.size_usd ? fmtMoney(a.size_usd, JURISDICTIONS[taxCountry]?.currency) : a.size_percent ? `${a.size_percent}% of portfolio` : ""}
                      </span>
                      {a.timing?.type === "delay" && (
                        <span className="text-xs text-blue-400 bg-blue-400/10 px-2 py-0.5 rounded border border-blue-400/20 ml-2">
                          @ T+{a.timing.delay_days}d
                        </span>
                      )}
                    </div>
                  ))}

                  {/* Market Shocks Visualization */}
                  {dec.market_shocks && dec.market_shocks.map((s: any, i: number) => (
                    <div key={`shock-${i}`} className="flex items-center gap-3 text-lg font-medium mt-2 pt-2 border-t border-white/5">
                      <span className="px-2 py-0.5 rounded text-xs font-bold uppercase tracking-wider bg-purple-500/20 text-purple-400 border border-purple-500/30">
                        MACRO SHOCK
                      </span>
                      <span className="text-white font-bold">{s.target}</span>
                      <span className="text-[#D4A853]/40">→</span>
                      <span className={`font-mono ${s.magnitude > 0 ? "text-emerald-400" : "text-red-400"}`}>
                        {s.magnitude > 0 ? "+" : ""}{s.magnitude}{s.unit === "percent" ? "%" : ""}
                      </span>
                      <span className="text-xs text-white/40 italic ml-2">({s.shock_type.replace(/_/g, " ").toLowerCase()})</span>
                    </div>
                  ))}
                </EmberCard>
              )}

              {/* ── 2. Portfolio Impact ── */}
              {exc && (
                <EmberCard title="Portfolio Impact">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Portfolio Value */}
                    <div>
                      <div className="text-sm text-white/50">Projected Value</div>
                      <div className="text-2xl font-bold text-white tracking-wide">{fmtMoney(totalValue, JURISDICTIONS[taxCountry]?.currency)}</div>
                      {exc.interpretation && (
                        <div className="text-xs text-[#D4A853]/60 mt-2 font-mono border-l-2 border-[#D4A853]/30 pl-3 py-1 bg-[#D4A853]/5 rounded-r">{exc.interpretation}</div>
                      )}
                    </div>
                  </div>

                  {/* Asset Changes */}
                  {exc.asset_deltas && exc.asset_deltas.length > 0 && (
                    <div className="mt-6">
                      <div className="text-xs font-bold text-[#D4A853] uppercase tracking-wider mb-3">Asset Reallocation</div>
                      <div className="space-y-3">
                        {exc.asset_deltas.map((d: any, i: number) => (
                          <div key={i} className="flex items-center justify-between bg-black/40 border border-[#D4A853]/10 rounded-lg p-3">
                            <span className="font-mono text-white font-bold">{d.symbol}</span>
                            <div className="flex items-center gap-3 text-sm font-mono">
                              <span className="text-white/50">{fmtPct(d.weight_before * 100)}</span>
                              <span className="text-[#D4A853]/40">→</span>
                              <span className="text-white">{fmtPct(d.weight_after * 100)}</span>
                              <span className={`font-bold ${d.weight_delta >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                                {fmtPct(d.weight_delta * 100)}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </EmberCard>
              )}

              {/* ── 3. Future Risk Paths (skip for day_trade) ── */}
              {/* Double check both state and result to ensure day trades are hidden */}
              {cmp && horizonCategory !== "day_trade" && unifiedResult.horizonCategory !== "day_trade" && unifiedResult.horizonDays > 1 && (() => {
                const scenarioVol = (cmp.scenario_volatility ?? 15) / 100; // annual vol as decimal
                const dailyVol = scenarioVol / Math.sqrt(252);
                const dailyDrift = 0.0001;
                const N_PATHS = 1000;

                // Build sub-horizons based on the selected category & slider value
                let subHorizons: { label: string; days: number; subtitle: string }[] = [];

                if (horizonCategory === "swing_trade") {
                  // Swing: slider is in days (2-7). Show 1-day steps up to selected value
                  const maxDays = Math.min(horizonValue, 7);
                  if (maxDays >= 2) subHorizons.push({ label: "2 Days", days: 2, subtitle: "2d" });
                  if (maxDays >= 3) subHorizons.push({ label: "3 Days", days: 3, subtitle: "3d" });
                  if (maxDays >= 5) subHorizons.push({ label: "5 Days", days: 5, subtitle: "5d" });
                  if (maxDays >= 7) subHorizons.push({ label: "1 Week", days: 7, subtitle: "7d" });
                  if (subHorizons.length === 0) subHorizons.push({ label: `${maxDays} Days`, days: maxDays, subtitle: `${maxDays}d` });
                } else if (horizonCategory === "position_trade") {
                  // Position: slider is in weeks (1-26)
                  const maxWeeks = Math.min(horizonValue, 26);
                  if (maxWeeks >= 1) subHorizons.push({ label: "1 Week", days: 7, subtitle: "7 days" });
                  if (maxWeeks >= 2) subHorizons.push({ label: "2 Weeks", days: 14, subtitle: "14 days" });
                  if (maxWeeks >= 4) subHorizons.push({ label: "1 Month", days: 28, subtitle: "28 days" });
                  if (maxWeeks >= 8) subHorizons.push({ label: "2 Months", days: 56, subtitle: "56 days" });
                  if (maxWeeks >= 13) subHorizons.push({ label: "3 Months", days: 91, subtitle: "91 days" });
                  if (maxWeeks >= 26) subHorizons.push({ label: "6 Months", days: 182, subtitle: "182 days" });
                  // Ensure at least the user's selected horizon is shown
                  const selectedDays = maxWeeks * 7;
                  if (!subHorizons.some(h => h.days === selectedDays) && maxWeeks > 0) {
                    subHorizons.push({ label: `${maxWeeks} Weeks`, days: selectedDays, subtitle: `${selectedDays} days` });
                    subHorizons.sort((a, b) => a.days - b.days);
                  }
                  // Take at most 4
                  if (subHorizons.length > 4) {
                    const first = subHorizons[0];
                    const last = subHorizons[subHorizons.length - 1];
                    const mid1 = subHorizons[Math.floor(subHorizons.length / 3)];
                    const mid2 = subHorizons[Math.floor(2 * subHorizons.length / 3)];
                    subHorizons = [first, mid1, mid2, last];
                  }
                } else if (horizonCategory === "long_term") {
                  // Long-term: slider is in months (6-60). Show standard horizons up to selected
                  const maxMonths = Math.min(horizonValue, 60);
                  if (maxMonths >= 1) subHorizons.push({ label: "1 Month", days: 30, subtitle: "30 days" });
                  if (maxMonths >= 3) subHorizons.push({ label: "3 Months", days: 90, subtitle: "90 days" });
                  if (maxMonths >= 6) subHorizons.push({ label: "6 Months", days: 180, subtitle: "180 days" });
                  if (maxMonths >= 12) subHorizons.push({ label: "1 Year", days: 365, subtitle: "365 days" });
                  if (maxMonths >= 24) subHorizons.push({ label: "2 Years", days: 730, subtitle: "730 days" });
                  if (maxMonths >= 36) subHorizons.push({ label: "3 Years", days: 1095, subtitle: "1095 days" });
                  if (maxMonths >= 60) subHorizons.push({ label: "5 Years", days: 1825, subtitle: "1825 days" });
                  // Take at most 4
                  if (subHorizons.length > 4) {
                    const first = subHorizons[0];
                    const last = subHorizons[subHorizons.length - 1];
                    const mid1 = subHorizons[Math.floor(subHorizons.length / 3)];
                    const mid2 = subHorizons[Math.floor(2 * subHorizons.length / 3)];
                    subHorizons = [first, mid1, mid2, last];
                  }
                }

                if (subHorizons.length === 0) return null;

                // Compute MC for each sub-horizon
                const pathResults = subHorizons.map(h => {
                  const returns: number[] = [];
                  for (let p = 0; p < N_PATHS; p++) {
                    let cumReturn = 1.0;
                    for (let d = 0; d < h.days; d++) {
                      // Box-Muller for normal random
                      const u1 = Math.random();
                      const u2 = Math.random();
                      const z = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
                      cumReturn *= (1 + dailyDrift + dailyVol * z);
                    }
                    returns.push((cumReturn - 1) * 100);
                  }
                  returns.sort((a, b) => a - b);
                  return {
                    ...h,
                    best_case: returns[returns.length - 1],
                    worst_case: returns[0],
                    median: returns[Math.floor(returns.length / 2)],
                    n_paths: N_PATHS,
                  };
                });

                return (
                  <EmberCard title="Future Risk Paths" subtitle="Monte Carlo projections across selected horizon">
                    <div className={`mt-4 grid gap-4 ${pathResults.length <= 2 ? "grid-cols-1 md:grid-cols-2" : "grid-cols-2 md:grid-cols-4"}`}>
                      {pathResults.map((data, idx) => (
                        <div key={idx} className="rounded-xl border border-[#D4A853]/10 bg-black/40 p-4 relative overflow-hidden group hover:border-[#D4A853]/30 transition-all">
                          <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-[#D4A853]/30 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />

                          <div className="text-center mb-3">
                            <div className="text-lg font-bold text-white tracking-wide">{data.label}</div>
                            <div className="text-xs text-[#D4A853]/60 font-mono">{data.subtitle}</div>
                          </div>

                          <div className="space-y-2">
                            <div className="flex justify-between items-center">
                              <span className="text-xs text-white/40 uppercase tracking-wider">Best</span>
                              <span className="text-sm font-mono text-emerald-400 font-bold">+{data.best_case.toFixed(1)}%</span>
                            </div>
                            <div className="flex justify-between items-center">
                              <span className="text-xs text-white/40 uppercase tracking-wider">Median</span>
                              <span className={`text-sm font-mono font-bold ${data.median >= 0 ? "text-white" : "text-red-400"}`}>
                                {data.median >= 0 ? "+" : ""}{data.median.toFixed(1)}%
                              </span>
                            </div>
                            <div className="flex justify-between items-center">
                              <span className="text-xs text-white/40 uppercase tracking-wider">Worst</span>
                              <span className="text-sm font-mono text-red-400 font-bold">{data.worst_case.toFixed(1)}%</span>
                            </div>
                          </div>

                          {/* Mini visualization bar */}
                          <div className="mt-4 h-1.5 bg-black/50 rounded-full overflow-hidden relative border border-white/5">
                            <div className="absolute left-1/2 h-full bg-white/40 w-[1px]" />
                            <div
                              className="absolute h-full bg-gradient-to-r from-red-500 via-amber-500 to-emerald-500 opacity-70"
                              style={{
                                left: `${Math.max(0, 50 + Math.min(data.worst_case, 0) * 0.5)}%`,
                                width: `${Math.min(100, Math.abs(data.best_case - data.worst_case) * 0.5)}%`
                              }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>

                    <div className="mt-4 text-[10px] text-[#D4A853]/40 text-center font-mono uppercase tracking-widest">
                      Based on {N_PATHS.toLocaleString()} Monte Carlo simulations per horizon
                    </div>
                  </EmberCard>
                );
              })()}

              {/* ── 4. Risk & Return Analysis Table ── */}
              {cmp && (
                <EmberCard title="Risk & Return Analysis">
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-[#D4A853]/20">
                          <th className="px-3 py-3 text-left text-[#D4A853]/60 font-mono text-xs uppercase tracking-wider">Metric</th>
                          <th className="px-3 py-3 text-center text-[#D4A853]/60 font-mono text-xs uppercase tracking-wider">Current</th>
                          <th className="px-3 py-3 text-center text-[#D4A853]/60 font-mono text-xs uppercase tracking-wider">With Decision</th>
                          <th className="px-3 py-3 text-center text-[#D4A853]/60 font-mono text-xs uppercase tracking-wider">Impact</th>
                        </tr>
                      </thead>
                      <tbody>
                        {[
                          { label: "Expected Return", base: cmp.baseline_expected_return, scen: cmp.scenario_expected_return, delta: cmp.delta_return, positive: true },
                          { label: "Price Fluctuation (Vol)", base: cmp.baseline_volatility, scen: cmp.scenario_volatility, delta: cmp.delta_volatility, positive: false },
                          { label: "Max Drop (Drawdown)", base: cmp.baseline_max_drawdown, scen: cmp.scenario_max_drawdown, delta: cmp.delta_drawdown, positive: false },
                          { label: "Extreme Loss (Tail Risk)", base: cmp.baseline_tail_loss, scen: cmp.scenario_tail_loss, delta: cmp.delta_tail_loss, positive: false },
                        ].map((row) => {
                          const isGood = row.positive ? (row.delta ?? 0) > 0 : (row.delta ?? 0) < 0;
                          const isBad = row.positive ? (row.delta ?? 0) < 0 : (row.delta ?? 0) > 0;
                          return (
                            <tr key={row.label} className="border-b border-white/5 group hover:bg-white/5 transition-colors">
                              <td className="px-3 py-3 text-white font-medium">{row.label}</td>
                              <td className="px-3 py-3 text-center text-white/60 font-mono text-xs">{fmtPct(row.base ?? 0)}</td>
                              <td className="px-3 py-3 text-center text-white font-mono text-xs font-bold">{fmtPct(row.scen ?? 0)}</td>
                              <td className={`px-3 py-3 text-center font-bold text-xs font-mono uppercase tracking-wider ${isGood ? "text-emerald-400" : isBad ? "text-red-400" : "text-white/40"}`}>
                                {fmtPct(row.delta ?? 0)}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </EmberCard>
              )}

              {/* ── 5. Verdict ── */}
              {scr && (
                <div className={`rounded-2xl border p-6 text-center backdrop-blur-xl transition-all shadow-2xl ${(scr.composite_score ?? 0) >= 60 ? "border-emerald-500/30 bg-emerald-500/10 shadow-[0_0_30px_rgba(16,185,129,0.1)]" :
                  (scr.composite_score ?? 0) >= 40 ? "border-amber-500/30 bg-amber-500/10 shadow-[0_0_30px_rgba(245,158,11,0.1)]" :
                    "border-red-500/30 bg-red-500/10 shadow-[0_0_30px_rgba(239,68,68,0.1)]"
                  }`}>
                  <div className={`text-5xl font-black tracking-tighter ${(scr.composite_score ?? 0) >= 60 ? "text-emerald-400 drop-shadow-[0_0_10px_rgba(16,185,129,0.3)]" :
                    (scr.composite_score ?? 0) >= 40 ? "text-amber-400 drop-shadow-[0_0_10px_rgba(245,158,11,0.3)]" :
                      "text-red-400 drop-shadow-[0_0_10px_rgba(239,68,68,0.3)]"
                    }`}>
                    {(scr.composite_score ?? 0).toFixed(0)} <span className="text-xl font-normal text-white/30 align-top ml-1">/ 100</span>
                  </div>
                  {scr.summary && <div className="text-white/80 mt-2 font-medium max-w-2xl mx-auto">{scr.summary}</div>}
                  {scr.key_factors && scr.key_factors.length > 0 && (
                    <div className="mt-4 flex flex-wrap justify-center gap-2">
                      {scr.key_factors.map((f: string, i: number) => (
                        <span key={i} className="text-xs bg-black/30 border border-white/10 rounded-full px-3 py-1 text-white/70 uppercase tracking-wide">• {f}</span>
                      ))}
                    </div>
                  )}
                </div>
              )}


              {/* ── 6. Risk Detail Cards ── */}
              {rsk && (
                <EmberCard title="Risk Deconstruction" subtitle="Deep dive into risk factors">
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                    {/* Primary Risks */}
                    {rsk.primary_risk_drivers && rsk.primary_risk_drivers.length > 0 && (
                      <div className="rounded-xl border border-[#D4A853]/10 bg-black/40 p-5 flex flex-col h-full">
                        <div className="text-xs text-white/50 mb-3 uppercase tracking-wider">Primary Risks</div>
                        <div className="space-y-1">
                          {rsk.primary_risk_drivers.map((r: string, i: number) => (
                            <div key={i} className="text-sm text-white/90 font-medium leading-tight">• {r}</div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Time to Impact */}
                    {rsk.time_to_risk_days != null && (
                      <div className="rounded-xl border border-[#D4A853]/10 bg-black/40 p-5 flex flex-col h-full">
                        <div className="text-xs text-white/50 mb-2 uppercase tracking-wider">Time to Impact</div>
                        <div className="text-3xl font-bold text-amber-400 tabular-nums">{Math.round(rsk.time_to_risk_days)} <span className="text-lg font-normal text-white/40">Days</span></div>
                        <div className="text-xs text-white/40 mt-auto pt-2 leading-snug">Estimated time before risks materialize.</div>
                      </div>
                    )}

                    {/* Permanent Loss Risk */}
                    {rsk.worst_case_permanent_loss_usd != null && (
                      <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-5 flex flex-col h-full">
                        <div className="text-xs text-white/50 mb-2 uppercase tracking-wider">Permanent Loss Risk</div>
                        <div className="text-3xl font-bold text-red-400 tabular-nums tracking-tight">{fmtMoney(Math.abs(rsk.worst_case_permanent_loss_usd), JURISDICTIONS[taxCountry]?.currency)}</div>
                        <div className="text-xs text-white/40 mt-auto pt-2 leading-snug">Panic-exit during adverse conditions could lock in long-term capital damage.</div>
                      </div>
                    )}

                    {/* Risk / Reward */}
                    {rsk.risk_reward_ratio && (
                      <div className="rounded-xl border border-[#D4A853]/10 bg-black/40 p-5 flex flex-col h-full">
                        <div className="text-xs text-white/50 mb-2 uppercase tracking-wider">Risk / Reward</div>
                        <div className="text-3xl font-bold text-white tabular-nums">{rsk.risk_reward_ratio}</div>
                        <div className="text-xs text-white/40 mt-auto pt-2 leading-snug">
                          For every $1 risk, {(() => {
                            const parts = rsk.risk_reward_ratio.split(":");
                            // Ensure parts[1] exists and is trimmed
                            const potentialUpside = parts.length === 2 ? parts[1].trim() : "";
                            return potentialUpside ? <span className="text-[#D4A853] font-bold">${potentialUpside}</span> : "";
                          })()} potential upside.
                        </div>
                      </div>
                    )}
                  </div>
                </EmberCard>
              )}

              {/* ── 7. Tax Impact Analysis (3-Layer) ── */}
              {tax && !tax.error && (() => {
                const isNL = tax.jurisdiction === "NL";
                const isBuyOnly = tax.is_buy_only ?? !actions.some((a: any) => ["sell", "reduce", "liquidate", "short", "cover"].includes(a?.direction?.toLowerCase?.()));
                const exitAssumptions = tax.exit_assumptions || unifiedResult.tax_metrics ? {
                  trigger: "Scenario Simulation Exit",
                  holding_period_days: horizonValue,
                  tax_regime: tax.tax_regime_applied || (tax.holding_period === "long_term" ? "Long-Term Capital Gains" : "Short-Term Capital Gains"),
                } : null;
                const taxMetrics = unifiedResult.tax_metrics;
                const grossGain = tax.estimated_gain_usd || 0;
                const totalAllTax = totalTxnTax + totalRealTax;
                const netProfit = grossGain - totalAllTax;
                const effectiveDrag = grossGain > 0 ? ((totalAllTax / grossGain) * 100) : 0;

                return (
                  <EmberCard title="Tax Impact Analysis" subtitle={tax.jurisdiction_name ? `Jurisdiction: ${tax.jurisdiction_name}` : undefined}>

                    {/* Layer 1: Decision Context */}
                    <div className="mt-4 mb-6 rounded-xl bg-black/40 border border-[#D4A853]/10 p-4">
                      <div className="text-xs font-bold text-[#D4A853] uppercase tracking-wider mb-3">Decision Context</div>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
                        <div>
                          <div className="text-white/40 mb-1">Account Type</div>
                          <div className="text-white font-medium">{(COUNTRY_ACCOUNT_TYPES[taxCountry]?.[tax.account_type] || DEFAULT_ACCOUNT_TYPES[tax.account_type] || tax.account_type || "Taxable Brokerage")}</div>
                        </div>
                        <div>
                          <div className="text-white/40 mb-1">Residency</div>
                          <div className="text-white font-medium">{tax.jurisdiction_name || JURISDICTIONS[taxCountry]?.label || taxCountry}</div>
                        </div>
                        <div>
                          <div className="text-white/40 mb-1">Assuming Hold</div>
                          <div className="text-white font-medium">{horizonLabel}</div>
                        </div>
                        <div>
                          <div className="text-white/40 mb-1">Asset Class</div>
                          <div className="text-white capitalize font-medium">{(tax.asset_class || "equity_domestic").replace(/_/g, " ")}</div>
                        </div>
                      </div>
                      {tax.tax_regime_applied && (
                        <div className="mt-3 text-xs text-white/50 border-t border-white/5 pt-2">
                          Tax Category: <span className="text-[#D4A853] font-medium">{tax.tax_regime_applied}</span>
                        </div>
                      )}
                    </div>

                    {/* Layer 2: Immediate Execution Taxes */}
                    <div className="mb-6">
                      <div className="text-sm font-bold text-white mb-3 flex items-center gap-2">
                        <span className="w-1 h-1 bg-[#D4A853] rounded-full" />
                        Immediate Execution Taxes (On {actions[0]?.direction || "Trade"})
                      </div>
                      {txnLayers.length > 0 ? (
                        <div className="overflow-x-auto rounded-lg border border-white/5">
                          <table className="w-full text-sm">
                            <thead className="bg-white/5">
                              <tr className="border-b border-white/10">
                                <th className="px-3 py-2 text-left text-white/60 font-mono text-xs uppercase">Layer</th>
                                <th className="px-3 py-2 text-center text-white/60 font-mono text-xs uppercase">Rate</th>
                                <th className="px-3 py-2 text-center text-white/60 font-mono text-xs uppercase">Amount</th>
                                <th className="px-3 py-2 text-left text-white/60 font-mono text-xs uppercase">Applied On</th>
                              </tr>
                            </thead>
                            <tbody>
                              {txnLayers.map((l: any, i: number) => (
                                <tr key={i} className="border-b border-white/5 last:border-0 hover:bg-white/5 transition-colors">
                                  <td className="px-3 py-2 text-white/80">{l.name}</td>
                                  <td className="px-3 py-2 text-center text-white/60 font-mono">{typeof l.rate === 'number' ? `${(l.rate < 1 ? l.rate * 100 : l.rate).toFixed(2)}%` : l.rate}</td>
                                  <td className="px-3 py-2 text-center text-red-400 font-mono">{fmtMoney(l.amount, JURISDICTIONS[taxCountry]?.currency)}</td>
                                  <td className="px-3 py-2 text-white/50 text-xs capitalize">{(l.applies_to || "transaction_value").replace(/_/g, " ")}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                          <div className="bg-red-500/10 p-2 text-sm font-bold text-right text-red-400 border-t border-red-500/20">
                            Total Execution Friction: {fmtMoney(totalTxnTax, JURISDICTIONS[taxCountry]?.currency)}
                          </div>
                        </div>
                      ) : (
                        <div className="text-sm text-white/40 italic pl-3 border-l-2 border-white/10">No execution taxes for this jurisdiction/event.</div>
                      )}
                    </div>

                    {/* Layer 3: Realization Taxes OR Wealth Regime */}
                    <div className="mb-6">
                      {isNL ? (
                        <>
                          <div className="text-sm font-bold text-white mb-3 flex items-center gap-2">
                            <span className="w-1 h-1 bg-[#D4A853] rounded-full" />
                            Projected Wealth Tax Impact (Box 3 — Netherlands)
                          </div>
                          {realLayers.length > 0 ? (
                            <div className="overflow-x-auto rounded-lg border border-white/5">
                              <table className="w-full text-sm">
                                <thead className="bg-white/5">
                                  <tr className="border-b border-white/10">
                                    <th className="px-3 py-2 text-left text-white/60 font-mono text-xs uppercase">Component</th>
                                    <th className="px-3 py-2 text-center text-white/60 font-mono text-xs uppercase">Rate</th>
                                    <th className="px-3 py-2 text-center text-white/60 font-mono text-xs uppercase">Annual Amount</th>
                                    <th className="px-3 py-2 text-left text-white/60 font-mono text-xs uppercase">Description</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {realLayers.map((l: any, i: number) => (
                                    <tr key={i} className="border-b border-white/5 last:border-0 hover:bg-white/5 transition-colors">
                                      <td className="px-3 py-2 text-white/80">{l.name}</td>
                                      <td className="px-3 py-2 text-center text-white/60 font-mono">{typeof l.rate === 'number' ? `${(l.rate < 1 ? l.rate * 100 : l.rate).toFixed(2)}%` : l.rate}</td>
                                      <td className="px-3 py-2 text-center text-amber-400 font-mono">{fmtMoney(l.amount, JURISDICTIONS[taxCountry]?.currency)}</td>
                                      <td className="px-3 py-2 text-white/50 text-xs">{l.description || ""}</td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                              <div className="p-2 text-xs text-white/40 bg-white/5 border-t border-white/10">
                                Netherlands has NO capital gains tax. Tax is based on deemed return (Box 3 wealth tax), applied annually to portfolio value.
                              </div>
                            </div>
                          ) : (
                            <div className="text-sm text-white/40 italic pl-3 border-l-2 border-white/10">No wealth tax applicable (below €57,000 exemption threshold).</div>
                          )}
                        </>
                      ) : (
                        <>
                          <div className="text-sm font-bold text-white mb-3 flex items-center gap-2">
                            <span className="w-1 h-1 bg-[#D4A853] rounded-full" />
                            {isBuyOnly ? "Projected Realization Taxes (If You Exit Within Horizon)" : "Realization Taxes (If Scenario Exit Occurs)"}
                          </div>
                          {isBuyOnly && realLayers.length === 0 ? (
                            <div className="rounded-lg bg-emerald-500/10 border border-emerald-500/20 p-3 text-sm flex items-center gap-2">
                              <svg className="w-4 h-4 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
                              <div>
                                <span className="text-emerald-400 font-bold">No projected realization taxes</span>
                                <span className="text-white/50 ml-1">— Projected return is ≤ 0, so no capital gains tax would apply on exit.</span>
                              </div>
                            </div>
                          ) : realLayers.length > 0 ? (
                            <div className="overflow-x-auto rounded-lg border border-white/5">
                              <table className="w-full text-sm">
                                <thead className="bg-white/5">
                                  <tr className="border-b border-white/10">
                                    <th className="px-3 py-2 text-left text-white/60 font-mono text-xs uppercase">Layer</th>
                                    <th className="px-3 py-2 text-center text-white/60 font-mono text-xs uppercase">Rate</th>
                                    <th className="px-3 py-2 text-center text-white/60 font-mono text-xs uppercase">Amount</th>
                                    <th className="px-3 py-2 text-left text-white/60 font-mono text-xs uppercase">Description</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {realLayers.map((l: any, i: number) => (
                                    <tr key={i} className="border-b border-white/5 last:border-0 hover:bg-white/5 transition-colors">
                                      <td className="px-3 py-2 text-white/80">{l.name}</td>
                                      <td className="px-3 py-2 text-center text-white/60 font-mono">{typeof l.rate === 'number' ? `${(l.rate < 1 ? l.rate * 100 : l.rate).toFixed(2)}%` : l.rate}</td>
                                      <td className="px-3 py-2 text-center text-red-400 font-mono">{fmtMoney(l.amount, JURISDICTIONS[taxCountry]?.currency)}</td>
                                      <td className="px-3 py-2 text-white/50 text-xs">{l.description || ""}</td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                              <div className="bg-red-500/10 p-2 text-sm font-bold text-right text-red-400 border-t border-red-500/20">
                                Total Realization Tax: {fmtMoney(totalRealTax, JURISDICTIONS[taxCountry]?.currency)}
                              </div>
                            </div>
                          ) : (
                            <div className="text-sm text-white/40 italic pl-3 border-l-2 border-white/10">No realization taxes for this event.</div>
                          )}
                        </>
                      )}
                    </div>

                    {/* Exit Assumptions (when scenario projects realization) */}
                    {exitAssumptions && !isBuyOnly && (
                      <div className="mb-6 rounded-xl bg-black/40 border border-[#D4A853]/10 p-4">
                        <div className="text-xs font-bold text-[#D4A853] uppercase tracking-wider mb-2">Exit Assumptions</div>
                        <div className="grid grid-cols-3 gap-3 text-xs">
                          <div>
                            <div className="text-white/40 mb-1">Exit Trigger</div>
                            <div className="text-white font-medium">{exitAssumptions.trigger}</div>
                          </div>
                          <div>
                            <div className="text-white/40 mb-1">Holding Period</div>
                            <div className="text-white font-medium">{exitAssumptions.holding_period_days} days</div>
                          </div>
                          <div>
                            <div className="text-white/40 mb-1">Tax Regime</div>
                            <div className="text-[#D4A853] font-medium">{exitAssumptions.tax_regime}</div>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Tax Metrics (Pre-Tax vs After-Tax) */}
                    {taxMetrics && (
                      <div className="mb-6">
                        <div className="text-sm font-bold text-white mb-3 flex items-center gap-2">
                          <span className="w-1 h-1 bg-[#D4A853] rounded-full" />
                          Tax Efficiency Metrics
                        </div>
                        <div className="overflow-x-auto rounded-lg border border-white/5">
                          <table className="w-full text-sm">
                            <thead className="bg-white/5">
                              <tr className="border-b border-white/10">
                                <th className="px-3 py-2 text-left text-white/60 font-mono text-xs uppercase">Metric</th>
                                <th className="px-3 py-2 text-center text-white/60 font-mono text-xs uppercase">Pre-Tax</th>
                                <th className="px-3 py-2 text-center text-white/60 font-mono text-xs uppercase">After-Tax</th>
                              </tr>
                            </thead>
                            <tbody>
                              <tr className="border-b border-white/5 last:border-0 hover:bg-white/5 transition-colors">
                                <td className="px-3 py-2 text-white/80">Expected Return</td>
                                <td className="px-3 py-2 text-center text-white font-mono">{fmtPct(taxMetrics.expected_return_pre * 100)}</td>
                                <td className="px-3 py-2 text-center text-[#D4A853] font-mono font-bold">{fmtPct(taxMetrics.expected_return_post * 100)}</td>
                              </tr>
                              <tr className="border-b border-white/5 last:border-0 hover:bg-white/5 transition-colors">
                                <td className="px-3 py-2 text-white/80">Max Drawdown</td>
                                <td className="px-3 py-2 text-center text-white font-mono">{fmtPct(taxMetrics.max_drawdown_pre * 100)}</td>
                                <td className="px-3 py-2 text-center text-red-400 font-mono">{fmtPct(taxMetrics.max_drawdown_post * 100)}</td>
                              </tr>
                              <tr className="border-b border-white/5 last:border-0 hover:bg-white/5 transition-colors">
                                <td className="px-3 py-2 text-white/80">Tail Loss (95%)</td>
                                <td className="px-3 py-2 text-center text-white font-mono">{fmtPct(taxMetrics.tail_loss_pre * 100)}</td>
                                <td className="px-3 py-2 text-center text-red-400 font-mono">{fmtPct(taxMetrics.tail_loss_post * 100)}</td>
                              </tr>
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )}

                    {/* Net Consequence Summary */}
                    <div className="rounded-xl bg-gradient-to-br from-black/60 to-[#D4A853]/10 border border-[#D4A853]/20 p-5 mt-6 relative overflow-hidden">
                      <div className="absolute top-0 right-0 p-4 opacity-10 filter blur-[2px]">
                        <span className="text-6xl">💰</span>
                      </div>
                      <div className="text-sm font-bold text-[#D4A853] uppercase tracking-wider mb-4 border-b border-[#D4A853]/20 pb-2">Net Consequence Summary</div>
                      <div className="overflow-x-auto relative z-10">
                        <table className="w-full text-sm">
                          <tbody>
                            {grossGain > 0 && (
                              <tr className="border-b border-white/5">
                                <td className="px-3 py-2 text-white/80">Gross Gain</td>
                                <td className="px-3 py-2 text-right text-emerald-400 font-mono">{fmtMoney(grossGain, JURISDICTIONS[taxCountry]?.currency)}</td>
                              </tr>
                            )}
                            <tr className="border-b border-white/5">
                              <td className="px-3 py-2 text-white/80">Trade Value</td>
                              <td className="px-3 py-2 text-right text-white font-mono">{fmtMoney(tax.transaction_value_usd || tradeValue, JURISDICTIONS[taxCountry]?.currency)}</td>
                            </tr>
                            <tr className="border-b border-white/5">
                              <td className="px-3 py-2 text-white/80">Execution Taxes</td>
                              <td className="px-3 py-2 text-right text-red-400 font-mono">-{fmtMoney(totalTxnTax, JURISDICTIONS[taxCountry]?.currency)}</td>
                            </tr>
                            <tr className="border-b border-white/5">
                              <td className="px-3 py-2 text-white/80">{isNL ? "Projected Annual Wealth Tax" : "Realization Tax"}</td>
                              <td className="px-3 py-2 text-right text-red-400 font-mono">-{fmtMoney(totalRealTax, JURISDICTIONS[taxCountry]?.currency)}</td>
                            </tr>
                            <tr className="border-t border-white/10 font-bold bg-white/5">
                              <td className="px-3 py-3 text-white uppercase tracking-wider text-xs">{grossGain > 0 ? "Net After-Tax Profit" : "Net After-Tax"}</td>
                              <td className="px-3 py-3 text-right text-white text-lg font-mono">
                                {fmtMoney(grossGain > 0 ? netProfit : (tax.transaction_value_usd || tradeValue) - totalAllTax, JURISDICTIONS[taxCountry]?.currency)}
                              </td>
                            </tr>
                          </tbody>
                        </table>
                        {grossGain > 0 && (
                          <div className="mt-3 text-xs text-white/40 text-right font-mono">
                            Effective Tax Drag: <span className="text-red-400">{effectiveDrag.toFixed(2)}%</span> of gross gain
                          </div>
                        )}
                        {isBuyOnly && totalRealTax > 0 && (
                          <div className="mt-3 text-xs text-white/50 text-center italic px-4">
                            Realization tax above is <strong>projected</strong> — applies only if you exit within the scenario horizon at the simulated projected return.
                          </div>
                        )}
                        {isBuyOnly && totalRealTax === 0 && (
                          <div className="mt-3 text-xs text-white/50 text-center italic px-4">
                            Tax shown above is execution friction only (projected return ≤ 0, so no capital gains tax).
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="mt-6 text-[10px] text-center text-[#D4A853]/30 font-mono uppercase tracking-widest">
                      Powered by GLOQONT Institutional Tax Engine · {tax.jurisdiction || taxCountry} · {(tax.holding_period || taxHoldingPeriod).replace(/_/g, "-")} simulation
                    </div>
                  </EmberCard>
                );
              })()}

              {/* ── 8. Final Verdict Banner ── */}
              {scr && (
                <div className={`rounded-xl border p-4 text-center backdrop-blur-xl transition-all shadow-lg mt-8 ${(scr.composite_score ?? 0) >= 60 ? "border-emerald-500/30 bg-emerald-500/10 shadow-[0_0_20px_rgba(16,185,129,0.1)]" :
                  (scr.composite_score ?? 0) >= 40 ? "border-amber-500/30 bg-amber-500/10 shadow-[0_0_20px_rgba(245,158,11,0.1)]" :
                    "border-red-500/30 bg-red-500/10 shadow-[0_0_20px_rgba(239,68,68,0.1)]"
                  }`}>
                  <div className="flex items-center justify-center gap-3">
                    <span className={`text-lg font-bold uppercase tracking-widest ${(scr.composite_score ?? 0) >= 60 ? "text-emerald-400" :
                      (scr.composite_score ?? 0) >= 40 ? "text-amber-400" :
                        "text-red-400"
                      }`}>
                      {scr.verdict === "dangerous" || scr.verdict === "negative" ? "Avoid Execution" :
                        scr.verdict === "strongly_positive" ? "Strong Buy" :
                          scr.verdict === "moderately_positive" ? "Proceed with Caution" : "Neutral"}
                    </span>
                    <span className="text-white/20 text-xl font-thin">|</span>
                    <span className="text-white/60 text-xs font-mono">Score: <span className="text-white font-bold">{scr.composite_score?.toFixed(0)}</span>/100</span>
                  </div>
                  {scr.summary && <div className="text-xs text-white/40 mt-2 font-mono max-w-xl mx-auto">{scr.summary}</div>}
                </div>
              )}



              {/* ── 10. Visualizations (Charts) ── */}
            </div>
          );
        })()}

      </div>
    </div >
  )
}

