"use client";

import { useEffect, useState, useMemo, useCallback } from "react";
import { apiFetch } from "@/lib/api";

// Types for Decision Intelligence API
interface DecisionAction {
  symbol: string;
  direction: "buy" | "sell" | "short" | "cover";
  size_percent: number | null;
  size_usd: number | null;
  timing_type: "immediate" | "delay" | "conditional";
  delay_days: number | null;
}

interface DecisionResult {
  ok: boolean;
  decision_id: string;
  decision_type: string;
  parsed_actions: DecisionAction[];
  confidence_score: number;
  parser_warnings: string[];

  baseline_expected_return: number;
  baseline_volatility: number;
  baseline_max_drawdown: number;

  scenario_expected_return: number;
  scenario_volatility: number;
  scenario_max_drawdown: number;

  delta_return: number;
  delta_volatility: number;
  delta_drawdown: number;

  verdict: string;
  composite_score: number;
  summary: string;
  key_factors: string[];
  warnings: string[];

  visualization_data: {
    comparison_chart?: {
      type: string;
      labels: string[];
      baseline: number[];
      scenario: number[];
    };
    score_breakdown?: {
      type: string;
      labels: string[];
      values: number[];
    };
    verdict_gauge?: {
      value: number;
      verdict: string;
    };
    is_fast_approximation?: boolean;
  };
}

interface Portfolio {
  id: string;
  name: string;
  risk_budget: "LOW" | "MEDIUM" | "HIGH";
  total_value: number;
  base_currency: string;
  positions: { ticker: string; weight: number }[];
  created_at: string;
}

import { fmtMoney, COUNTRY_CURRENCY } from "@/lib/currencyUtils";

function fmtPct(n: number, showSign = true) {
  const sign = showSign && n > 0 ? "+" : "";
  return `${sign}${n.toFixed(2)}%`;
}

// Verdict colors
const VERDICT_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  strongly_positive: { bg: "bg-green-500/20", text: "text-green-400", border: "border-green-500/50" },
  moderately_positive: { bg: "bg-green-500/10", text: "text-green-300", border: "border-green-500/30" },
  neutral: { bg: "bg-yellow-500/10", text: "text-yellow-300", border: "border-yellow-500/30" },
  negative: { bg: "bg-orange-500/10", text: "text-orange-300", border: "border-orange-500/30" },
  dangerous: { bg: "bg-red-500/20", text: "text-red-400", border: "border-red-500/50" },
};

// Comparison Bar Chart Component
function ComparisonChart({ data }: { data: DecisionResult["visualization_data"]["comparison_chart"] }) {
  if (!data) return null;

  const maxValue = Math.max(...data.baseline, ...data.scenario);
  const minValue = Math.min(...data.baseline, ...data.scenario);
  const range = Math.max(Math.abs(maxValue), Math.abs(minValue)) || 1;

  return (
    <div className="space-y-4">
      {data.labels.map((label, i) => {
        const baseline = data.baseline[i];
        const scenario = data.scenario[i];
        const delta = scenario - baseline;
        const isImprovement = label === "Max Drawdown" ? delta < 0 : delta > 0;

        return (
          <div key={label} className="space-y-1">
            <div className="flex justify-between text-sm">
              <span className="text-white/60">{label}</span>
              <span className={isImprovement ? "text-green-400" : delta !== 0 ? "text-red-400" : "text-white/60"}>
                {fmtPct(delta)}
              </span>
            </div>
            <div className="flex gap-2">
              {/* Baseline bar */}
              <div className="flex-1">
                <div className="h-3 bg-white/10 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-blue-500/50 rounded-full transition-all duration-500"
                    style={{ width: `${Math.abs(baseline / range) * 50 + 50}%` }}
                  />
                </div>
                <div className="text-xs text-white/40 mt-0.5">Baseline: {fmtPct(baseline, false)}</div>
              </div>
              {/* Scenario bar */}
              <div className="flex-1">
                <div className="h-3 bg-white/10 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${isImprovement ? "bg-green-500/70" : "bg-orange-500/70"}`}
                    style={{ width: `${Math.abs(scenario / range) * 50 + 50}%` }}
                  />
                </div>
                <div className="text-xs text-white/40 mt-0.5">Scenario: {fmtPct(scenario, false)}</div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// Verdict Gauge Component
function VerdictGauge({ data }: { data: DecisionResult["visualization_data"]["verdict_gauge"] }) {
  if (!data) return null;

  const colors = VERDICT_COLORS[data.verdict] || VERDICT_COLORS.neutral;
  const percentage = data.value;

  return (
    <div className={`rounded-xl border ${colors.border} ${colors.bg} p-6`}>
      <div className="text-center">
        <div className={`text-3xl font-bold ${colors.text}`}>
          {data.verdict.replace(/_/g, " ").toUpperCase()}
        </div>
        <div className="mt-2">
          <div className="w-full h-4 bg-black/30 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-1000 ease-out ${percentage >= 70 ? "bg-green-500" :
                percentage >= 55 ? "bg-green-400" :
                  percentage >= 45 ? "bg-yellow-400" :
                    percentage >= 30 ? "bg-orange-400" :
                      "bg-red-500"
                }`}
              style={{ width: `${percentage}%` }}
            />
          </div>
          <div className="mt-1 text-sm text-white/60">{percentage.toFixed(1)} / 100</div>
        </div>
      </div>
    </div>
  );
}

// Score Radar Component (simplified as bars for now)
function ScoreBreakdown({ data }: { data: DecisionResult["visualization_data"]["score_breakdown"] }) {
  if (!data) return null;

  return (
    <div className="space-y-2">
      {data.labels.map((label, i) => {
        const value = data.values[i];
        const isGood = value >= 50;

        return (
          <div key={label} className="flex items-center gap-3">
            <div className="w-20 text-xs text-white/60">{label}</div>
            <div className="flex-1 h-2 bg-white/10 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-500 ${isGood ? "bg-green-500/70" : "bg-orange-500/70"}`}
                style={{ width: `${value}%` }}
              />
            </div>
            <div className="w-10 text-xs text-right text-white/40">{value.toFixed(0)}</div>
          </div>
        );
      })}
    </div>
  );
}

