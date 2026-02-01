"use client";

import { useEffect, useMemo, useState } from "react";
import { apiFetch } from "@/lib/api";
import { DecisionVisualizations } from "@/components/DecisionVisualizations";

type Portfolio = {
  id: string;
  name: string;
  risk_budget: "LOW" | "MEDIUM" | "HIGH";
  total_value: number;
  base_currency: string;
  positions: { ticker: string; weight: number }[]; // weights are decimals (0.5)
  created_at: string;
};

type DecisionResult = {
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
    return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(n);
  } catch {
    return `$${n.toFixed(2)}`;
  }
}

function fmtPct(n: number) {
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(2)}%`;
}

export default function ScenarioSimulationPage() {
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [decisionText, setDecisionText] = useState("");
  const [taxCountry, setTaxCountry] = useState("United States");
  const [decisionType, setDecisionType] = useState<"trade" | "rebalance">("rebalance");
  const [marketContext, setMarketContext] = useState<any | null>(null);

  const [result, setResult] = useState<any | null>(null);
  const [showVisualizeRisk, setShowVisualizeRisk] = useState<boolean>(false);
  const [showOnlyVisualizations, setShowOnlyVisualizations] = useState<boolean>(false);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  // Helper function to extract tickers from decision text
  function extractTickersFromText(text: string): string[] {
    // Common ticker patterns to look for (2-5 characters, uppercase, with possible international suffixes)
    const tickerPattern = /\b([A-Z]{1,5}(?:\.[A-Z]{1,3})?)\b/g;
    const matches = text.match(tickerPattern) || [];

    // Also look for common variations like "apple", "Apple", "AAPL", etc.
    const commonNames = [
      { name: "apple", ticker: "AAPL" },
      { name: "microsoft", ticker: "MSFT" },
      { name: "google", ticker: "GOOGL" },
      { name: "alphabet", ticker: "GOOGL" },
      { name: "amazon", ticker: "AMZN" },
      { name: "nvidia", ticker: "NVDA" },
      { name: "meta", ticker: "META" },
      { name: "facebook", ticker: "META" },
      { name: "tesla", ticker: "TSLA" },
      { name: "netflix", ticker: "NFLX" },
      { name: "amd", ticker: "AMD" },
      { name: "intel", ticker: "INTC" },
      { name: "ibm", ticker: "IBM" },
      { name: "oracle", ticker: "ORCL" },
      { name: "salesforce", ticker: "CRM" },
      { name: "adobe", ticker: "ADBE" },
      { name: "paypal", ticker: "PYPL" },
      { name: "shopify", ticker: "SHOP" },
      { name: "spotify", ticker: "SPOT" },
      { name: "uber", ticker: "UBER" },
      { name: "lyft", ticker: "LYFT" },
      { name: "snap", ticker: "SNAP" },
      { name: "twitter", ticker: "TWTR" },
      { name: "x", ticker: "X" },
      { name: "coinbase", ticker: "COIN" },
      { name: "robinhood", ticker: "HOOD" },
      { name: "square", ticker: "SQ" },
      { name: "block", ticker: "SQ" },
      { name: "zoom", ticker: "ZM" },
      { name: "docu", ticker: "DOCU" },
      { name: "okta", ticker: "OKTA" },
      { name: "snowflake", ticker: "SNOW" },
      { name: "datadog", ticker: "DDOG" },
      { name: "crowdstrike", ticker: "CRWD" },
      { name: "palantir", ticker: "PLTR" },
      { name: "upstart", ticker: "UPST" },
      { name: "chegg", ticker: "CHGG" },
      { name: "zoominfo", ticker: "ZI" },
      // Indian companies
      { name: "reliance", ticker: "RELIANCE.NS" },
      { name: "tcs", ticker: "TCS.NS" },
      { name: "infosys", ticker: "INFY.NS" },
      { name: "hdfc bank", ticker: "HDFCBANK.NS" },
      { name: "icici bank", ticker: "ICICIBANK.NS" },
      { name: "state bank of india", ticker: "SBIN.NS" },
      { name: "bharti airtel", ticker: "BHARTIARTL.NS" },
      { name: "hindustan unilever", ticker: "HINDUNILVR.NS" },
      { name: "itc", ticker: "ITC.NS" },
      { name: "kotak mahindra", ticker: "KOTAKBANK.NS" },
      { name: "larsen and toubro", ticker: "LT.NS" },
      { name: "asian paints", ticker: "ASIANPAINT.NS" },
      { name: "axis bank", ticker: "AXISBANK.NS" },
      { name: "maruti suzuki", ticker: "MARUTI.NS" },
      { name: "sun pharmaceutical", ticker: "SUNPHARMA.NS" },
      { name: "titan", ticker: "TITAN.NS" },
      { name: "ultratech cement", ticker: "ULTRACEMCO.NS" },
      { name: "wipro", ticker: "WIPRO.NS" },
      { name: "nestle india", ticker: "NESTLEIND.NS" },
      { name: "hcl technologies", ticker: "HCLTECH.NS" },
      { name: "tata steel", ticker: "TATASTEEL.NS" },
      { name: "tech mahindra", ticker: "TECHM.NS" },
      { name: "bajaj finance", ticker: "BAJFINANCE.NS" },
      { name: "mahindra and mahindra", ticker: "M&M.NS" },
      { name: "oil and natural gas", ticker: "ONGC.NS" },
      { name: "power grid", ticker: "POWERGRID.NS" },
      { name: "coal india", ticker: "COALINDIA.NS" },
      { name: "grasim", ticker: "GRASIM.NS" },
      { name: "vedanta", ticker: "VEDL.NS" },
      { name: "jsw steel", ticker: "JSWSTEEL.NS" },
      { name: "apollo hospitals", ticker: "APOLLOHOSP.NS" },
      { name: "upl", ticker: "UPL.NS" },
      { name: "bharat petroleum", ticker: "BPCL.NS" },
      { name: "divi's laboratories", ticker: "DIVISLAB.NS" },
      { name: "britannia", ticker: "BRITANNIA.NS" },
      { name: "shree cement", ticker: "SHREECEM.NS" },
      { name: "dr reddy's", ticker: "DRREDDY.NS" },
      { name: "tata motors", ticker: "TATAMOTORS.NS" },
      { name: "bajaj finserv", ticker: "BAJAJFINSV.NS" },
      { name: "eicher motors", ticker: "EICHERMOT.NS" },
      { name: "indusind bank", ticker: "INDUSINDBK.NS" },
      { name: "sbi life", ticker: "SBILIFE.NS" },
      { name: "hdfc life", ticker: "HDFCLIFE.NS" },
      { name: "cipla", ticker: "CIPLA.NS" },
      { name: "hero motocorp", ticker: "HEROMOTOCO.NS" },
      { name: "indian oil", ticker: "IOC.NS" },
      { name: "adani ports", ticker: "ADANIPORTS.NS" },
      { name: "godrej consumer", ticker: "GODREJCP.NS" },
      { name: "berger paints", ticker: "BERGEPAINT.NS" },
      { name: "bajaj auto", ticker: "BAJAJ-AUTO.NS" },
      // Crypto
      { name: "bitcoin", ticker: "BTC" },
      { name: "ethereum", ticker: "ETH" },
      { name: "binance coin", ticker: "BNB" },
      { name: "cardano", ticker: "ADA" },
      { name: "ripple", ticker: "XRP" },
      { name: "dogecoin", ticker: "DOGE" },
      { name: "polkadot", ticker: "DOT" },
      { name: "avalanche", ticker: "AVAX" },
      { name: "solana", ticker: "SOL" },
      { name: "polygon", ticker: "MATIC" },
      { name: "chainlink", ticker: "LINK" },
      { name: "litecoin", ticker: "LTC" },
      { name: "uniswap", ticker: "UNI" },
      { name: "cosmos", ticker: "ATOM" },
      { name: "monero", ticker: "XMR" },
    ];

    // Additional ticker variations with common suffixes/prefixes
    const tickerVariations: Record<string, string> = {
      "nvda": "NVDA",
      "nvd": "NVDA",
      "nvidia": "NVDA",
      "aapl": "AAPL",
      "appl": "AAPL",
      "apple": "AAPL",
      "msft": "MSFT",
      "microsoft": "MSFT",
      "goog": "GOOGL",
      "googl": "GOOGL",
      "google": "GOOGL",
      "amzn": "AMZN",
      "amazon": "AMZN",
      "meta": "META",
      "fb": "META",
      "tsla": "TSLA",
      "tesla": "TSLA",
      "nflx": "NFLX",
      "netflix": "NFLX",
      "amd": "AMD",
      "advanced micro devices": "AMD",
      "intc": "INTC",
      "intel": "INTC",
      "ibm": "IBM",
      "international business machines": "IBM",
      "crm": "CRM",
      "salesforce": "CRM",
      "adbe": "ADBE",
      "adobe": "ADBE",
      "pypl": "PYPL",
      "paypal": "PYPL",
      "shop": "SHOP",
      "shopify": "SHOP",
      "spot": "SPOT",
      "spotify": "SPOT",
      "uber": "UBER",
      "lyft": "LYFT",
      "snap": "SNAP",
      "twtr": "TWTR",
      "x": "X",
      "twitter": "X",
      "coin": "COIN",
      "coinbase": "COIN",
      "hood": "HOOD",
      "robinhood": "HOOD",
      "sq": "SQ",
      "square": "SQ",
      "zm": "ZM",
      "zoom": "ZM",
      "docu": "DOCU",
      "document": "DOCU",
      "okta": "OKTA",
      "snow": "SNOW",
      "snowflake": "SNOW",
      "ddog": "DDOG",
      "datadog": "DDOG",
      "crwd": "CRWD",
      "crowdstrike": "CRWD",
      "pltr": "PLTR",
      "palantir": "PLTR",
      "upst": "UPST",
      "upstart": "UPST",
      "chgg": "CHGG",
      "chegg": "CHGG",
      "zi": "ZI",
      "zoominfo": "ZI",
      // Indian variations
      "reliance": "RELIANCE.NS",
      "tcs": "TCS.NS",
      "infy": "INFY.NS",
      "hdfcbank": "HDFCBANK.NS",
      "icicibank": "ICICIBANK.NS",
      "sbin": "SBIN.NS",
      "bhartiartl": "BHARTIARTL.NS",
      "hindunilvr": "HINDUNILVR.NS",
      "itc": "ITC.NS",
      "kotakbank": "KOTAKBANK.NS",
      "lt": "LT.NS",
      "asianpaint": "ASIANPAINT.NS",
      "axisbank": "AXISBANK.NS",
      "maruti": "MARUTI.NS",
      "sunpharma": "SUNPHARMA.NS",
      "titan": "TITAN.NS",
      "ultracemco": "ULTRACEMCO.NS",
      "wipro": "WIPRO.NS",
      "nestleind": "NESTLEIND.NS",
      "hcltech": "HCLTECH.NS",
      "tatsteel": "TATASTEEL.NS",
      "techm": "TECHM.NS",
      "bajajfinance": "BAJFINANCE.NS",
      "m&m": "M&M.NS",
      "ongc": "ONGC.NS",
      "powergrid": "POWERGRID.NS",
      "coalindia": "COALINDIA.NS",
      "grasim": "GRASIM.NS",
      "vedl": "VEDL.NS",
      "jswsteel": "JSWSTEEL.NS",
      "apollohosp": "APOLLOHOSP.NS",
      "upl": "UPL.NS",
      "bpcl": "BPCL.NS",
      "divislab": "DIVISLAB.NS",
      "britannia": "BRITANNIA.NS",
      "shreecem": "SHREECEM.NS",
      "drreddy": "DRREDDY.NS",
      "tatamotors": "TATAMOTORS.NS",
      "bajajfinsv": "BAJAJFINSV.NS",
      "eichermot": "EICHERMOT.NS",
      "indusindbk": "INDUSINDBK.NS",
      "sbilife": "SBILIFE.NS",
      "hdfclife": "HDFCLIFE.NS",
      "cipla": "CIPLA.NS",
      "heromotoco": "HEROMOTOCO.NS",
      "ioc": "IOC.NS",
      "adaniports": "ADANIPORTS.NS",
      "godrejcp": "GODREJCP.NS",
      "bergepaint": "BERGEPAINT.NS",
      "bajajauto": "BAJAJ-AUTO.NS",
      // Crypto variations
      "bitcoin": "BTC",
      "ethereum": "ETH",
      "bnb": "BNB",
      "ada": "ADA",
      "xrp": "XRP",
      "doge": "DOGE",
      "dot": "DOT",
      "avax": "AVAX",
      "sol": "SOL",
      "matic": "MATIC",
      "link": "LINK",
      "ltc": "LTC",
      "uni": "UNI",
      "atom": "ATOM",
      "xmr": "XMR",
    };

    const extractedTickers = new Set<string>();

    // Add matches from the pattern
    matches.forEach(match => {
      extractedTickers.add(match.toUpperCase());
    });

    // Check for common company names in the text
    const lowerText = text.toLowerCase();

    // Check for direct name matches
    commonNames.forEach(item => {
      if (lowerText.includes(item.name)) {
        extractedTickers.add(item.ticker);
      }
    });

    // Check for variations
    Object.entries(tickerVariations).forEach(([variation, ticker]) => {
      if (lowerText.includes(variation)) {
        extractedTickers.add(ticker);
      }
    });

    // Look for patterns like "buy [ticker]", "sell [ticker]", etc.
    const buySellPattern = /(buy|sell|purchase|invest in|add to|remove from|trim|increase|decrease)\s+([A-Z]{1,5}(?:\.[A-Z]{1,3})?)/gi;
    let buySellMatch;
    while ((buySellMatch = buySellPattern.exec(lowerText)) !== null) {
      const ticker = buySellMatch[2].toUpperCase();
      extractedTickers.add(ticker);
    }

    // Look for patterns like "[ticker] stock", "[ticker] shares", etc.
    const stockPattern = /\b([A-Z]{1,5}(?:\.[A-Z]{1,3})?)\s+(stock|shares|position)/gi;
    let stockMatch;
    while ((stockMatch = stockPattern.exec(lowerText)) !== null) {
      const ticker = stockMatch[1].toUpperCase();
      extractedTickers.add(ticker);
    }

    return Array.from(extractedTickers);
  }

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

  async function runScenario() {
    setErr(null);
    setResult(null);

    if (!portfolio) {
      setErr("No portfolio found. Go to Portfolio Optimizer and click Save first.");
      return;
    }

    const text = decisionText.trim();
    if (text.length < 3) {
      setErr("Type a decision first (at least a few words).");
      return;
    }

    // Extract tickers from the decision text
    const decisionTickers = extractTickersFromText(text);

    // Check if the decision type matches the portfolio contents
    if (decisionType === "rebalance") {
      // For portfolio rebalancing, all mentioned tickers should be in the portfolio
      const portfolioTickers = portfolio.positions.map(p => p.ticker.toUpperCase());
      const missingTickers = decisionTickers.filter(ticker => !portfolioTickers.includes(ticker.toUpperCase()));

      if (missingTickers.length > 0) {
        setErr(`Portfolio rebalancing: The following stocks are not in your portfolio: ${missingTickers.join(', ')}. Please select 'Trade Decision' for stocks not in your portfolio, or adjust your decision to only include stocks from your portfolio (${portfolioTickers.join(', ')}).`);
        return;
      }
    } else if (decisionType === "trade") {
      // For trade decision, at least some mentioned tickers should NOT be in the portfolio
      const portfolioTickers = portfolio.positions.map(p => p.ticker.toUpperCase());
      const existingTickers = decisionTickers.filter(ticker => portfolioTickers.includes(ticker.toUpperCase()));

      if (existingTickers.length > 0) {
        setErr(`Trade decision: The following stocks are already in your portfolio: ${existingTickers.join(', ')}. Please select 'Portfolio Rebalancing' for stocks in your portfolio, or adjust your decision to only include stocks not in your portfolio.`);
        return;
      }
    }

    setLoading(true);
    try {
      const data = await apiFetch("/api/v1/scenario/run", {
        method: "POST",
        body: JSON.stringify({
          decision_text: text,
          tax_country: taxCountry,
          decision_type: decisionType  // Send decision type to backend
        }),
      });
      setResult(data);
      setShowVisualizeRisk(true); // Show the visualize risk button after successful scenario run
      setMarketContext((mc: any) => ({ ...(mc || {}), prices_tail: data.market_context?.prices_tail }));
    } catch (e: any) {
      setErr(e.message || "Failed to run scenario.");
    } finally {
      setLoading(false);
    }
}


// Validate strict output contract
function isValidOutputContract(result: any): boolean {
  // A. DECISION SUMMARY (REQUIRED)
  if (!result.decision_summary) return false;
  if (!result.decision_summary.asset?.symbol) return false;
  if (typeof result.decision_summary.allocation_change_pct !== 'number') return false;
  if (typeof result.decision_summary.previous_weight_pct !== 'number') return false; // Explicitly state previous weight
  if (!result.decision_summary.decision_type) return false; // decision_type must match portfolio state

  // B. PRIMARY EXPOSURE CHANGE (REQUIRED)
  if (!result.primary_exposure_impact) return false;
  if (!result.primary_exposure_impact.asset_symbol) return false; // primary_asset == decision asset
  if (typeof result.primary_exposure_impact.weight_before_pct !== 'number') return false;
  if (typeof result.primary_exposure_impact.weight_after_pct !== 'number') return false;
  if (typeof result.primary_exposure_impact.absolute_change_pct !== 'number') return false;

  // Validate: weight_before + allocation_change == weight_after (±0.01)
  const expectedAfter = result.primary_exposure_impact.weight_before_pct + result.primary_exposure_impact.absolute_change_pct;
  if (Math.abs(result.primary_exposure_impact.weight_after_pct - expectedAfter) > 0.01) return false;

  // C. RISK IMPACT (REQUIRED)
  if (!result.risk_impact) return false;
  if (typeof result.risk_impact.horizon_days !== 'number') return false;
  if (typeof result.risk_impact.downside_pct !== 'number') return false;
  if (typeof result.risk_impact.expected_pct !== 'number') return false;
  if (typeof result.risk_impact.upside_pct !== 'number') return false;
  if (!(result.risk_impact.downside_pct < result.risk_impact.expected_pct &&
        result.risk_impact.expected_pct < result.risk_impact.upside_pct)) return false; // downside < expected < upside

  // D. TIME TO RISK (OPTIONAL)
  if (result.time_to_risk) {
    if (!result.time_to_risk.threshold_definition) return false;
    if (typeof result.time_to_risk.estimated_days !== 'number') return false;
  }

  // E. MARKET REGIME SENSITIVITY (REQUIRED)
  if (!result.market_regimes) return false;
  if (!result.market_regimes.explanation) return false; // Must explain WHY sensitivity increased

  // F. PORTFOLIO CONCENTRATION (POST-DECISION) (REQUIRED)
  if (!result.concentration_after_decision) return false;
  if (!Array.isArray(result.concentration_after_decision.top_exposures)) return false;

  // Decision asset MUST appear in top exposures
  const decisionAssetSymbol = result.primary_exposure_impact?.asset_symbol;
  if (decisionAssetSymbol && decisionAssetSymbol !== "UNKNOWN") {
    const assetInTop = result.concentration_after_decision.top_exposures.some(
      (exp: any) => exp.symbol?.toUpperCase() === decisionAssetSymbol.toUpperCase()
    );
    if (!assetInTop) return false;
  }

  // G. IRREVERSIBILITY RISK (OPTIONAL)
  if (result.irreversibility_detailed) {
    if (typeof result.irreversibility_detailed.irreversible_loss_usd !== 'number') return false;
    if (typeof result.irreversibility_detailed.irreversible_loss_pct !== 'number') return false;
    // USD loss and % loss must reconcile mathematically
    // This is a simplified check - in a full implementation, we'd validate the relationship
  }

  // H. HEATMAP (OPTIONAL)
  if (result.irreversible_loss_heatmap) {
    if (!result.irreversible_loss_heatmap.interpretation) return false; // Must include interpretation text
  }

  // I. BOTTOM-LINE SUMMARY (REQUIRED)
  if (!result.decision_summary_line) return false;
  if (!result.decision_summary_line.dominant_risk_driver) return false; // Must include dominant_risk_driver

  return true;
}

  // Function to visualize risk - shows only visualizations in a separate view
  function visualizeRisk() {
    setShowOnlyVisualizations(true);
  }

  return (
    <div className="min-h-screen px-6 py-8">
      <div className="mx-auto max-w-6xl">
        <div>
          <div className="text-sm text-muted-foreground">GLOQONT</div>
          <h1 className="text-3xl font-semibold tracking-tight">Scenario Simulation</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Enter a decision, run a scenario, and generate the “last decision” used by Tax Impact.
          </p>
        </div>


        {/* Portfolio summary */}
        <div id="scenario-portfolio-summary" className="mt-6 rounded-2xl border border-border bg-card/80 backdrop-blur p-6">
          <div className="text-sm text-muted-foreground">Current Portfolio</div>

          {portfolio ? (
            <div className="mt-2">
              <div className="flex flex-wrap items-end justify-between gap-3">
                <div>
                  <div className="text-xl font-semibold">{portfolio.name}</div>
                  <div className="text-sm text-muted-foreground mt-1">
                    Risk: <span className="text-foreground">{portfolio.risk_budget}</span> • Value:{" "}
                    <span className="text-foreground">{fmtMoney(portfolio.total_value)}</span> •{" "}
                    <span className="text-foreground">{portfolio.base_currency}</span>
                  </div>
                </div>

                <div className="text-xs text-muted-foreground">
                  Saved: {new Date(portfolio.created_at).toLocaleString()}
                </div>
              </div>

              {positionsSummary ? (
                <div className="mt-3 rounded-xl border border-border bg-muted p-3 text-sm text-foreground/80">
                  {positionsSummary}
                </div>
              ) : null}
            </div>
          ) : (
            <div className="mt-3 text-sm text-red-500">
              No saved portfolio found. Go to <span className="text-foreground">Portfolio Optimizer</span> and click{" "}
              <span className="text-foreground">Save</span>.
            </div>
          )}
        </div>

        {/* Decision Type Selector */}
        <div id="decision-type-selector" className="mt-6 rounded-2xl border border-border bg-card/80 backdrop-blur p-6">
          <div className="text-sm text-muted-foreground">Decision Type</div>
          <div className="mt-2 flex gap-4">
            <label className="flex items-center gap-2">
              <input
                type="radio"
                name="decisionType"
                value="trade"
                checked={decisionType === "trade"}
                onChange={(e) => setDecisionType(e.target.value as "trade" | "rebalance")}
                className="w-4 h-4"
              />
              <span className="text-sm">Trade Decision</span>
            </label>
            <label className="flex items-center gap-2">
              <input
                type="radio"
                name="decisionType"
                value="rebalance"
                checked={decisionType === "rebalance"}
                onChange={(e) => setDecisionType(e.target.value as "trade" | "rebalance")}
                className="w-4 h-4"
              />
              <span className="text-sm">Portfolio Rebalancing</span>
            </label>
          </div>
          <div className="mt-2 text-xs text-muted-foreground">
            {decisionType === "trade"
              ? "Trade decision: Buying stocks not currently in your portfolio."
              : "Portfolio rebalancing: Buying/selling stocks that are already in your portfolio."}
          </div>
        </div>

        {/* Inputs */}
        <div className="mt-6 grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div id="decision-input" className="lg:col-span-2 rounded-2xl border border-border bg-card/80 backdrop-blur p-6">
            <div className="text-sm text-muted-foreground">Decision</div>
            <textarea
              className="mt-2 w-full min-h-[120px] rounded-xl border border-border bg-background px-3 py-2 text-foreground outline-none placeholder:text-muted-foreground focus:border-foreground/40"
              value={decisionText}
              onChange={(e) => setDecisionText(e.target.value)}
              placeholder='Example: "Buy Nvidia 1%" or "Sell Apple 25% and put it on Google"'
            />
            <div className="mt-2 text-xs text-muted-foreground">
              {decisionType === "trade"
                ? "Enter a trade decision (e.g., 'Buy NVDA 1%'). Stocks not in portfolio."
                : "Enter a portfolio rebalancing decision (e.g., 'Sell AAPL 25% and buy GOOGL'). Stocks must be in portfolio."}
            </div>

            {/* Visualize Risk Button - shown after running scenario */}
            {showVisualizeRisk && result && (
              <button
                onClick={visualizeRisk}
                className="mt-4 w-full rounded-xl bg-primary text-primary-foreground font-medium px-4 py-2.5 hover:opacity-90 disabled:opacity-60"
              >
                Visualize Risk
              </button>
            )}
          </div>

          <div id="tax-country-and-actions" className="rounded-2xl border border-border bg-card/80 backdrop-blur p-6">
            <div className="text-sm text-muted-foreground">Tax Country</div>
            <input
              className="mt-2 w-full rounded-xl border border-border bg-background px-3 py-2 text-foreground outline-none placeholder:text-muted-foreground focus:border-foreground/40"
              value={taxCountry}
              onChange={(e) => setTaxCountry(e.target.value)}
              placeholder="United States"
            />

            <button
              id="run-scenario-button"
              onClick={runScenario}
              disabled={loading || !portfolio}
              className="mt-4 w-full rounded-xl bg-primary text-primary-foreground font-medium px-4 py-2.5 hover:opacity-90 disabled:opacity-60"
            >
              {loading ? "Running..." : "Run Scenario"}
            </button>

            <button
              onClick={() => (window.location.href = "/dashboard/tax-impact")}
              className="mt-2 w-full rounded-xl border border-border bg-card px-4 py-2.5 font-medium hover:bg-muted"
            >
              Open Tax Impact
            </button>
          </div>
        </div>

        {/* Error */}
        {err && (
          <div className="mt-6 text-sm rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-red-600">
            {err}
          </div>
        )}

        {/* Result */}
        {result && !showOnlyVisualizations && (
          <div id="scenario-results" className="mt-6 rounded-2xl border border-border bg-card/80 backdrop-blur p-6">
            {/* Validate strict output contract before rendering */}
            {!isValidOutputContract(result) ? (
              <div className="mt-4 text-sm rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-red-600">
                Decision impact could not be computed reliably.
              </div>
            ) : (
              <div>
                {/* Decision Summary */}
                <div className="mt-4">
                  <div className="text-sm font-medium">Impact of Your Decision</div>

                  {/* Decision Summary Section */}
                  <div className="mt-2 rounded-xl border border-border bg-muted p-4">
                    <div className="font-medium text-foreground">Decision Summary</div>
                    <div className="mt-1 text-sm">
                      {result.executed_decision?.combined_actions_description ||
                       `You ${result.decision_summary?.allocation_change_pct && result.decision_summary?.allocation_change_pct > 0 ? 'increased' : 'decreased'} exposure to ${result.decision_summary?.asset?.symbol || result.executed_decision?.primary_exposure_ticker} by ${result.decision_summary?.allocation_change_pct || result.executed_decision?.portfolio_weight_affected_pct}% of portfolio value.`}
                    </div>
                  </div>

                  {/* Primary Exposure Change */}
                  <div className="mt-4 rounded-xl border border-border bg-muted p-4">
                    <div className="font-medium text-foreground">Primary Exposure Change</div>
                    <div className="mt-2 text-sm">
                      {result.decision_summary?.decision_type === "multi_asset_decision" && result.decision_summary?.actions ? (
                        <>
                          {result.decision_summary.actions.map((action: any, index: number) => (
                            <div key={index} className="mb-2">
                              <div><strong>Asset {index + 1} impacted:</strong> {action.asset?.symbol} ({action.asset?.country || "USA"}, {action.asset?.sector || "Sector"})</div>
                              <div><strong>Portfolio weight change:</strong> {action.allocation_change_pct > 0 ? '+' : ''}{action.allocation_change_pct}%</div>
                              <div><strong>New estimated portfolio weight:</strong> {action.previous_weight_pct + action.allocation_change_pct}%</div>
                            </div>
                          ))}
                        </>
                      ) : (
                        <>
                          <div><strong>Primary asset impacted:</strong> {result.primary_exposure_impact?.asset_symbol} ({result.decision_summary?.asset?.country || "USA"}, {result.decision_summary?.asset?.sector || "Sector"})</div>
                          <div><strong>Portfolio weight change:</strong> {result.primary_exposure_impact?.absolute_change_pct > 0 ? '+' : ''}{result.primary_exposure_impact?.absolute_change_pct}%</div>
                          <div><strong>New estimated portfolio weight:</strong> {result.primary_exposure_impact?.weight_after_pct}%</div>
                        </>
                      )}
                    </div>
                    <div className="mt-2 text-sm italic">
                      {result.decision_summary?.decision_type === "multi_asset_decision" && result.decision_summary?.actions ? (
                        <>
                          Why this matters: This multi-asset decision introduces <strong>direct {result.decision_summary?.actions[0]?.asset?.country || "equity"} exposure</strong> and <strong>sectoral exposure to {result.decision_summary?.actions[0]?.asset?.sector?.toLowerCase() || "relevant sectors"}</strong>, while also impacting other assets in your portfolio.
                        </>
                      ) : (
                        <>
                          Why this matters: This decision introduces <strong>direct {result.decision_summary?.asset?.country || "equity"} exposure</strong> and <strong>sectoral exposure to {result.decision_summary?.asset?.sector?.toLowerCase() || "relevant sectors"}</strong>.
                        </>
                      )}
                    </div>
                  </div>

                  {/* What Changed Because of This Decision */}
                  <div className="mt-4 rounded-xl border border-border bg-muted p-4">
                    <div className="font-medium text-foreground">What Changed Because of This Decision</div>
                    <div className="mt-2 text-sm">
                      {result.decision_summary?.decision_type === "multi_asset_decision" && result.decision_summary?.actions ? (
                        <>
                          <div><strong>Net effects introduced by this multi-asset trade:</strong></div>
                          <ul className="list-disc list-inside ml-2 mt-1">
                            {result.concentration_after_decision?.concentration_reduced ? (
                              <li>Reduced single-stock concentration risk in existing holdings</li>
                            ) : (
                              <li>Changed concentration across multiple assets</li>
                            )}
                            {result.decision_summary?.actions.map((action: any, index: number) => (
                              <li key={index}>
                                {action.action === 'buy' || action.action === 'add' || action.action === 'increase' ? 'Increased' : 'Changed'} exposure to {action.asset?.country || "market"} macro growth through {action.asset?.symbol} in the {action.asset?.sector?.toLowerCase() || "relevant sector"}
                              </li>
                            ))}
                            {result.decision_summary?.actions.map((action: any, index: number) => (
                              <li key={`risk-${index}`}>
                                Added {action.asset?.sector?.toLowerCase() || "sector"}-linked earnings risk through {action.asset?.symbol}
                              </li>
                            ))}
                          </ul>
                        </>
                      ) : (
                        <>
                          <div><strong>Net effects introduced by this trade:</strong></div>
                          <ul className="list-disc list-inside ml-2 mt-1">
                            {result.concentration_after_decision?.concentration_reduced ? (
                              <li>Reduced single-stock concentration risk in existing holdings</li>
                            ) : (
                              <li>Increased concentration in the top holding</li>
                            )}
                            <li>{result.decision_summary?.allocation_change_pct && result.decision_summary?.allocation_change_pct > 0 ? 'Increased' : 'Changed'} exposure to {result.decision_summary?.asset?.country || "market"} macro growth</li>
                            <li>Added {result.decision_summary?.asset?.sector?.toLowerCase() || "sector"}-linked earnings risk</li>
                          </ul>
                        </>
                      )}
                    </div>
                  </div>

                  {/* Downside/Upside Risk */}
                  <div className="mt-4 rounded-xl border border-border bg-muted p-4">
                    <div className="font-medium text-foreground">Downside / Upside Risk</div>
                    <div className="mt-2 text-sm">
                      <div><strong>Estimated impact over 1-month horizon under current volatility regime:</strong></div>
                      <div className="mt-1">• <strong>Downside (stress scenario):</strong> <span className="text-red-400">{fmtPct(result.risk_impact?.downside_pct)}</span></div>
                      {result.decision_summary?.decision_type === "multi_asset_decision" && result.decision_summary?.actions ? (
                        <div className="text-xs ml-5">
                          Triggered by {result.decision_summary?.actions.map((action: any) => `${action.asset?.country?.toLowerCase() || "market"} market drawdown or ${action.asset?.sector?.toLowerCase() || "sector"} sector shock`).join(' and ')}
                        </div>
                      ) : (
                        <div className="text-xs ml-5">
                          Triggered by {result.decision_summary?.asset?.country?.toLowerCase() || "market"} market drawdown or {result.decision_summary?.asset?.sector?.toLowerCase() || "sector"} sector shock
                        </div>
                      )}
                      <div className="mt-1">• <strong>Expected outcome (base case):</strong> <span className="text-foreground">{fmtPct(result.risk_impact?.expected_pct)}</span></div>
                      <div className="mt-1">• <strong>Upside (favorable scenario):</strong> <span className="text-green-400">{fmtPct(result.risk_impact?.upside_pct)}</span></div>
                      <div className="mt-1 text-xs italic">Confidence level: {result.risk_impact?.confidence_note}</div>
                    </div>
                  </div>

                  {/* Time to Risk Realization */}
                  {result.time_to_risk && (
                    <div className="mt-4 rounded-xl border border-border bg-muted p-4">
                      <div className="font-medium text-foreground">Time to Risk Realization</div>
                      <div className="mt-2 text-sm">
                        <div><strong>Time to potential material drawdown:</strong> ~{result.time_to_risk?.estimated_days} trading days</div>
                        <div className="mt-1 text-xs">Definition: Estimated time for losses to exceed a predefined risk threshold under adverse market conditions.</div>
                      </div>
                    </div>
                  )}

                  {/* Market Regimes Sensitivity */}
                  <div className="mt-4 rounded-xl border border-border bg-muted p-4">
                    <div className="font-medium text-foreground">Market Regimes This Decision Is Sensitive To</div>
                    <div className="mt-2 text-sm">
                      <div><strong>Heightened sensitivity to:</strong></div>
                      <ul className="list-disc list-inside ml-2 mt-1">
                        {result.market_regimes?.increased_sensitivity?.map((regime: string, idx: number) => (
                          <li key={idx}>{regime.replace(/_/g, ' ')}</li>
                        ))}
                      </ul>
                      <div className="mt-1 text-xs">This sensitivity <strong>did not exist at this magnitude before the trade</strong>.</div>
                    </div>
                  </div>

                  {/* Portfolio Concentration After Decision */}
                  <div className="mt-4 rounded-xl border border-border bg-muted p-4">
                    <div className="font-medium text-foreground">Portfolio Concentration After the Decision</div>
                    <div className="mt-2 text-sm">
                      <div><strong>Top exposures after executing this trade:</strong></div>
                      <table className="w-full text-sm mt-2">
                        <tbody>
                          {(result.concentration_after_decision?.top_exposures || []).map((r: any, idx: number) => (
                            <tr key={idx} className="border-b border-border/60">
                              <td className="py-1">{r.symbol}</td>
                              <td className="py-1 text-right">{r.weight_pct}%</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      <div className="mt-2 text-xs">
                        Interpretation: This trade {result.concentration_after_decision?.concentration_reduced ?
                          "reduces extreme concentration" :
                          "maintains concentration pattern"}, but the portfolio remains dominated by a single equity.
                      </div>
                    </div>
                  </div>

                  {/* Irreversibility Risk */}
                  <div className="mt-4 rounded-xl border border-border bg-muted p-4">
                    <div className="font-medium text-foreground">Irreversibility Risk</div>
                    <div className="mt-2 text-sm">
                      <div><strong>Estimated irreversible capital loss:</strong> {fmtMoney(result.irreversibility_detailed?.irreversible_loss_usd || 0)} ({result.irreversibility_detailed?.irreversible_loss_pct}%)</div>
                      <div className="mt-1 text-xs">Assumptions: Forced exit during market stress, liquidity or behavioral constraints prevent optimal timing</div>
                      <div className="mt-1"><strong>Estimated recovery time:</strong> ~{result.irreversibility_detailed?.recovery_time_months} months</div>
                      <div className="text-xs">Based on historical drawdown and earnings recovery patterns.</div>
                    </div>
                  </div>

                  {/* Irreversible Loss Heatmap - REMOVED PER REQUEST */}

                  {/* Bottom-Line Exposure Summary */}
                  <div className="mt-4 rounded-xl border border-border bg-muted p-4">
                    <div className="font-medium text-foreground">Bottom-Line Exposure Summary</div>
                    <div className="mt-2 text-sm">
                      <div><strong>Decision-attributed downside risk:</strong></div>
                      <div className="text-lg font-semibold mt-1">{fmtMoney(result.decision_summary_line?.max_decision_attributed_loss_usd || 0)} | {result.decision_summary_line?.max_decision_attributed_loss_pct}% of portfolio</div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Visualizations Only View */}
        {showOnlyVisualizations && result && (
          <div className="mt-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-semibold">Risk Visualizations</h2>
              <button
                onClick={() => setShowOnlyVisualizations(false)}
                className="rounded-xl border border-border bg-card px-4 py-2 text-sm hover:bg-muted"
              >
                Back to Results
              </button>
            </div>

            {/* Validate strict output contract before rendering */}
            {!isValidOutputContract(result) ? (
              <div className="text-sm rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-red-600">
                Decision impact could not be computed reliably.
              </div>
            ) : (
              <div>
                {/* Advanced Decision Visualizations */}
                {/* Display main visualization */}
                {result.visualization_data && (
                  <div className="mb-8">
                    <h3 className="text-lg font-medium mb-4">Overall Decision Impact</h3>
                    <DecisionVisualizations
                      visualizationData={result.visualization_data}
                      decisionType={result.decision_summary?.decision_type || "trade_decision"}
                    />
                  </div>
                )}

                {/* Display individual visualizations for multiple actions */}
                {result.individual_visualizations && result.individual_visualizations.length > 0 && (
                  <div>
                    <h3 className="text-lg font-medium mb-4">Individual Action Visualizations</h3>
                    {result.individual_visualizations.map((visData: any, index: number) => (
                      <div key={index} className="mb-8 p-4 border border-border rounded-xl bg-muted/70">
                        <h4 className="text-md font-medium mb-2">
                          Action {index + 1}: {visData.decision_delta?.asset} {visData.decision_delta?.change > 0 ? 'Buy' : 'Sell'} {Math.abs(visData.decision_delta?.change || 0)}%
                        </h4>
                        <DecisionVisualizations
                          visualizationData={visData}
                          decisionType={visData.decision_type || "trade_decision"}
                        />
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
