"use client";

import { useEffect, useMemo, useState, useRef } from "react";
import { apiFetch } from "@/lib/api";
import { useTutorial } from "@/components/tutorial/TutorialContext";
import { PORTFOLIO_OPTIMIZER_TUTORIAL } from "@/components/tutorial/tutorialContent";
import { useSearchParams } from "next/navigation";
import * as XLSX from "xlsx";
import { EXCHANGE_RATES } from "@/lib/constants";
import { EmberCard } from "@/components/dashboard/ui/EmberCard";

import { fmtMoney, APPROX_FX_RATES, COUNTRY_CURRENCY } from "@/lib/currencyUtils";

type RiskBudget = "LOW" | "MEDIUM" | "HIGH";
type Row = { ticker: string; quantity: string; price?: number; currency?: string };

function toNumber(s: string) {
  const n = Number(s);
  return Number.isFinite(n) ? n : 0;
}

export default function PortfolioOptimizerPage() {
  const searchParams = useSearchParams();
  const [name, setName] = useState("My Portfolio");
  const [riskBudget, setRiskBudget] = useState<RiskBudget>("MEDIUM");
  const [rows, setRows] = useState<Row[]>([]);

  // Hydrate state from localStorage AFTER mount to prevent SSR mismatch
  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    setMounted(true);
    const savedName = localStorage.getItem("portfolio_name");
    if (savedName) setName(savedName);

    const savedRisk = localStorage.getItem("portfolio_risk") as RiskBudget;
    if (savedRisk) setRiskBudget(savedRisk);

    try {
      const savedRows = localStorage.getItem("portfolio_rows");
      const savedProfileStr = localStorage.getItem("gloqont_user_profile");

      if (savedRows && savedRows !== "[]") {
        setRows(JSON.parse(savedRows));
      } else if (savedProfileStr) {
        const profile = JSON.parse(savedProfileStr);
        if (profile.country === "IN") {
          setRows([
            { ticker: "RELIANCE.NS", quantity: "10" },
            { ticker: "TCS.NS", quantity: "15" },
            { ticker: "HDFCBANK.NS", quantity: "20" },
          ]);
        } else {
          setRows([
            { ticker: "AAPL", quantity: "10" },
            { ticker: "MSFT", quantity: "5" },
          ]);
        }
      } else {
        setRows([
          { ticker: "AAPL", quantity: "10" },
          { ticker: "MSFT", quantity: "5" },
        ]);
      }
    } catch (e) {
      console.error("Failed to load portfolio from localStorage", e);
      setRows([
        { ticker: "AAPL", quantity: "10" },
        { ticker: "MSFT", quantity: "5" },
      ]);
    }
  }, []);

  // Save state to localStorage whenever it changes, but ONLY AFTER mounted
  useEffect(() => {
    if (mounted && rows.length > 0) {
      localStorage.setItem("portfolio_rows", JSON.stringify(rows));
    }
  }, [rows, mounted]);

  useEffect(() => {
    localStorage.setItem("portfolio_name", name);
  }, [name]);

  useEffect(() => {
    localStorage.setItem("portfolio_risk", riskBudget);
  }, [riskBudget]);

  // Global Profile State
  const [showQuestionnaire, setShowQuestionnaire] = useState(false);
  const [userProfile, setUserProfile] = useState<any>(null);
  const userCurrency = COUNTRY_CURRENCY[userProfile?.country] || "USD";

  // Load User Profile
  useEffect(() => {
    const savedProfile = localStorage.getItem("gloqont_user_profile");
    if (savedProfile) {
      setUserProfile(JSON.parse(savedProfile));
    }
  }, [searchParams]);

  const { startTutorial, isTutorialActive } = useTutorial();

  // Start the portfolio optimizer tutorial when the page loads with tutorial param and no tutorial is active
  useEffect(() => {
    const tutorialParam = searchParams.get("tutorial");
    const hasCompletedTutorial = localStorage.getItem("hasCompletedTutorial_v2");
    const hasShownTutorialThisSession = sessionStorage.getItem("tutorialShownThisSession");

    // Only start if explicitly requested via query param (which OnboardingFlow does)
    // AND onboarding is completed
    const onboardingShown = sessionStorage.getItem("gloqont_onboarding_shown");
    if (
      (tutorialParam === "portfolio" && !isTutorialActive && onboardingShown === "true")
    ) {
      // If no tutorial param is present, it means this is the first page in the sequence
      const timer = setTimeout(() => {
        sessionStorage.setItem("tutorialShownThisSession", "true");
        startTutorial(PORTFOLIO_OPTIMIZER_TUTORIAL);
      }, 500); // Small delay to ensure DOM is ready

      return () => clearTimeout(timer);
    }
  }, [searchParams, startTutorial, isTutorialActive]);

  useEffect(() => {
    // Logic for auto-showing questionnaire removed in favor of global OnboardingFlow
  }, []);

  const [marketPrices, setMarketPrices] = useState<Record<string, number>>({});
  const [suggestions, setSuggestions] = useState<Record<number, any>>({});

  const totalValue = useMemo(() => {
    return rows.reduce((acc, r) => {
      const q = toNumber(r.quantity);
      const p = marketPrices[r.ticker?.toUpperCase()] || 0;
      const currency = r.currency || "USD";
      const rate = EXCHANGE_RATES[currency] || 1.0;
      return acc + (q * p * rate);
    }, 0);
  }, [rows, marketPrices]);

  const [status, setStatus] = useState<any>(null);
  const [analysis, setAnalysis] = useState<any>(null);

  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [importStatus, setImportStatus] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Monte Carlo Paths State for Future Risk Visualization
  const [mcPaths, setMcPaths] = useState<any | null>(null);

  const sum = useMemo(() => {
    const tv = totalValue || 0;
    if (tv <= 0) return 0;
    // compute weights from quantities and prices (converted to USD)
    const vals = rows.map((r) => {
      const currency = r.currency || "USD";
      const rate = EXCHANGE_RATES[currency] || 1.0;
      const val = toNumber(r.quantity) * (marketPrices[r.ticker?.toUpperCase()] || 0) * rate;
      return { ticker: r.ticker?.toUpperCase(), val };
    });
    const total = vals.reduce((a, b) => a + b.val, 0);
    return vals.reduce((a, b) => a + (total > 0 ? (b.val / total) * 100 : 0), 0);
  }, [rows, marketPrices, totalValue]);

  const sumOk = Math.abs(sum - 100) <= 0.5;
  const totalValueOk = totalValue > 0;
  const canRun = sumOk && totalValueOk && !loading;

  function updateRow(i: number, patch: Partial<Row>) {
    setRows((prev) => prev.map((r, idx) => (idx === i ? { ...r, ...patch } : r)));
  }

  function clearSuggestion(i: number) {
    setSuggestions((s) => ({ ...s, [i]: null }));
  }

  async function fetchSuggestion(i: number, q: string) {
    if (!q || q.trim().length < 2) return; // Reduce minimum length to 2 for international tickers
    try {
      const country = userProfile?.country || "US";
      const res = await apiFetch(`/api/v1/market/search?q=${encodeURIComponent(q)}&country=${country}`);
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

    // compute weights from quantities and marketPrices, converting to USD
    const vals = positions.map((p) => {
      const row = rows.find((r) => r.ticker.trim().toUpperCase() === p.ticker);
      const currency = row?.currency || "USD";
      const rate = EXCHANGE_RATES[currency] || 1.0;
      return {
        ticker: p.ticker,
        val: p.quantity * (marketPrices[p.ticker] || 0) * rate
      };
    });
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
    setMcPaths(null); // Reset paths
    try {
      const data = await apiFetch("/api/v1/portfolio/analyze", {
        method: "POST",
        body: JSON.stringify({
          risk_budget: riskBudget,
          positions: payload().positions,
          lookback_days: 365,
          interval: "1d",
          include_paths: true,  // Backend generates all 4 horizons automatically
        }),
      });
      setAnalysis(data.analysis);
      if (data.simulation_paths) {
        setMcPaths(data.simulation_paths);
      }
      setStatus(null);
    } catch (e: any) {
      setErr(e.message);
      setAnalysis(null);
    } finally {
      setLoading(false);
    }
  }

  async function fetchMarketPrices() {
    const tickers = rows
      .map((r) => (r.ticker || "").trim().toUpperCase())
      .filter((t) => t && /^[A-Z0-9][A-Z0-9._-]*$/.test(t));
    const uniqueTickers = Array.from(new Set(tickers));
    if (!uniqueTickers.length) return;
    try {
      const res = await apiFetch(`/api/v1/market/prices?tickers=${encodeURIComponent(uniqueTickers.join(","))}&lookback=2&interval=1d`);
      const data = res.data;
      const latestValues: Record<string, number> = {};
      if (data && data.prices_tail && data.prices_tail.values) {
        for (const [k, vals] of Object.entries(data.prices_tail.values)) {
          const arr: any = vals as any;
          latestValues[k.toUpperCase()] = Number(arr[arr.length - 1] || 0);
        }
      }

      if (Object.keys(latestValues).length) {
        setMarketPrices((prev) => ({ ...prev, ...latestValues }));
      }

      // Update row currencies if detected
      if (data.currencies) {
        setRows((prev) => {
          let hasChanges = false;
          const next = prev.map((r) => {
            const t = (r.ticker || "").trim().toUpperCase();
            const c = data.currencies[t];
            if (t && c && r.currency !== c) {
              hasChanges = true;
              return { ...r, currency: c };
            }
            return r;
          });
          return hasChanges ? next : prev;
        });
      }
    } catch (e) {
      // ignore errors
    }
  }

  useEffect(() => {
    fetchMarketPrices();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rows.map((r) => r.ticker).join(",")]);

  // File Import Handler
  async function handleFileImport(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    setImportStatus("Parsing file...");
    setErr(null);

    try {
      const ext = file.name.split(".").pop()?.toLowerCase();
      let parsedRows: Row[] = [];

      if (ext === "xlsx" || ext === "xls") {
        // Excel file
        const buffer = await file.arrayBuffer();
        const workbook = XLSX.read(buffer, { type: "array" });
        const sheetName = workbook.SheetNames[0];
        const sheet = workbook.Sheets[sheetName];
        const data = XLSX.utils.sheet_to_json<Record<string, any>>(sheet);

        parsedRows = data
          .map((row) => {
            const ticker = String(row.Ticker || row.ticker || row.TICKER || row.Symbol || row.symbol || "").trim();
            const qty = String(row.Quantity || row.quantity || row.QUANTITY || row.Qty || row.qty || row.QTY || "0").trim();
            return { ticker, quantity: qty };
          })
          .filter((r) => r.ticker);
      } else {
        // CSV or TXT file
        const text = await file.text();
        const lines = text.split(/\r?\n/).filter((l) => l.trim());

        if (lines.length < 2) {
          throw new Error("File must have at least a header row and one data row.");
        }

        // Parse header
        const headerLine = lines[0];
        const delimiter = headerLine.includes(",") ? "," : headerLine.includes("\t") ? "\t" : ",";
        const headers = headerLine.split(delimiter).map((h) => h.trim().toLowerCase());

        const tickerIdx = headers.findIndex((h) => ["ticker", "symbol"].includes(h));
        const qtyIdx = headers.findIndex((h) => ["quantity", "qty"].includes(h));

        if (tickerIdx === -1) {
          throw new Error("Could not find 'Ticker' or 'Symbol' column in the file.");
        }
        if (qtyIdx === -1) {
          throw new Error("Could not find 'Quantity' or 'Qty' column in the file.");
        }

        for (let i = 1; i < lines.length; i++) {
          const cols = lines[i].split(delimiter);
          const ticker = (cols[tickerIdx] || "").trim();
          const qty = (cols[qtyIdx] || "0").trim();
          if (ticker) {
            parsedRows.push({ ticker, quantity: qty });
          }
        }
      }

      if (parsedRows.length === 0) {
        throw new Error("No valid rows found in the file.");
      }

      // Merge with existing rows or replace
      setRows(parsedRows);
      setImportStatus(`Imported ${parsedRows.length} positions. Fetching prices...`);

      // Prices will be fetched automatically via the useEffect
      setTimeout(() => setImportStatus(null), 3000);
    } catch (error: any) {
      setErr(`Import failed: ${error.message}`);
      setImportStatus(null);
    }

    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }

  return (
    <div className="min-h-screen px-6 py-8">
      <div className="mx-auto max-w-6xl">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="text-sm text-white/60">GLOQONT</div>
            <h1 className="text-3xl font-semibold tracking-tight">Portfolio</h1>
            <p className="text-sm text-white/60 mt-1">
              Build a portfolio and validate 100% allocation before running analysis.
            </p>
          </div>
          {/* Import Button */}
          <div>
            <input
              type="file"
              ref={fileInputRef}
              accept=".csv,.xlsx,.xls,.txt"
              onChange={handleFileImport}
              className="hidden"
              id="portfolio-import-input"
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              className="rounded-xl border border-[#D4A853]/20 bg-[#D4A853]/10 text-[#D4A853] px-4 py-2.5 text-sm font-medium hover:bg-[#D4A853]/20 transition-all shadow-[0_0_10px_rgba(212,168,83,0.1)]"
            >
              📁 Import Portfolio
            </button>
            {importStatus && (
              <div className="mt-2 text-xs text-emerald-300">{importStatus}</div>
            )}
          </div>
        </div>


        {/* Top cards */}
        <div className="mt-6 grid grid-cols-1 lg:grid-cols-4 gap-4">
          {/* Name */}
          {/* Name */}
          <EmberCard title="Identity" className="h-full">
            <label htmlFor="portfolio-name-input" className="text-sm text-white/60 mb-2 block">Portfolio Name</label>
            <input
              className="w-full rounded-xl border border-[#D4A853]/20 bg-black/40 px-3 py-2 text-[#D4A853] outline-none focus:border-[#D4A853]/50 focus:shadow-[0_0_10px_rgba(212,168,83,0.1)] transition-all placeholder-white/20"
              value={name}
              onChange={(e) => setName(e.target.value)}
              id="portfolio-name-input"
            />
          </EmberCard>

          {/* Risk budget */}
          <EmberCard title="Risk Profile" className="h-full">
            <div className="text-sm text-white/60">Risk Budget</div>
            <div className="mt-3 flex gap-2" id="risk-budget-selector">
              {(["LOW", "MEDIUM", "HIGH"] as RiskBudget[]).map((rb) => (
                <button
                  key={rb}
                  onClick={() => setRiskBudget(rb)}
                  className={[
                    "flex-1 rounded-xl px-2 py-2 text-xs font-semibold border transition-all",
                    rb === riskBudget
                      ? "bg-[#D4A853] text-black border-[#D4A853] shadow-[0_0_10px_rgba(212,168,83,0.3)]"
                      : "bg-black/20 text-white/60 border-[#D4A853]/10 hover:border-[#D4A853]/30 hover:text-[#D4A853]",
                  ].join(" ")}
                >
                  {rb}
                </button>
              ))}
            </div>
            <div className="mt-2 text-[10px] text-[#D4A853]/40 font-mono">
              * Constraints & Solver objectives
            </div>
          </EmberCard>

          <EmberCard title="Valuation" className="h-full">
            <div className="text-sm text-white/60">Total Value ({userCurrency})</div>
            <div className="mt-2 text-2xl font-bold text-white tracking-tight tabular-nums drop-shadow-[0_0_10px_rgba(255,255,255,0.2)]" id="total-portfolio-value">
              {fmtMoney(totalValue, userCurrency)}
            </div>
            <div className={totalValueOk ? "mt-2 text-[10px] text-emerald-400 font-mono" : "mt-2 text-[10px] text-red-400 font-mono"}>
              {totalValueOk ? "● SYNCED" : "○ PAYLOAD EMPTY"}
            </div>
          </EmberCard>

          {/* Allocation + actions */}
          <EmberCard title="Allocation" className="h-full">
            <div className="flex items-end justify-between mb-4">
              <div className="text-3xl font-bold text-[#D4A853] tabular-nums drop-shadow-[0_0_10px_rgba(212,168,83,0.3)]" id="total-allocation">
                {sum.toFixed(2)}%
              </div>
              <div className={sumOk ? "text-xs font-bold text-emerald-400 uppercase tracking-widest mb-1" : "text-xs font-bold text-red-400 uppercase tracking-widest mb-1"}>
                {sumOk ? "OPTIMIZED" : "UNBALANCED"}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2 mb-2">
              <button
                id="validate-button"
                onClick={doValidate}
                disabled={loading || !sumOk || !totalValueOk}
                className="rounded-lg bg-[#D4A853] text-black font-bold py-2 text-xs hover:bg-[#C9963B] disabled:opacity-50 disabled:cursor-not-allowed uppercase tracking-wider shadow-[0_0_15px_rgba(212,168,83,0.2)]"
              >
                {loading ? "..." : "Validate"}
              </button>
              <button
                onClick={doSave}
                disabled={!canRun}
                className="rounded-lg border border-[#D4A853]/30 bg-[#D4A853]/5 text-[#D4A853] py-2 text-xs font-bold hover:bg-[#D4A853]/10 disabled:opacity-50 uppercase tracking-wider"
              >
                Save
              </button>
            </div>

            <button
              onClick={doAnalyze}
              disabled={!canRun}
              className="w-full rounded-lg bg-gradient-to-r from-red-900/40 to-red-800/40 border border-red-500/30 text-red-200 py-2 text-xs font-bold hover:from-red-900/60 hover:to-red-800/60 disabled:opacity-50 uppercase tracking-wider flex items-center justify-center gap-2 shadow-[0_0_15px_rgba(220,38,38,0.2)]"
            >
              Analyze Risk
            </button>

            {(!totalValueOk || !sumOk) && (
              <div className="mt-3 text-[10px] text-red-300/80 font-mono border-t border-red-500/20 pt-2">
                {(!totalValueOk ? "! ZERO VALUE DETECTED\n" : "")}
                {(!sumOk ? "! ALLOCATION != 100%" : "")}
              </div>
            )}
          </EmberCard>
        </div>

        {/* Positions table */}
        {/* Positions table */}
        <EmberCard
          title="Composition"
          subtitle="Tickers + weights. Backend enforces 100% total."
          className="mt-6"
          id="positions-table"
        >
          <div className="absolute top-6 right-6">
            <button
              onClick={addRow}
              className="rounded-lg border border-[#D4A853]/30 bg-[#D4A853]/10 px-3 py-1.5 text-xs font-bold text-[#D4A853] hover:bg-[#D4A853]/20 transition-all uppercase tracking-wider flex items-center gap-2"
            >
              <span>+</span> Add Asset
            </button>
          </div>

          <div className="mt-2 overflow-x-auto overflow-y-visible" style={{ minHeight: 150 + rows.length * 44 }}>
            <table className="w-full text-sm">
              <thead className="text-[#D4A853]/60 font-mono text-xs uppercase tracking-wider">
                <tr className="border-b border-[#D4A853]/20">
                  <th className="text-left py-3 font-normal">Ticker / Name</th>
                  <th className="text-left py-3 font-normal">Quantity</th>
                  <th className="text-left py-3 font-normal">Live Price</th>
                  <th className="text-right py-3 font-normal">Action</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r, i) => (
                  <tr key={i} className="border-b border-white/5 group hover:bg-white/5 transition-colors">
                    <td className="py-2 pr-4">
                      <div className="relative">
                        <input
                          aria-label="Asset Ticker"
                          className="w-full rounded-lg border border-[#D4A853]/20 bg-black/40 px-3 py-2 text-white outline-none focus:border-[#D4A853]/50 focus:shadow-[0_0_10px_rgba(212,168,83,0.1)] placeholder-white/20 font-mono"
                          value={r.ticker}
                          onChange={(e) => {
                            updateRow(i, { ticker: e.target.value });
                            if (e.target.value.length >= 2) {
                              fetchSuggestion(i, e.target.value);
                            }
                          }}
                          onKeyDown={(e) => {
                            if (e.key === "Enter" && suggestions[i] && suggestions[i].symbol) {
                              updateRow(i, { ticker: suggestions[i].symbol });
                              clearSuggestion(i);
                              e.preventDefault(); // Prevent form submission
                            }
                          }}
                          onBlur={() => {
                            setTimeout(() => clearSuggestion(i), 150);
                          }}
                          placeholder="Search ticker..."
                        />
                        {suggestions[i] && suggestions[i].symbol && (
                          <div className="absolute z-10 mt-1 w-full rounded-xl border border-[#D4A853]/20 bg-black/90 backdrop-blur-xl p-1 shadow-2xl">
                            <div
                              className="cursor-pointer p-3 hover:bg-[#D4A853]/20 rounded-lg transition-colors border border-transparent hover:border-[#D4A853]/30"
                              onClick={() => {
                                updateRow(i, {
                                  ticker: suggestions[i].symbol,
                                  currency: suggestions[i].currency || "USD"
                                });
                                clearSuggestion(i);
                              }}
                            >
                              <div className="font-bold text-[#D4A853]">{suggestions[i].shortname || suggestions[i].symbol}</div>
                              <div className="text-xs text-white/60 font-mono">{suggestions[i].symbol} · {suggestions[i].exchange || "Global"} · {suggestions[i].currency || "USD"}</div>
                            </div>
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="py-2 pr-4">
                      <input
                        aria-label="Asset Quantity"
                        className="w-full rounded-lg border border-[#D4A853]/20 bg-black/40 px-3 py-2 text-white outline-none focus:border-[#D4A853]/50 focus:shadow-[0_0_10px_rgba(212,168,83,0.1)] placeholder-white/20 font-mono tabular-nums"
                        value={r.quantity}
                        onChange={(e) => updateRow(i, { quantity: e.target.value })}
                        placeholder="0"
                        inputMode="decimal"
                      />
                    </td>
                    <td className="py-2 pr-4">
                      <div className="text-left font-mono tabular-nums text-white/80">
                        {marketPrices[r.ticker?.toUpperCase()] ? (
                          <div>
                            <div className="text-[#D4A853]">
                              {r.currency && r.currency !== "USD" ? (
                                <span>
                                  {fmtMoney(marketPrices[r.ticker?.toUpperCase()], r.currency, r.currency)}
                                </span>
                              ) : (
                                <span>{fmtMoney(marketPrices[r.ticker?.toUpperCase()], "USD", "USD")}</span>
                              )}
                            </div>
                            {/* Show converted value if user currency is different from asset currency */}
                            {(r.currency || "USD") !== userCurrency && (
                              <div className="text-[10px] text-white/40">
                                ≈ {fmtMoney((marketPrices[r.ticker?.toUpperCase()] * (EXCHANGE_RATES[r.currency || "USD"] || 1)), userCurrency)}
                              </div>
                            )}
                          </div>
                        ) : <span className="text-white/20">—</span>}
                      </div>
                    </td>
                    <td className="py-2 text-right">
                      <button
                        onClick={() => removeRow(i)}
                        className="rounded-lg border border-red-500/20 bg-red-500/5 px-2 py-1.5 text-xs text-red-400 hover:bg-red-500/10 hover:border-red-500/40 transition-all opacity-0 group-hover:opacity-100"
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
        </EmberCard>

        {/* Risk analysis (real data) */}
        {analysis && (
          <div className="mt-6 rounded-2xl border border-white/10 bg-white/5 backdrop-blur p-5">
            <div className="text-lg font-semibold">Risk Analysis</div>
            <div className="text-sm text-white/60">
              Historical data ({analysis.lookback_days}d, {analysis.interval})
            </div>

            <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="rounded-xl border border-white/10 bg-black/20 p-4">
                <div className="text-xs text-white/60">Annualized Volatility</div>
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

        {/* Future Risk Paths Visualization */}
        <div className="mt-6 rounded-2xl border border-white/10 bg-white/5 backdrop-blur p-5">
          <div>
            <div className="text-lg font-semibold">Future Risk Paths</div>
            <div className="text-sm text-white/60">
              Monte Carlo projections of your portfolio across different time horizons
            </div>
          </div>

          {/* Show message if no paths yet */}
          {!mcPaths && !loading && (
            <div className="mt-4 p-4 rounded-xl border border-white/10 bg-black/20 text-center text-white/50 text-sm">
              Click "Analyze Risk (Real Data)" above to generate future risk projections
            </div>
          )}

          {/* Loading state */}
          {loading && (
            <div className="mt-4 p-4 rounded-xl border border-white/10 bg-black/20 text-center text-white/60 text-sm">
              Generating risk paths for all time horizons...
            </div>
          )}

          {/* All 4 Time Horizons Grid */}
          {mcPaths && (
            <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4">
              {(["1m", "3m", "6m", "1y"] as const).map((horizon) => {
                const data = mcPaths[horizon];
                if (!data) return null;

                return (
                  <div key={horizon} className="rounded-xl border border-white/10 bg-black/20 p-4">
                    <div className="text-center mb-3">
                      <div className="text-lg font-semibold text-white">
                        {horizon === "1m" ? "1 Month" : horizon === "3m" ? "3 Months" : horizon === "6m" ? "6 Months" : "1 Year"}
                      </div>
                      <div className="text-xs text-white/40">{data.horizon_days} days</div>
                    </div>

                    {/* Statistics */}
                    <div className="space-y-2">
                      <div className="flex justify-between">
                        <span className="text-xs text-white/40">Best</span>
                        <span className="text-sm font-mono text-green-400">+{data.best_case?.toFixed(1)}%</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-xs text-white/40">Median</span>
                        <span className={`text-sm font-mono ${data.median >= 0 ? "text-white" : "text-red-400"}`}>
                          {data.median >= 0 ? "+" : ""}{data.median?.toFixed(1)}%
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-xs text-white/40">Worst</span>
                        <span className="text-sm font-mono text-red-400">{data.worst_case?.toFixed(1)}%</span>
                      </div>
                    </div>

                    {/* Mini visualization bar */}
                    <div className="mt-3 h-2 bg-black/30 rounded-full overflow-hidden relative">
                      <div
                        className="absolute left-1/2 h-full bg-white/30"
                        style={{ width: '1px' }}
                      />
                      <div
                        className="absolute h-full bg-gradient-to-r from-red-500 to-green-500 opacity-50"
                        style={{
                          left: `${50 + Math.min(data.worst_case, 0)}%`,
                          width: `${Math.abs(data.best_case - data.worst_case)}%`
                        }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {mcPaths && (
            <div className="mt-3 text-xs text-white/40 text-center">
              Based on {mcPaths["1m"]?.n_paths || 30} Monte Carlo simulations per horizon
            </div>
          )}
        </div>
      </div>
    </div>

  );
}
