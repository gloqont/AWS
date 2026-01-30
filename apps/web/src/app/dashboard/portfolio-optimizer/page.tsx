"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { apiFetch } from "@/lib/api";
import { useTutorial } from "@/components/tutorial/TutorialContext";
import { PORTFOLIO_OPTIMIZER_TUTORIAL } from "@/components/tutorial/tutorialContent";

type RiskBudget = "LOW" | "MEDIUM" | "HIGH";
type Row = { ticker: string; quantity: string; price?: number };

function toNumber(s: string) {
  const n = Number(s);
  return Number.isFinite(n) ? n : 0;
}

export default function PortfolioOptimizerPage() {
  const [name, setName] = useState("My Portfolio");
  const [riskBudget, setRiskBudget] = useState<RiskBudget>("MEDIUM");
  const [rows, setRows] = useState<Row[]>([
    { ticker: "AAPL", quantity: "10" },
    { ticker: "MSFT", quantity: "5" },
  ]);

  const { startTutorial, isTutorialActive } = useTutorial();
  const hasAutoStarted = useRef(false);

  // Start the portfolio optimizer tutorial when the page loads
  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;

    const maybeStartTutorial = () => {
      if (cancelled || isTutorialActive || hasAutoStarted.current) return;
      hasAutoStarted.current = true;
      timer = setTimeout(() => {
        if (!cancelled) {
          startTutorial(PORTFOLIO_OPTIMIZER_TUTORIAL);
        }
      }, 500); // Small delay to ensure DOM is ready
    };

    const checkServerBoot = async () => {
      try {
        const data = await apiFetch("/api/v1/meta/boot");
        const bootId = data?.boot_id;
        if (bootId) {
          const prevBootId = localStorage.getItem("serverBootId");
          if (prevBootId !== bootId) {
            localStorage.setItem("serverBootId", bootId);
            localStorage.removeItem("hasCompletedTutorial");
            hasAutoStarted.current = false;
          }
        }
      } catch {
        // Ignore boot check errors; tutorial can still start normally.
      } finally {
        maybeStartTutorial();
      }
    };

    checkServerBoot();

    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [startTutorial, isTutorialActive]);

  const [marketPrices, setMarketPrices] = useState<Record<string, number>>({});
  const [suggestions, setSuggestions] = useState<Record<number, any>>({});

  const totalValue = useMemo(() => {
    return rows.reduce((acc, r) => {
      const q = toNumber(r.quantity);
      const p = marketPrices[r.ticker?.toUpperCase()] || 0;
      return acc + q * p;
    }, 0);
  }, [rows, marketPrices]);

  const [status, setStatus] = useState<any>(null);
  const [analysis, setAnalysis] = useState<any>(null);

  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const sum = useMemo(() => {
    const tv = totalValue || 0;
    if (tv <= 0) return 0;
    // compute weights from quantities and prices
    const vals = rows.map((r) => ({ ticker: r.ticker?.toUpperCase(), val: toNumber(r.quantity) * (marketPrices[r.ticker?.toUpperCase()] || 0) }));
    const total = vals.reduce((a, b) => a + b.val, 0);
    return vals.reduce((a, b) => a + (total > 0 ? (b.val / total) * 100 : 0), 0);
  }, [rows, marketPrices]);

  const sumOk = Math.abs(sum - 100) <= 0.5;
  const totalValueOk = totalValue > 0;
  const canRun = sumOk && totalValueOk && !loading;

  function updateRow(i: number, patch: Partial<Row>) {
    setRows((prev) => prev.map((r, idx) => (idx === i ? { ...r, ...patch } : r)));
  }

  async function fetchSuggestion(i: number, q: string) {
    if (!q || q.trim().length < 2) return; // Reduce minimum length to 2 for international tickers
    try {
      const res = await apiFetch(`/api/v1/market/search?q=${encodeURIComponent(q)}`);
      setSuggestions((s) => ({ ...s, [i]: res }));
    } catch (e) {
      setSuggestions((s) => ({ ...s, [i]: null }));
    }
  }

  function addRow() {
    setRows((prev) => [...prev, { ticker: "", quantity: "" }]);
  }

  function removeRow(i: number) {
    setRows((prev) => prev.filter((_, idx) => idx !== i));
  }

  function payload() {
    const positions = rows
      .filter((r) => r.ticker.trim())
      .map((r) => ({ ticker: r.ticker.trim().toUpperCase(), quantity: toNumber(r.quantity) }));

    // compute weights from quantities and marketPrices
    const vals = positions.map((p) => ({ ticker: p.ticker, val: p.quantity * (marketPrices[p.ticker] || 0) }));
    const total = vals.reduce((a, b) => a + b.val, 0) || 1;

    return {
      name,
      risk_budget: riskBudget,
      total_value: total,
      base_currency: "USD",
      positions: vals.map((v) => ({ ticker: v.ticker, weight: (v.val / total) * 100 })),
    };
  }

  async function doValidate() {
    setErr(null);
    setAnalysis(null);
    setLoading(true);
    try {
      const data = await apiFetch("/api/v1/portfolio/validate", {
        method: "POST",
        body: JSON.stringify(payload()),
      });
      setStatus(data);
    } catch (e: any) {
      setErr(e.message);
      setStatus(null);
    } finally {
      setLoading(false);
    }
  }

  async function doSave() {
    setErr(null);
    setAnalysis(null);
    setLoading(true);
    try {
      const data = await apiFetch("/api/v1/portfolio/save", {
        method: "POST",
        body: JSON.stringify(payload()),
      });
      setStatus({ ok: true, sum_weights: 100, warnings: [], errors: [], saved: data.portfolio });
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function doAnalyze() {
    setErr(null);
    setLoading(true);
    try {
      const data = await apiFetch("/api/v1/portfolio/analyze", {
        method: "POST",
        body: JSON.stringify({
          risk_budget: riskBudget,
          positions: payload().positions,
          lookback_days: 365,
          interval: "1d",
        }),
      });
      setAnalysis(data.analysis);
      setStatus(null);
    } catch (e: any) {
      setErr(e.message);
      setAnalysis(null);
    } finally {
      setLoading(false);
    }
  }

  // fetch market prices for tickers in the rows
  async function fetchMarketPrices() {
    const tickers = rows.map((r) => (r.ticker || "").trim()).filter(Boolean).join(",");
    if (!tickers) return;
    try {
      const res = await apiFetch(`/api/v1/market/prices?tickers=${encodeURIComponent(tickers)}&lookback=7&interval=1d`);
      const data = res.data;
      const latestValues: Record<string, number> = {};
      if (data && data.prices_tail && data.prices_tail.values) {
        for (const [k, vals] of Object.entries(data.prices_tail.values)) {
          const arr: any = vals as any;
          latestValues[k.toUpperCase()] = Number(arr[arr.length - 1] || 0);
        }
      }
      setMarketPrices(latestValues);
    } catch (e) {
      // ignore errors
    }
  }

  useEffect(() => {
    fetchMarketPrices();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rows.map((r) => r.ticker).join(",")]);

  return (
    <div className="min-h-screen px-6 py-8">
      <div className="mx-auto max-w-6xl">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="text-sm text-white/60">Advisor Dashboard</div>
            <h1 className="text-3xl font-semibold tracking-tight">Portfolio Optimizer</h1>
            <p className="text-sm text-white/60 mt-1">
              Build a portfolio + validate 100% allocation.
            </p>
          </div>
        </div>


        {/* Top cards */}
        <div className="mt-6 grid grid-cols-1 lg:grid-cols-4 gap-4">
          {/* Name */}
          <div id="portfolio-name-input" className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur p-5">
            <div className="text-sm text-white/60">Portfolio Name</div>
            <input
              className="mt-2 w-full rounded-xl border border-white/10 bg-black/20 px-3 py-2 outline-none focus:border-white/25"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>

          {/* Risk budget */}
          <div id="risk-budget-selector" className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur p-5">
            <div className="text-sm text-white/60">Risk Budget</div>
            <div className="mt-3 flex gap-2">
              {(["LOW", "MEDIUM", "HIGH"] as RiskBudget[]).map((rb) => (
                <button
                  key={rb}
                  onClick={() => setRiskBudget(rb)}
                  className={[
                    "flex-1 rounded-xl px-3 py-2 text-sm border",
                    rb === riskBudget
                      ? "bg-white text-black border-white"
                      : "bg-white/5 text-white border-white/10 hover:bg-white/10",
                  ].join(" ")}
                >
                  {rb}
                </button>
              ))}
            </div>
            <div className="mt-2 text-xs text-white/50">
              V1 enum now. Later: constraints + regime logic + solver objectives.
            </div>
          </div>

          <div id="total-portfolio-value" className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur p-5">
            <div className="text-sm text-white/60">Total Portfolio Value (USD)</div>
            <div className="mt-2 text-2xl font-semibold">${totalValue.toFixed(2)}</div>
            <div className={totalValueOk ? "mt-2 text-xs text-emerald-200" : "mt-2 text-xs text-red-200"}>
              {totalValueOk ? "OK - recalculated from quantities" : "Enter quantities to calculate portfolio value"}
            </div>
          </div>

          {/* Allocation + actions */}
          <div id="total-allocation" className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur p-5">
            <div className="text-sm text-white/60">Total Allocation</div>

            <div className="mt-2 flex items-end justify-between">
              <div className="text-3xl font-semibold tabular-nums">{sum.toFixed(2)}%</div>
              <div className={sumOk ? "text-sm text-emerald-200" : "text-sm text-red-200"}>
                {sumOk ? "Valid" : "Must equal 100%"}
              </div>
            </div>

            <div className="mt-3 flex gap-2">
              <button
                id="validate-button"
                onClick={doValidate}
                disabled={loading || !sumOk || !totalValueOk}
                className="flex-1 rounded-xl bg-white text-black font-medium py-2.5 hover:opacity-90 disabled:opacity-60"
              >
                {loading ? "Working..." : "Validate"}
              </button>
              <button
                onClick={doSave}
                disabled={!canRun}
                className="flex-1 rounded-xl border border-white/10 bg-white/5 py-2.5 font-medium hover:bg-white/10 disabled:opacity-60"
              >
                Save
              </button>
            </div>

            <button
              onClick={doAnalyze}
              disabled={!canRun}
              className="mt-2 w-full rounded-xl border border-white/10 bg-white/5 py-2.5 font-medium hover:bg-white/10 disabled:opacity-60"
            >
              Analyze Risk (Real Data)
            </button>

            {(!totalValueOk || !sumOk) && (
              <div className="mt-3 text-xs text-white/50 leading-relaxed">
                {(!totalValueOk ? "• Enter a total portfolio value.\n" : "")}
                {(!sumOk ? "• Weights must sum to 100%." : "")}
              </div>
            )}
          </div>
        </div>

        {/* Positions table */}
        <div id="positions-table" className="mt-6 rounded-2xl border border-white/10 bg-white/5 backdrop-blur p-5">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-lg font-semibold">Positions</div>
              <div className="text-sm text-white/60">Tickers + weights. Backend enforces 100% total.</div>
            </div>
            <button
              onClick={addRow}
              className="rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm hover:bg-white/10"
            >
              + Add Row
            </button>
          </div>

          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-white/60">
                <tr className="border-b border-white/10">
                  <th className="text-left py-2">Ticker</th>
                  <th className="text-left py-2">Quantity</th>
                  <th className="text-left py-2">Price</th>
                  <th className="text-right py-2">Action</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r, i) => (
                  <tr key={i} className="border-b border-white/5">
                    <td className="py-2 pr-4">
                      <div className="relative">
                        <input
                          className="w-full rounded-xl border border-white/10 bg-black/20 px-3 py-2 outline-none focus:border-white/25"
                          value={r.ticker}
                          onChange={(e) => {
                            updateRow(i, { ticker: e.target.value });
                            if (e.target.value.length >= 2) {
                              fetchSuggestion(i, e.target.value);
                            }
                          }}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' && suggestions[i] && suggestions[i].symbol) {
                              updateRow(i, { ticker: suggestions[i].symbol });
                              e.preventDefault(); // Prevent form submission
                            }
                          }}
                          placeholder="Search ticker (e.g. AAPL, RELIANCE.NS, TCS.NS)"
                        />
                        {suggestions[i] && suggestions[i].symbol && (
                          <div className="absolute z-10 mt-1 w-full rounded-xl border border-white/10 bg-black/90 backdrop-blur p-1 shadow-xl">
                            <div
                              className="cursor-pointer p-3 hover:bg-white/10 rounded-lg transition-colors"
                              onClick={() => updateRow(i, { ticker: suggestions[i].symbol })}
                            >
                              <div className="font-medium">{suggestions[i].shortname || suggestions[i].symbol}</div>
                              <div className="text-xs text-white/60">{suggestions[i].symbol} · {suggestions[i].exchange || "Global"}</div>
                            </div>
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="py-2 pr-4">
                      <input
                        className="w-full rounded-xl border border-white/10 bg-black/20 px-3 py-2 outline-none focus:border-white/25"
                        value={r.quantity}
                        onChange={(e) => updateRow(i, { quantity: e.target.value })}
                        placeholder="10"
                        inputMode="decimal"
                      />
                    </td>
                    <td className="py-2 pr-4">
                      <div className="text-right">{marketPrices[r.ticker?.toUpperCase()] ? `$${marketPrices[r.ticker?.toUpperCase()].toFixed(2)}` : "—"}</div>
                    </td>
                    <td className="py-2 text-right">
                      <button
                        onClick={() => removeRow(i)}
                        className="rounded-xl border border-white/10 bg-white/5 px-3 py-2 hover:bg-white/10"
                      >
                        Remove
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {err && (
            <div className="mt-4 text-sm rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-red-200">
              {err}
            </div>
          )}

          {status && (
            <div className="mt-4 text-sm rounded-xl border border-white/10 bg-black/20 p-3">
              <div className="font-medium">{status.ok ? "Validation passed" : "Validation failed"}</div>
              <div className="text-white/70 mt-1">Sum: {Number(status.sum_weights).toFixed(2)}%</div>
              {status.errors?.length ? (
                <ul className="mt-2 list-disc pl-5 text-red-200">
                  {status.errors.map((x: string, idx: number) => (
                    <li key={idx}>{x}</li>
                  ))}
                </ul>
              ) : null}
              {status.warnings?.length ? (
                <ul className="mt-2 list-disc pl-5 text-amber-200">
                  {status.warnings.map((x: string, idx: number) => (
                    <li key={idx}>{x}</li>
                  ))}
                </ul>
              ) : null}
              {status.saved ? (
                <div className="mt-2 text-white/70">
                  Saved as <span className="text-white">{status.saved.id}</span>
                </div>
              ) : null}
            </div>
          )}
        </div>

        {/* Risk analysis (real data) */}
        {analysis && (
          <div className="mt-6 rounded-2xl border border-white/10 bg-white/5 backdrop-blur p-5">
            <div className="text-lg font-semibold">Risk Analysis</div>
            <div className="text-sm text-white/60">
              Historical data ({analysis.lookback_days}d, {analysis.interval})
            </div>

            <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="rounded-xl border border-white/10 bg-black/20 p-4">
                <div className="text-xs text-white/60">Typical Yearly Swing</div>
                <div className="text-2xl font-semibold mt-1">
                  {(analysis.annualized_vol * 100).toFixed(2)}%
                </div>
              </div>

              <div className="rounded-xl border border-white/10 bg-black/20 p-4">
                <div className="text-xs text-white/60">Max Drawdown</div>
                <div className="text-2xl font-semibold mt-1">
                  {(analysis.max_drawdown * 100).toFixed(2)}%
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
