"""
GLOQONT Intent Parser — Natural Language → Structured Decision

This module converts unstructured user input into StructuredDecision objects.

Architecture:
- Layer 1: Smart Heuristic Parser (regex + NLP rules) - FAST
- Layer 2: LLM Parser (GPT-4/Gemini) - ACCURATE (optional)

The heuristic parser handles common patterns like:
- "Buy AAPL 10%"
- "Short Apple after 3 days"
- "Increase NVDA by 20%"
- "Reduce tech exposure"

For complex/ambiguous inputs, the LLM parser is invoked.
"""

import re
import secrets
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any

from decision_schema import (
    StructuredDecision, InstrumentAction, Timing, Constraint,
    DecisionType, Direction, TimingType, CapitalSource
)


class IntentParser:
    """
    Multi-layer intent parser for converting natural language to structured decisions.
    """
    
    # Common action keywords
    BUY_KEYWORDS = {"buy", "purchase", "acquire", "add", "increase", "long", "overweight"}
    SELL_KEYWORDS = {"sell", "reduce", "trim", "decrease", "exit", "underweight", "liquidate"}
    SHORT_KEYWORDS = {"short", "shorting", "bet against"}
    COVER_KEYWORDS = {"cover", "close short", "buy to cover"}
    
    # Time pattern: "after X days/hours/weeks"
    TIME_PATTERN = re.compile(
        r"(?:after|in|wait)\s+(\d+)\s*(day|days|hour|hours|week|weeks|month|months)",
        re.IGNORECASE
    )
    
    # Percentage pattern: "5%", "5 percent", "5 pct"
    PERCENT_PATTERN = re.compile(
        r"(\d+(?:\.\d+)?)\s*(%|percent|pct)",
        re.IGNORECASE
    )
    
    # Dollar amount pattern: "$5000", "5000 dollars", "5k", "₹5000", "C$500", "€100"
    # STRICTER: Require currency prefix OR currency suffix. prevent matching "5" or "10" 
    DOLLAR_PATTERN = re.compile(
        r"(?:[\$₹£€]|C\$)\s*(\d+(?:\.\d+)?)\s*(?:k|m|b|million|billion)?|(?:(\d+(?:\.\d+)?)\s*(?:dollars|usd|rs|inr|rupees|euros|eur|cad|gbp|million dollars))",
        re.IGNORECASE
    )
    
    # Common ticker aliases - US Markets
    TICKER_ALIASES = {
        # US Tech
        "apple": "AAPL",
        "microsoft": "MSFT",
        "google": "GOOGL",
        "alphabet": "GOOGL",
        "amazon": "AMZN",
        "meta": "META",
        "facebook": "META",
        "nvidia": "NVDA",
        "tesla": "TSLA",
        "netflix": "NFLX",
        "amd": "AMD",
        "intel": "INTC",
        "ibm": "IBM",
        "oracle": "ORCL",
        "salesforce": "CRM",
        "adobe": "ADBE",
        "paypal": "PYPL",
        # US Finance
        "visa": "V",
        "mastercard": "MA",
        "jpmorgan": "JPM",
        "goldman": "GS",
        "berkshire": "BRK-B",
        # US Consumer
        "walmart": "WMT",
        "costco": "COST",
        "disney": "DIS",
        "coca-cola": "KO",
        "pepsi": "PEP",
        "mcdonalds": "MCD",
        "nike": "NKE",
        # US Industrial
        "boeing": "BA",
        "lockheed": "LMT",
        # US Energy
        "exxon": "XOM",
        "chevron": "CVX",
        # US Healthcare
        "pfizer": "PFE",
        "johnson": "JNJ",
        "unitedhealth": "UNH",
        # US ETFs
        "spy": "SPY",
        "qqq": "QQQ",
        "iwm": "IWM",
        "voo": "VOO",
        "vti": "VTI",
        "agg": "AGG",
        "tlt": "TLT",
        "gld": "GLD",
        # Crypto
        "btc": "BTC-USD",
        "bitcoin": "BTC-USD",
        "eth": "ETH-USD",
        "ethereum": "ETH-USD",
        # Indian Stocks (NSE)
        "reliance": "RELIANCE.NS",
        "tcs": "TCS.NS",
        "infosys": "INFY.NS",
        "infy": "INFY.NS",
        "hdfc": "HDFCBANK.NS",
        "hdfc bank": "HDFCBANK.NS",
        "icici": "ICICIBANK.NS",
        "icici bank": "ICICIBANK.NS",
        "kotak": "KOTAKBANK.NS",
        "sbi": "SBIN.NS",
        "state bank": "SBIN.NS",
        "axis": "AXISBANK.NS",
        "axis bank": "AXISBANK.NS",
        "wipro": "WIPRO.NS",
        "hcl": "HCLTECH.NS",
        "hcl tech": "HCLTECH.NS",
        "bharti": "BHARTIARTL.NS",
        "airtel": "BHARTIARTL.NS",
        "bajaj finance": "BAJFINANCE.NS",
        "bajaj": "BAJFINANCE.NS",
        "asian paints": "ASIANPAINT.NS",
        "maruti": "MARUTI.NS",
        "tata motors": "TATAMOTORS.NS",
        "tata steel": "TATASTEEL.NS",
        "tata": "TCS.NS",
        "itc": "ITC.NS",
        "hindustan unilever": "HINDUNILVR.NS",
        "hul": "HINDUNILVR.NS",
        "larsen": "LT.NS",
        "l&t": "LT.NS",
        "sun pharma": "SUNPHARMA.NS",
        "nifty": "^NSEI",
        "sensex": "^BSESN",
        "nifty50": "^NSEI",
    }
    
    # Sector keywords for sector-based decisions
    SECTOR_KEYWORDS = {
        "tech": ["AAPL", "MSFT", "GOOGL", "NVDA", "AMD", "INTC"],
        "technology": ["AAPL", "MSFT", "GOOGL", "NVDA", "AMD", "INTC"],
        "healthcare": ["JNJ", "UNH", "PFE", "ABBV", "MRK"],
        "health": ["JNJ", "UNH", "PFE", "ABBV", "MRK"],
        "finance": ["JPM", "BAC", "GS", "MS", "V", "MA"],
        "financial": ["JPM", "BAC", "GS", "MS", "V", "MA"],
        "energy": ["XOM", "CVX", "COP", "SLB", "EOG"],
        "consumer": ["AMZN", "WMT", "COST", "HD", "NKE"],
        "industrial": ["BA", "CAT", "GE", "HON", "UPS"],
    }
    
    # Keywords for sector-level adjustments
    REDUCE_KEYWORDS = {"reduce", "decrease", "lower", "cut", "trim", "less"}
    INCREASE_KEYWORDS = {"increase", "raise", "boost", "more", "add to", "grow"}
    
    # Keywords for swap/compound decisions
    SWAP_KEYWORDS = {"put", "move", "transfer", "reallocate", "shift", "swap", "into", "to"}
    EXPOSURE_KEYWORDS = {"exposure", "allocation", "position", "weight", "holdings"}
    
    # Pattern for "sell X and buy Y" or "sell X put in Y"
    # Relaxed to handle "put those 40% in", "move into", etc.
    # We use a non-capturing group to skip filler words (those, that, %, in, etc.) before the target
    COMPOUND_PATTERN = re.compile(
        r"(sell|reduce|trim|decrease|exit)\s+([a-zA-Z0-9\.\^:-]+)\s+(\d+(?:\.\d+)?)\s*%?.*?(buy|put|move|into|in|swap|allocate)(?:\s+(?:those|that|the|it|this|proceeds|capital|amount|\d+(?:\.\d+)?%?|with|of|and|or|in|into))*\s+([a-zA-Z0-9\.\^:-]+)",
        re.IGNORECASE | re.DOTALL
    )
    
    # Pattern for sector exposure: "reduce tech exposure by 10%"
    SECTOR_EXPOSURE_PATTERN = re.compile(
        r"(reduce|increase|cut|boost|lower|raise)\s+(\w+)\s+(?:exposure|allocation|position|holdings?)(?:\s+by)?\s+(\d+(?:\.\d+)?)\s*%?",
        re.IGNORECASE
    )

    # Macro Targets for heuristic parsing
    MACRO_TARGETS = {
        "rates": ["interest rate", "rates", "fed rate", "yields", "rate"],
        "inflation": ["inflation", "cpi", "ppi"],
        "oil": ["oil", "crude", "energy prices"],
        "gdp": ["gdp", "gpd", "growth", "economy", "recession"],
        "vix": ["vix", "volatility", "fear index"],
        "tech": ["tech", "technology", "nasdaq", "qqq"],
    }
    
    # Macro Directions
    UP_KEYWORDS = {"up", "rise", "increase", "spike", "soar", "higher", "climb", "jump"}
    DOWN_KEYWORDS = {"down", "fall", "drop", "crash", "lower", "decline", "slump", "collapse", "recession", "cut", "cute"}
    
    def __init__(self, llm_client=None):
        """
        Initialize the parser.
        
        Args:
            llm_client: Optional LLM client for complex parsing (Phase 2)
        """
        self.llm_client = llm_client
    
    def parse(self, text: str, portfolio: Optional[Dict[str, Any]] = None) -> StructuredDecision:
        """
        Parse natural language into a StructuredDecision.
        
        Flow:
        1. Heuristic Parser (Fast Path)
        2. If confidence < 0.95 -> LLM Parser (Fallback Path)
        3. Validation
        """
        text = text.strip()
        
        # 1. Heuristic Path
        decision = self._parse_heuristic(text, portfolio)
        
        # 2. LLM Fallback (if confidence low)
        # We check for API key availability inside _parse_llm
        if decision.confidence_score < 0.95:
             # Try LLM
             try:
                 llm_decision = self._parse_llm(text, portfolio, decision)
                 # Only use LLM result if it worked (has actions or high confidence)
                 if llm_decision.actions or llm_decision.warnings:
                     decision = llm_decision
             except Exception as e:
                 # Fallback to heuristic result but add warning
                 decision.warnings.append(f"LLM parsing failed, using heuristic: {str(e)}")

        # 3. Validation (Critical Safety Gate)
        # Validate logic is now in StructuredDecision.validate() which returns list of error strings
        validation_errors = decision.validate(portfolio)
        if validation_errors:
            # Downgrade confidence if validation fails
            decision.confidence_score *= 0.5
            decision.warnings.extend(validation_errors)
            
        # 4. Final Decision Type Alignment
        # User Rule: Single asset = Trade, Multi asset/Swap/Sector = Rebalance
        # REFINEMENT: If actions are all in the same direction (e.g. all BUY), treat as TRADE (Basket Trade)
        # to ensure exposure is added/removed in simulation. Rebalance implies mixed directions (Buy & Sell).
        unique_directions = {a.direction for a in decision.actions}
        
        has_buy = Direction.BUY in unique_directions
        has_sell = Direction.SELL in unique_directions or Direction.SHORT in unique_directions
        
        # If we have market shocks, it is a custom scenario even if there are no trades
        if decision.market_shocks:
             decision.decision_type = DecisionType.TRADE # Default container for simulation
             
        elif has_buy and has_sell:
            decision.decision_type = DecisionType.REBALANCE
        else:
            decision.decision_type = DecisionType.TRADE
        
        return decision

    def _parse_heuristic(self, text: str, portfolio: Optional[Dict[str, Any]] = None) -> StructuredDecision:
        """
        Fast regex-based parser for common patterns.
        Handles: single trades, sector adjustments, compound/swap decisions, AND MACRO SHOCKS.
        """
        from decision_schema import MarketShock, ScenarioType
        
        decision = StructuredDecision(original_text=text)
        
        # Normalize text: pad punctuation with spaces to ensure tokens are separated
        text_normalized = text.replace("?", " ? ").replace(".", " . ").replace(",", " , ").replace("!", " ! ")
        text_lower = text_normalized.lower()
        
        # Default confidence
        decision.confidence_score = 0.0
        
        # ==== MACRO SCENARIO PARSING (Heuristic) ====
        # Check for "What if" or simple shock statements like "Oil crash"
        # Only trigger if we find a specific macro target keyword
        found_macro = None
        for key, aliases in self.MACRO_TARGETS.items():
            if any(alias in text_lower for alias in aliases):
                found_macro = key
                break
        
        # Only proceed if we found a macro keyword AND it's likely a scenario (has direction or is a question)
        has_direction = any(w in text_lower for w in self.UP_KEYWORDS | self.DOWN_KEYWORDS)
        
        if found_macro and (has_direction or "?" in text):
            # Determine direction
            shock_dir = 0
            if any(w in text_lower for w in self.UP_KEYWORDS):
                shock_dir = 1
            elif any(w in text_lower for w in self.DOWN_KEYWORDS):
                shock_dir = -1
                
            # Determine magnitude
            magnitude = 0.0
            pct_match = self.PERCENT_PATTERN.search(text)
            if pct_match:
                try:
                    magnitude = float(pct_match.group(1))
                except:
                    pass
            
            # If no magnitude found, apply defaults
            if magnitude == 0.0:
                 if found_macro == "rates": magnitude = 1.0 # 1% (100bps)
                 elif found_macro == "inflation": magnitude = 2.0
                 elif found_macro == "oil": magnitude = 20.0
                 elif found_macro == "gdp": magnitude = 2.0
                 elif found_macro == "vix": magnitude = 50.0 # +50% VIX
                 elif found_macro == "tech": magnitude = 10.0 # 10% correction
                 
            # Handle basis points (bps) if in text
            if "bps" in text_lower or "basis points" in text_lower:
                 magnitude = magnitude / 100.0
            
            # Apply direction
            final_mag = magnitude
            if shock_dir != 0:
                final_mag = magnitude * shock_dir
            elif "recession" in text_lower and found_macro == "gdp":
                final_mag = -magnitude # Recession implies negative GDP

            # Map to ScenarioType
            scenario_type = ScenarioType.CUSTOM_SHOCK
            target = found_macro.upper()
            
            if found_macro == "rates": scenario_type = ScenarioType.RATES_CHANGE
            elif found_macro == "inflation": scenario_type = ScenarioType.INFLATION_CHANGE
            elif found_macro == "gdp": scenario_type = ScenarioType.GDP_GROWTH
            elif found_macro == "oil": scenario_type = ScenarioType.COMMODITY_SHOCK
            elif found_macro == "vix": scenario_type = ScenarioType.VOLATILITY_SHOCK
            elif found_macro == "tech": 
                scenario_type = ScenarioType.SECTOR_SHOCK
                target = "TECH"

            shock = MarketShock(
                shock_type=scenario_type,
                target=target,
                magnitude=final_mag,
                unit="percent",
                description=f"Simulated {final_mag:+.1f}% change in {target}"
            )
            decision.market_shocks.append(shock)
            decision.confidence_score = 0.85
            return decision
        
        # ==== PATTERN 1: Sector Exposure (e.g., "reduce tech exposure by 10%") ====
        sector_match = self.SECTOR_EXPOSURE_PATTERN.search(text)
        if sector_match:
            action_word = sector_match.group(1).lower()
            sector_name = sector_match.group(2).lower()
            size_pct = float(sector_match.group(3))
            
            # Determine direction
            direction = Direction.SELL if action_word in self.REDUCE_KEYWORDS else Direction.BUY
            
            # Get sector tickers from portfolio or defaults
            sector_tickers = self.SECTOR_KEYWORDS.get(sector_name, [])
            
            # If portfolio exists, find matching tickers
            matching_tickers = []
            if portfolio and sector_tickers:
                positions = portfolio.get("positions", [])
                portfolio_tickers = {p.get("ticker"): p.get("weight", 0) for p in positions}
                matching_tickers = [t for t in sector_tickers if t in portfolio_tickers]
            
            if matching_tickers:
                # Distribute the size proportionally across matching sector tickers
                total_sector_weight = sum(portfolio_tickers[t] for t in matching_tickers)
                for ticker in matching_tickers:
                    ticker_weight = portfolio_tickers[ticker]
                    # Proportional share of the adjustment
                    if total_sector_weight > 0:
                        rel_weight = ticker_weight / total_sector_weight
                        ticker_pct = size_pct * rel_weight
                    else:
                        ticker_pct = size_pct / len(matching_tickers)
                    
                    action = InstrumentAction(
                        symbol=ticker,
                        direction=direction,
                        size_percent=round(ticker_pct, 2),
                        timing=Timing()
                    )
                    decision.actions.append(action)
                
                decision.decision_type = DecisionType.REBALANCE
                decision.confidence_score = 0.85
                return decision
            else:
                # No portfolio context or no matches
                decision.warnings.append(f"Sector '{sector_name}' detected but no matching positions found in portfolio context.")
                placeholder = sector_tickers[0] if sector_tickers else "SECTOR_ETF"
                action = InstrumentAction(symbol=placeholder, direction=direction, size_percent=size_pct, timing=Timing(), constraints=[f"Entire {sector_name} sector"])
                decision.actions.append(action)
                decision.decision_type = DecisionType.REBALANCE
                decision.confidence_score = 0.6
                return decision

        # ==== PATTERN 1.5: Sell Whole Portfolio / Liquidate ====
        LIQUIDATE_PATTERN = re.compile(
            r"(sell|liquidate|close|exit)\s+(my\s+)?(whole|entire|all|full)?\s*(portfolio|positions|holdings|everything)",
            re.IGNORECASE
        )
        if LIQUIDATE_PATTERN.search(text):
            if portfolio and portfolio.get("positions"):
                for pos in portfolio.get("positions"):
                    ticker = pos.get("ticker", "").upper()
                    if ticker:
                        action = InstrumentAction(
                            symbol=ticker,
                            direction=Direction.SELL,
                            size_percent=100.0,
                            timing=Timing()
                        )
                        decision.actions.append(action)
                
                decision.decision_type = DecisionType.REBALANCE
                decision.confidence_score = 0.98
                decision.warnings.append("Detected request to liquidate entire portfolio.")
                return decision
            else:
                decision.warnings.append("Request to liquidate portfolio, but no active portfolio context available.")
                # Fallback to general unknown
        
        # ==== PATTERN 2: Compound/Swap (e.g., "sell AAPL 40% and put in MSFT") ====
        compound_match = self.COMPOUND_PATTERN.search(text)
        if compound_match:
            sell_action = compound_match.group(1).lower()
            source_ticker_raw = compound_match.group(2)
            size_pct = float(compound_match.group(3))
            buy_action = compound_match.group(4).lower()
            target_ticker_raw = compound_match.group(5)
            
            # Resolve ticker aliases
            source_ticker = self.TICKER_ALIASES.get(source_ticker_raw.lower(), source_ticker_raw.upper())
            target_ticker = self.TICKER_ALIASES.get(target_ticker_raw.lower(), target_ticker_raw.upper())
            
            # Create sell action
            sell = InstrumentAction(
                symbol=source_ticker,
                direction=Direction.SELL,
                size_percent=size_pct,
                timing=Timing()
            )
            decision.actions.append(sell)
            
            # Create buy action with same size
            buy = InstrumentAction(
                symbol=target_ticker,
                direction=Direction.BUY,
                size_percent=size_pct,
                timing=Timing()
            )
            decision.actions.append(buy)
            
            decision.decision_type = DecisionType.REBALANCE
            decision.confidence_score = 0.90
            return decision
        
        # ==== PATTERN 3: Standard Single-Ticker Decision ====
        # 1. Identify Action
        action_type = None
        direction = None
        
        if any(w in text_lower for w in self.BUY_KEYWORDS) or "buy/short" in text_lower:
            direction = Direction.BUY
        elif any(w in text_lower for w in self.SELL_KEYWORDS):
            direction = Direction.SELL
        elif any(w in text_lower for w in self.SHORT_KEYWORDS):
            direction = Direction.SHORT
        elif any(w in text_lower for w in self.COVER_KEYWORDS):
            direction = Direction.COVER
            
        if not direction:
            # If no clear action found, return indeterminate decision
            # UNLESS we have shocks from earlier (which should have returned already, but safe guard)
            if not decision.market_shocks:
                decision.confidence_score = 0.1
                decision.warnings.append("No clear action found (buy/sell/short/cover).")
            return decision

        # 2. Identify Ticker
        symbol = None
        words = text.split()  # Keep original casing for alias checks
        
        # Check aliases first - word by word
        for w in words:
            clean_w = w.strip(".,!?:$").lower()
            if clean_w in self.TICKER_ALIASES:
                symbol = self.TICKER_ALIASES[clean_w]
                break
        
        # If no alias match, look for standalone ticker-like words
        if not symbol:
            # Build exclusion set: stop words + action keywords (upper-cased)
            ALL_KEYWORDS = set()
            ALL_KEYWORDS.update(w.upper() for w in self.BUY_KEYWORDS)
            ALL_KEYWORDS.update(w.upper() for w in self.SELL_KEYWORDS)
            ALL_KEYWORDS.update(w.upper() for w in self.SHORT_KEYWORDS)
            ALL_KEYWORDS.update(w.upper() for w in self.COVER_KEYWORDS)
            STOP_WORDS = {"I", "A", "AM", "AT", "IN", "ON", "OF", "TO", "BY", "FOR", "IS", "OR", "IT", "MY", "ME", "UP", "DO", "AN", "AS", "BE", "WE", "SO", "IF", "THE", "AND", "WITH", "THIS", "THAT", "FROM", "SHARES", "SHARE", "LOT", "LOTS", "UNIT", "UNITS"}
            ALL_KEYWORDS.update(STOP_WORDS)
            
            for w in words:
                clean_w = w.strip(".,!?:$")
                upper_w = clean_w.upper()
                
                # Skip if it's an action keyword or stop word
                if upper_w in ALL_KEYWORDS:
                    continue
                
                # Valid ticker: 1-5 chars, alphanumeric (allow . for international like RELIANCE.NS)
                # EXCLUDE pure numbers (unless specifically 6 chars for China/India codes, but "12" is definitely not)
                if 1 <= len(clean_w) <= 12 and all(c.isalnum() or c in '.-:' for c in clean_w):
                     # Heuristic: If it's purely numeric and length < 3, it's likely a quantity, not a ticker
                     if clean_w.isdigit() and len(clean_w) < 3:
                         continue
                         
                     symbol = upper_w
                     break
        
        if not symbol:
            decision.confidence_score = 0.2
            decision.warnings.append("Could not identify a valid ticker symbol in your input.")
            return decision
        
        # NEW: Validate that symbol looks real (warn if unknown)
        # Check if it matches any known alias target or is in portfolio context
        known_tickers = set(self.TICKER_ALIASES.values())
        if portfolio:
            known_tickers.update(p.get("ticker", "").upper() for p in portfolio.get("positions", []))
        
        if symbol not in known_tickers:
            decision.warnings.append(f"Ticker '{symbol}' is not recognized. Verify this is a valid symbol.")

        # 3. Identify Size
        size_pct = None
        size_usd = None
        size_shares = None  # NEW: explicit share count
        
        pct_match = self.PERCENT_PATTERN.search(text)
        if pct_match:
            try:
                size_pct = float(pct_match.group(1))
            except ValueError:
                pass
                
        usd_match = self.DOLLAR_PATTERN.search(text)
        if usd_match:
            try:
                # Group 1: Number with $ prefix
                # Group 2: Number with dollar suffix
                amt_str = usd_match.group(1) or usd_match.group(2)
                if amt_str:
                    amt = float(amt_str)
                    
                    # Check for K/M/B suffixes in original text context if needed, 
                    # but our regex now includes some suffix checking in non-capturing groups.
                    # For simplicity with the new regex, we extracted the number. 
                    # Let's simple-check specific multiplier suffixes in the full match if we extracted from group 1 (prefix style)
                    
                    full_match = usd_match.group(0).lower()
                    if 'k' in full_match or 'thousand' in full_match:
                        amt *= 1000
                    elif 'm' in full_match or 'million' in full_match:
                        amt *= 1000000
                    elif 'b' in full_match or 'billion' in full_match:
                        amt *= 1000000000
                    
                    # FX CONVERSION: Detect non-USD currency symbols and convert to actual USD
                    # Without this, ₹2300 gets stored as size_usd=2300, then the frontend
                    # multiplies by 83.5 again (USD→INR) producing ₹1,92,050 instead of ₹2,300
                    HEURISTIC_FX_RATES = {
                        "₹": 83.5,   # INR to USD divisor
                        "£": 0.79,   # GBP to USD divisor
                        "€": 0.92,   # EUR to USD divisor
                    }
                    # Check which currency symbol was matched
                    raw_match = usd_match.group(0)
                    detected_currency_divisor = None
                    for symbol_char, divisor in HEURISTIC_FX_RATES.items():
                        if symbol_char in raw_match:
                            detected_currency_divisor = divisor
                            break
                    # Also check suffix-based: "rs", "inr", "rupees"
                    if detected_currency_divisor is None:
                        suffix_lower = full_match
                        if any(kw in suffix_lower for kw in ["rs", "inr", "rupees"]):
                            detected_currency_divisor = 83.5
                        elif any(kw in suffix_lower for kw in ["euros", "eur"]):
                            detected_currency_divisor = 0.92
                        elif any(kw in suffix_lower for kw in ["gbp"]):
                            detected_currency_divisor = 0.79
                        elif "c$" in raw_match.lower() or "cad" in suffix_lower:
                            detected_currency_divisor = 1.35
                    
                    if detected_currency_divisor and detected_currency_divisor > 1.0:
                        # Non-USD currency: convert to USD by dividing
                        size_usd = amt / detected_currency_divisor
                    elif detected_currency_divisor and detected_currency_divisor < 1.0:
                        # EUR/GBP: 1 EUR = ~1.09 USD, so multiply by (1/rate)
                        size_usd = amt / detected_currency_divisor
                    else:
                        # USD or unknown: keep as-is
                        size_usd = amt
            except ValueError:
                pass

        # NEW: Share quantity pattern "45 shares"
        SHARE_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*(?:shares|share)", re.IGNORECASE)
        share_match = SHARE_PATTERN.search(text)
        if share_match:
            try:
                size_shares = float(share_match.group(1))
            except ValueError:
                pass
        timing = Timing()
        time_match = self.TIME_PATTERN.search(text)
        if time_match:
            try:
                amount = int(time_match.group(1))
                unit = time_match.group(2).lower()
                
                timing.type = TimingType.DELAY
                
                if "hour" in unit:
                    # Hours: set delay_hours directly
                    timing.delay_hours = amount
                elif "week" in unit:
                    timing.delay_days = amount * 7
                elif "month" in unit:
                    timing.delay_days = amount * 30
                else:
                    # Days is the default
                    timing.delay_days = amount
            except ValueError:
                pass
        
        # Construct Action
        action = InstrumentAction(
            symbol=symbol,
            direction=direction,
            size_percent=size_pct,
            size_usd=size_usd,
            size_shares=size_shares,  # NEW
            timing=timing
        )
        
        decision.actions.append(action)
        decision.decision_type = DecisionType.TRADE # Default to trade
        
        # Heuristic Success Confidence
        # If we got direction, symbol, and (size OR timing), we are pretty confident
        if direction and symbol:
            base_conf = 0.7
            if size_pct or size_usd or size_shares:  # Updated confidence check
                base_conf += 0.2
            if timing.type == TimingType.DELAY:
                base_conf += 0.05
            decision.confidence_score = min(base_conf, 0.95)
        else:
            decision.confidence_score = 0.3
            
        return decision

    def _parse_llm(
        self, 
        text: str, 
        portfolio: Optional[Dict[str, Any]], 
        fallback: StructuredDecision
    ) -> StructuredDecision:
        """
        Parse using LLM (Gemini) with strict JSON schema.
        matches User Requirement 3.2: LLM outputs strict JSON.
        """
        import os
        import json
        
        # Check for API key
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            fallback.warnings.append("LLM parsing unavailable: No GOOGLE_API_KEY configured")
            return fallback
        
        try:
            import google.generativeai as genai
            
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.0-flash')
            
            # Build portfolio context
            portfolio_context = ""
            if portfolio:
                positions = portfolio.get("positions", [])
                if positions:
                    portfolio_context = "Current Portfolio:\n" + "\n".join(
                        f"- {p.get('ticker')} ({p.get('weight', 0)*100:.1f}%)" 
                        for p in positions[:10]
                    )
            
            prompt = f"""You are a strict, highly robust financial intent parser. Convert the user input into a JSON object.
The user's input might be grammatically incorrect, highly colloquial, or very unique ("unique decisions"). You must adapt and infer their financial intent accurately.
Do NOT compute, simulate, or advise. Only extract intent.

User Input: "{text}"
{portfolio_context}

IMPORTANT: 
- For trades: Extract action, ticker, size, and TIMING (if 'after X days/hours'). Identify tickers even if slightly misspelled. For absolute fiat currencies (e.g. ₹23000, €500), extract the numerical value. If the currency is NOT USD, you MUST mathematically convert it to USD by DIVIDING the raw number by these approximate exchange rates (1 USD = 83.5 INR, 0.92 EUR, 0.79 GBP, 1.35 CAD, 1.54 AUD) and put the final computed USD value into `size_usd`. NEVER put the raw foreign currency number directly into `size_usd` without dividing it first. Do NOT include the currency symbol in the output JSON.
- For macro scenarios: If user asks "What if rates rise?", output a "market_shock".
- For sector shocks: "What if tech crashes 20%?" -> "market_shock" on target "TECH" with magnitude -20.0.

Output strict JSON with this schema:
{{
  "intent": "string (brief summary)",
  "decision_type": "trade" | "rebalance",
  "market_shocks": [
      {{
          "shock_type": "rates_change" | "inflation_change" | "gdp_growth" | "commodity_shock" | "sector_shock" | "custom_shock",
          "target": "string (e.g. RATES, OIL, TECH)",
          "magnitude": float (e.g. 5.0 for 5%),
          "unit": "percent",
          "description": "string"
      }}
  ],
  "actions": [
    {{
      "action": "buy" | "sell" | "short" | "cover",
      "instrument": "TICKER (uppercase)",
      "size_percent": float | null,
      "size_usd": float | null,
      "timing_type": "immediate" | "delay",
      "delay_days": int (default 0)
    }}
  ],
  "ambiguity_score": float (0.0 to 1.0),
  "confidence_score": float (0.0 to 1.0)
}}

Examples:

1. Simple buy:
Input: "Buy $4000 AAPL after 3 days"
JSON: {{"intent":"Buy AAPL with delay","decision_type":"trade","actions":[{{"action":"buy","instrument":"AAPL","size_usd":4000.0,"timing_type":"delay","delay_days":3}}],"ambiguity_score":0.05,"confidence_score":0.95}}

2. Sector reduction:
Input: "Reduce tech exposure by 10%"
JSON: {{"intent":"Reduce technology sector holdings","decision_type":"rebalance","actions":[{{"action":"sell","instrument":"AAPL","size_percent":10.0,"timing_type":"immediate","delay_days":0}},{{"action":"sell","instrument":"MSFT","size_percent":10.0,"timing_type":"immediate","delay_days":0}},{{"action":"sell","instrument":"GOOGL","size_percent":10.0,"timing_type":"immediate","delay_days":0}}],"ambiguity_score":0.15,"confidence_score":0.85}}

3. Swap/Transfer:
Input: "Sell Apple 40% and put those in Microsoft"
JSON: {{"intent":"Transfer 40% from AAPL to MSFT","decision_type":"rebalance","actions":[{{"action":"sell","instrument":"AAPL","size_percent":40.0,"timing_type":"immediate","delay_days":0}},{{"action":"buy","instrument":"MSFT","size_percent":40.0,"timing_type":"immediate","delay_days":0}}],"ambiguity_score":0.1,"confidence_score":0.9}}

4. Conditional:
Input: "Short Tesla if it drops 5%"
JSON: {{"intent":"Conditional short on TSLA price drop","decision_type":"trade","actions":[{{"action":"short","instrument":"TSLA","size_percent":null,"timing_type":"immediate","delay_days":0}}],"ambiguity_score":0.3,"confidence_score":0.7}}

5. Absolute Fiat Buy in other currencies:
Input: "Buy TCS ₹50000 more"
JSON: {{"intent":"Buy more TCS","decision_type":"trade","actions":[{{"action":"buy","instrument":"TCS.NS","size_usd":598.80,"timing_type":"immediate","delay_days":0}}],"ambiguity_score":0.05,"confidence_score":0.98}}
"""

            response = model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Clean up response (remove markdown code blocks if present)
            if response_text.startswith("```"):
                lines = response_text.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                response_text = "\n".join(lines)
            
            # Parse JSON
            parsed = json.loads(response_text)
            
            # Build structured decision from LLM output
            decision = StructuredDecision(
                decision_id=fallback.decision_id,
                original_text=text,
                parsed_at=fallback.parsed_at,
            )
            
            decision.decision_type = DecisionType(parsed.get("decision_type", "trade").lower())
            decision.confidence_score = float(parsed.get("confidence_score", 0.8))
            decision.ambiguity_score = float(parsed.get("ambiguity_score", 0.2))
            
            # Parse Market Shocks
            for shock_data in parsed.get("market_shocks", []):
                try:
                    shock = MarketShock(
                        shock_type=shock_data.get("shock_type", "custom_shock"),
                        target=shock_data.get("target", "UNKNOWN"),
                        magnitude=float(shock_data.get("magnitude", 0.0)),
                        unit=shock_data.get("unit", "percent"),
                        description=shock_data.get("description")
                    )
                    decision.market_shocks.append(shock)
                except Exception as e:
                    decision.warnings.append(f"Failed to parse shock: {str(e)}")

            for action_data in parsed.get("actions", []):
                timing = Timing()
                t_type = action_data.get("timing_type", "immediate").lower()
                timing.type = TimingType.DELAY if t_type == "delay" else TimingType.IMMEDIATE
                timing.delay_days = action_data.get("delay_days", 0)
                
                direction_str = action_data.get("action", "buy").lower()
                direction_map = {
                    "buy": Direction.BUY,
                    "sell": Direction.SELL,
                    "short": Direction.SHORT,
                    "cover": Direction.COVER,
                }
                
                # Handle constraints if present (simple string to object mapping for now)
                constraints = []
                if action_data.get("constraints"):
                     # TODO: Parse constraint string if sophisticated
                     pass

                action = InstrumentAction(
                    symbol=action_data.get("instrument", "").upper(),
                    direction=direction_map.get(direction_str, Direction.BUY),
                    size_percent=action_data.get("size_percent"),
                    size_usd=action_data.get("size_usd"),
                    timing=timing,
                    constraints=constraints
                )
                
                if action.symbol:
                    decision.actions.append(action)
            
            return decision
            
        except Exception as e:
            fallback.warnings.append(f"LLM parsing failed or unavailable: {str(e)}")
            return fallback