// Parsed Actions Display
function ParsedActions({ actions, currency = "USD" }: { actions: DecisionAction[]; currency?: string }) {
  return (
    <div className="space-y-2">
      {actions.map((action, i) => (
        <div key={i} className="flex items-center gap-2 text-sm">
          <span className={`px-2 py-0.5 rounded text-xs font-medium uppercase ${action.direction === "buy" ? "bg-green-500/20 text-green-400" :
            action.direction === "sell" ? "bg-red-500/20 text-red-400" :
              action.direction === "short" ? "bg-purple-500/20 text-purple-400" :
                "bg-blue-500/20 text-blue-400"
            }`}>
            {action.direction}
          </span>
          <span className="font-mono text-white">{action.symbol}</span>
          {action.size_percent && <span className="text-white/60">{action.size_percent}%</span>}
          {action.size_usd && <span className="text-white/60">{fmtMoney(action.size_usd, currency)}</span>}
          {action.delay_days && action.delay_days > 0 && (
            <span className="text-amber-400 text-xs">(T+{action.delay_days}d)</span>
          )}
        </div>
      ))}
    </div>
  );
}

export default function DecisionIntelligencePage() {
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [decisionText, setDecisionText] = useState("");
  const [horizonDays, setHorizonDays] = useState(30);
  const [userCurrency, setUserCurrency] = useState("USD");

  const [fastResult, setFastResult] = useState<DecisionResult | null>(null);
  const [fullResult, setFullResult] = useState<DecisionResult | null>(null);

  const [loadingFast, setLoadingFast] = useState(false);
  const [loadingFull, setLoadingFull] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [showFullSimulation, setShowFullSimulation] = useState(false);

  // Load portfolio and user profile on mount
  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const res = await apiFetch("/api/v1/portfolio/current", { method: "GET" });
        if (!mounted) return;
        setPortfolio(res.portfolio ?? null);
      } catch (e: any) {
        if (!mounted) return;
        setError(e.message || "Failed to load portfolio.");
      }
    })();

    // Load user currency preference
    try {
      const savedProfile = localStorage.getItem("gloqont_user_profile");
      if (savedProfile) {
        const p = JSON.parse(savedProfile);
        if (p.country && COUNTRY_CURRENCY[p.country]) {
          setUserCurrency(COUNTRY_CURRENCY[p.country]);
        }
      }
    } catch (e) {
      console.error("Failed to load user profile", e);
    }

    return () => { mounted = false; };
  }, []);

  const positionsSummary = useMemo(() => {
    if (!portfolio?.positions?.length) return "";
    return portfolio.positions
      .map((p) => `${p.ticker} ${(p.weight * 100).toFixed(0)}%`)
      .join(" • ");
  }, [portfolio]);

  // Run fast evaluation
  const runFastEvaluation = useCallback(async () => {
    if (!decisionText.trim()) {
      setError("Enter a decision first.");
      return;
    }

    setError(null);
    setFastResult(null);
    setFullResult(null);
    setLoadingFast(true);

    try {
      const data = await apiFetch("/api/v1/decision/evaluate/fast", {
        method: "POST",
        body: JSON.stringify({
          decision_text: decisionText.trim(),
          horizon_days: horizonDays,
          n_paths: 100, // Ignored for fast
        }),
      });
      setFastResult(data);
    } catch (e: any) {
      setError(e.message || "Failed to evaluate decision.");
    } finally {
      setLoadingFast(false);
    }
  }, [decisionText, horizonDays]);

  // Run full Monte Carlo simulation
  const runFullSimulation = useCallback(async () => {
    setLoadingFull(true);

    try {
      const data = await apiFetch("/api/v1/decision/evaluate", {
        method: "POST",
        body: JSON.stringify({
          decision_text: decisionText.trim(),
          horizon_days: horizonDays,
          n_paths: 100,
        }),
      });
      setFullResult(data);
      setShowFullSimulation(true);
    } catch (e: any) {
      setError(e.message || "Failed to run full simulation.");
    } finally {
      setLoadingFull(false);
    }
  }, [decisionText, horizonDays]);

  // Current result to display
  const currentResult = showFullSimulation && fullResult ? fullResult : fastResult;
  const isFastMode = !showFullSimulation || !fullResult;

  return (
    <div className="min-h-screen px-6 py-8">
      <div className="mx-auto max-w-6xl">
        {/* Header */}
        <div>
          <div className="text-sm text-white/60">GLOQONT</div>
          <h1 className="text-3xl font-semibold tracking-tight">Decision Intelligence</h1>
          <p className="text-sm text-white/60 mt-1">
            AI-powered counterfactual analysis of investment decisions
          </p>
        </div>

        {/* Portfolio Summary */}
        <div className="mt-6 rounded-2xl border border-white/10 bg-white/5 backdrop-blur p-6">
          <div className="text-sm text-white/60">Current Portfolio</div>
          {portfolio ? (
            <div className="mt-2">
              <div className="flex flex-wrap items-end justify-between gap-3">
                <div>
                  <div className="text-xl font-semibold">{portfolio.name}</div>
                  <div className="text-sm text-white/60 mt-1">
                    Risk: <span className="text-white">{portfolio.risk_budget}</span> • Value:{" "}
                    <span className="text-white">{fmtMoney(portfolio.total_value, userCurrency)}</span>
                  </div>
                </div>
              </div>
              {positionsSummary && (
                <div className="mt-3 rounded-xl border border-white/10 bg-black/20 p-3 text-sm text-white/80">
                  {positionsSummary}
                </div>
              )}
            </div>
          ) : (
            <div className="mt-3 text-sm text-red-200">
              No saved portfolio found. Go to <span className="text-white">Portfolio Optimizer</span> first.
            </div>
          )}
        </div>

        {/* Decision Input */}
        <div className="mt-6 grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2 rounded-2xl border border-white/10 bg-white/5 backdrop-blur p-6">
            <div className="text-sm text-white/60">Your Decision</div>
            <textarea
              className="mt-2 w-full min-h-[120px] rounded-xl border border-white/10 bg-black/20 px-3 py-2 outline-none focus:border-white/25 resize-none"
              value={decisionText}
              onChange={(e) => setDecisionText(e.target.value)}
              placeholder='Examples: "Short Apple 4% after 3 days" or "Buy NVDA 10%"'
            />
            <div className="mt-2 text-xs text-white/50">
              Supports natural language with timing: "after 3 days", "in 2 weeks"
            </div>
          </div>

          <div className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur p-6">
            <div className="text-sm text-white/60">Simulation Horizon</div>
            <div className="mt-2 flex items-center gap-2">
              <input
                type="range"
                min="7"
                max="90"
                value={horizonDays}
                onChange={(e) => setHorizonDays(Number(e.target.value))}
                className="flex-1"
              />
              <span className="w-16 text-right font-mono">{horizonDays} days</span>
            </div>

            <button
              onClick={runFastEvaluation}
              disabled={loadingFast || !portfolio}
              className="mt-4 w-full rounded-xl bg-white text-black font-medium px-4 py-2.5 hover:opacity-90 disabled:opacity-60"
            >
              {loadingFast ? "Analyzing..." : "Evaluate Decision"}
            </button>

            <div className="mt-2 text-xs text-center text-white/50">
              Instant analysis (~30ms)
            </div>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="mt-6 text-sm rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-red-200">
            {error}
          </div>
        )}

        {/* Results */}
        {currentResult && (
          <div className="mt-6 space-y-4">
            {/* Mode Indicator */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {isFastMode ? (
                  <>
                    <div className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
                    <span className="text-sm text-amber-400">Fast Approximation</span>
                  </>
                ) : (
                  <>
                    <div className="w-2 h-2 rounded-full bg-green-400" />
                    <span className="text-sm text-green-400">Full Monte Carlo Simulation</span>
                  </>
                )}
              </div>

              {isFastMode && !loadingFull && (
                <button
                  onClick={runFullSimulation}
                  className="text-sm text-blue-400 hover:text-blue-300"
                >
                  Run Full Simulation →
                </button>
              )}
              {loadingFull && (
                <span className="text-sm text-white/60">Running deep simulation...</span>
              )}
            </div>

            {/* Verdict Card */}
            {currentResult.visualization_data?.verdict_gauge && (
              <VerdictGauge data={currentResult.visualization_data.verdict_gauge} />
            )}

            {/* Summary */}
            <div className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur p-6">
              <div className="text-lg font-medium">{currentResult.summary}</div>

              {currentResult.key_factors.length > 0 && (
                <div className="mt-4">
                  <div className="text-sm text-white/60 mb-2">Key Factors</div>
                  <ul className="space-y-1">
                    {currentResult.key_factors.map((factor, i) => (
                      <li key={i} className="text-sm text-white/80 flex items-start gap-2">
                        <span className="text-green-400">•</span> {factor}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {currentResult.warnings.length > 0 && (
                <div className="mt-4">
                  <div className="text-sm text-amber-400/80 mb-2">⚠️ Warnings</div>
                  <ul className="space-y-1">
                    {currentResult.warnings.map((warning, i) => (
                      <li key={i} className="text-sm text-amber-300/80">{warning}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {/* Parsed Actions */}
            <div className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur p-6">
              <div className="text-sm text-white/60 mb-3">Parsed Actions</div>
              <ParsedActions actions={currentResult.parsed_actions} currency={userCurrency} />
              <div className="mt-3 text-xs text-white/40">
                Decision Type: {currentResult.decision_type} •
                Parser Confidence: {(currentResult.confidence_score * 100).toFixed(0)}%
              </div>
            </div>

            {/* Comparison Chart */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur p-6">
                <div className="text-sm text-white/60 mb-4">Baseline vs. Scenario Comparison</div>
                {currentResult.visualization_data?.comparison_chart && (
                  <ComparisonChart data={currentResult.visualization_data.comparison_chart} />
                )}
              </div>

              <div className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur p-6">
                <div className="text-sm text-white/60 mb-4">Score Breakdown</div>
                {currentResult.visualization_data?.score_breakdown && (
                  <ScoreBreakdown data={currentResult.visualization_data.score_breakdown} />
                )}
              </div>
            </div>

            {/* Raw Metrics */}
            <div className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur p-6">
              <div className="text-sm text-white/60 mb-4">Detailed Metrics</div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <div className="text-xs text-white/40">Δ Return</div>
                  <div className={`text-xl font-mono ${currentResult.delta_return >= 0 ? "text-green-400" : "text-red-400"}`}>
                    {fmtPct(currentResult.delta_return)}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-white/40">Δ Volatility</div>
                  <div className={`text-xl font-mono ${currentResult.delta_volatility <= 0 ? "text-green-400" : "text-orange-400"}`}>
                    {fmtPct(currentResult.delta_volatility)}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-white/40">Δ Max Drawdown</div>
                  <div className={`text-xl font-mono ${currentResult.delta_drawdown <= 0 ? "text-green-400" : "text-red-400"}`}>
                    {fmtPct(currentResult.delta_drawdown)}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-white/40">Composite Score</div>
                  <div className="text-xl font-mono text-white">
                    {currentResult.composite_score.toFixed(1)}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