# Convenience function for module-level use
_parser = IntentParser()

def parse_decision(text: str, portfolio: Optional[Dict[str, Any]] = None) -> StructuredDecision:
    """
    Parse natural language into a StructuredDecision.
    
    Args:
        text: User input text
        portfolio: Current portfolio state (optional)
        
    Returns:
        StructuredDecision object
    """
    return _parser.parse(text, portfolio)


# Example usage and testing
if __name__ == "__main__":
    test_inputs = [
        "Buy AAPL 10%",
        "Short Apple 4% after 3 days",
        "Increase NVDA by 20%",
        "Reduce tech exposure",
        "Sell MSFT 5% in 2 weeks",
        "Is shorting Apple 4% after 3 days worth it?",
        "Add $5000 to GOOGL",
    ]
    
    print("=" * 60)
    print("INTENT PARSER TEST")
    print("=" * 60)
    
    for text in test_inputs:
        print(f"\nInput: {text}")
        decision = parse_decision(text)
        print(f"  Type: {decision.decision_type.value}")
        print(f"  Actions: {len(decision.actions)}")
        for action in decision.actions:
            delay = action.timing.get_execution_offset_days()
            delay_str = f" (T+{delay}d)" if delay > 0 else ""
            print(f"    - {action.direction.value} {action.symbol} {action.size_percent or action.size_usd or '?'}{'%' if action.size_percent else ''}{delay_str}")
        print(f"  Confidence: {decision.confidence_score:.2f}")
        if decision.warnings:
            print(f"  Warnings: {decision.warnings}")
