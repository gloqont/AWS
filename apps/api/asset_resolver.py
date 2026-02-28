"""
Canonical Asset Resolver for GLOQONT

This module implements a strict asset identity resolver that ensures:
1. Assets are never confused with verbs/actions
2. All assets have canonical identifiers
3. Proper country/sector classification
4. International ticker support (including Indian NSE/Nifty 50 and crypto)
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
import yfinance as yf


@dataclass
class AssetInfo:
    """Canonical representation of an asset"""
    symbol: str
    name: str
    country: str
    sector: str
    asset_type: str  # STOCK, ETF, CRYPTO, etc.
    is_valid: bool = True
    currency: str = "USD"  # Trading currency (USD, INR, GBP, EUR, etc.)


# Derive currency from ticker suffix
TICKER_SUFFIX_CURRENCY = {
    ".NS": "INR", ".BO": "INR",  # India (NSE/BSE)
    ".L": "GBP", ".IL": "GBP",  # London
    ".TO": "CAD", ".V": "CAD",   # Canada (TSX/TSXV)
    ".AX": "AUD",                # Australia
    ".T": "JPY",                 # Japan (Tokyo)
    ".HK": "HKD",               # Hong Kong
    ".SI": "SGD",               # Singapore
    ".DE": "EUR", ".PA": "EUR", ".AS": "EUR", ".MI": "EUR",  # Europe
}

COUNTRY_CURRENCY_MAP = {
    "India": "INR", "Canada": "CAD", "United Kingdom": "GBP",
    "Australia": "AUD", "Japan": "JPY", "Singapore": "SGD",
    "Hong Kong": "HKD", "Germany": "EUR", "France": "EUR", 
    "Netherlands": "EUR", "Italy": "EUR", "China": "CNY",
}

def _currency_from_symbol(symbol: str, country: str = "") -> str:
    """Derive trading currency from ticker suffix, with country fallback."""
    for suffix, currency in TICKER_SUFFIX_CURRENCY.items():
        if symbol.upper().endswith(suffix):
            return currency
    # Fallback: if country is known (e.g. from Nifty 50 dict), use that
    if country and country in COUNTRY_CURRENCY_MAP:
        return COUNTRY_CURRENCY_MAP[country]
    return "USD"


class CanonicalAssetResolver:
    """Resolves asset identities with strict validation"""
    
    def __init__(self):
        # Nifty 50 companies with their sectors and countries
        self.nifty_50_symbols = {
            'RELIANCE.NS': {'name': 'Reliance Industries Limited', 'sector': 'Energy', 'country': 'India'},
            'TCS.NS': {'name': 'Tata Consultancy Services Limited', 'sector': 'Technology', 'country': 'India'},
            'HDFCBANK.NS': {'name': 'HDFC Bank Limited', 'sector': 'Financial Services', 'country': 'India'},
            'INFY.NS': {'name': 'Infosys Limited', 'sector': 'Technology', 'country': 'India'},
            'HINDUNILVR.NS': {'name': 'Hindustan Unilever Limited', 'sector': 'Consumer Defensive', 'country': 'India'},
            'ICICIBANK.NS': {'name': 'ICICI Bank Limited', 'sector': 'Financial Services', 'country': 'India'},
            'SBIN.NS': {'name': 'State Bank of India', 'sector': 'Financial Services', 'country': 'India'},
            'BHARTIARTL.NS': {'name': 'Bharti Airtel Limited', 'sector': 'Communication Services', 'country': 'India'},
            'ITC.NS': {'name': 'ITC Limited', 'sector': 'Consumer Defensive', 'country': 'India'},
            'KOTAKBANK.NS': {'name': 'Kotak Mahindra Bank Limited', 'sector': 'Financial Services', 'country': 'India'},
            'LT.NS': {'name': 'Larsen & Toubro Limited', 'sector': 'Industrials', 'country': 'India'},
            'ASIANPAINT.NS': {'name': 'Asian Paints Limited', 'sector': 'Consumer Cyclical', 'country': 'India'},
            'AXISBANK.NS': {'name': 'Axis Bank Limited', 'sector': 'Financial Services', 'country': 'India'},
            'MARUTI.NS': {'name': 'Maruti Suzuki India Limited', 'sector': 'Consumer Cyclical', 'country': 'India'},
            'SUNPHARMA.NS': {'name': 'Sun Pharmaceutical Industries Limited', 'sector': 'Healthcare', 'country': 'India'},
            'TITAN.NS': {'name': 'Titan Company Limited', 'sector': 'Consumer Cyclical', 'country': 'India'},
            'ULTRACEMCO.NS': {'name': 'UltraTech Cement Limited', 'sector': 'Basic Materials', 'country': 'India'},
            'WIPRO.NS': {'name': 'Wipro Limited', 'sector': 'Technology', 'country': 'India'},
            'NESTLEIND.NS': {'name': 'Nestle India Limited', 'sector': 'Consumer Defensive', 'country': 'India'},
            'HCLTECH.NS': {'name': 'HCL Technologies Limited', 'sector': 'Technology', 'country': 'India'},
            'TATASTEEL.NS': {'name': 'Tata Steel Limited', 'sector': 'Basic Materials', 'country': 'India'},
            'TECHM.NS': {'name': 'Tech Mahindra Limited', 'sector': 'Technology', 'country': 'India'},
            'BAJFINANCE.NS': {'name': 'Bajaj Finance Limited', 'sector': 'Financial Services', 'country': 'India'},
            'M&M.NS': {'name': 'Mahindra & Mahindra Limited', 'sector': 'Consumer Cyclical', 'country': 'India'},
            'ONGC.NS': {'name': 'Oil & Natural Gas Corporation Limited', 'sector': 'Energy', 'country': 'India'},
            'POWERGRID.NS': {'name': 'Power Grid Corporation of India Limited', 'sector': 'Utilities', 'country': 'India'},
            'COALINDIA.NS': {'name': 'Coal India Limited', 'sector': 'Energy', 'country': 'India'},
            'GRASIM.NS': {'name': 'Grasim Industries Limited', 'sector': 'Basic Materials', 'country': 'India'},
            'VEDL.NS': {'name': 'Vedanta Limited', 'sector': 'Basic Materials', 'country': 'India'},
            'JSWSTEEL.NS': {'name': 'JSW Steel Limited', 'sector': 'Basic Materials', 'country': 'India'},
            'APOLLOHOSP.NS': {'name': 'Apollo Hospitals Enterprise Limited', 'sector': 'Healthcare', 'country': 'India'},
            'UPL.NS': {'name': 'UPL Limited', 'sector': 'Agriculture', 'country': 'India'},
            'BPCL.NS': {'name': 'Bharat Petroleum Corporation Limited', 'sector': 'Energy', 'country': 'India'},
            'DIVISLAB.NS': {'name': 'Divi\'s Laboratories Limited', 'sector': 'Healthcare', 'country': 'India'},
            'BRITANNIA.NS': {'name': 'Britannia Industries Limited', 'sector': 'Consumer Defensive', 'country': 'India'},
            'SHREECEM.NS': {'name': 'Shree Cement Limited', 'sector': 'Basic Materials', 'country': 'India'},
            'DRREDDY.NS': {'name': 'Dr. Reddy\'s Laboratories Limited', 'sector': 'Healthcare', 'country': 'India'},
            'TATAMOTORS.NS': {'name': 'Tata Motors Limited', 'sector': 'Consumer Cyclical', 'country': 'India'},
            'BAJAJFINSV.NS': {'name': 'Bajaj Finserv Limited', 'sector': 'Financial Services', 'country': 'India'},
            'EICHERMOT.NS': {'name': 'Eicher Motors Limited', 'sector': 'Consumer Cyclical', 'country': 'India'},
            'INDUSINDBK.NS': {'name': 'IndusInd Bank Limited', 'sector': 'Financial Services', 'country': 'India'},
            'SBILIFE.NS': {'name': 'SBI Life Insurance Company Limited', 'sector': 'Financial Services', 'country': 'India'},
            'HDFCLIFE.NS': {'name': 'HDFC Life Insurance Company Limited', 'sector': 'Financial Services', 'country': 'India'},
            'CIPLA.NS': {'name': 'Cipla Limited', 'sector': 'Healthcare', 'country': 'India'},
            'HEROMOTOCO.NS': {'name': 'Hero MotoCorp Limited', 'sector': 'Consumer Cyclical', 'country': 'India'},
            'IOC.NS': {'name': 'Indian Oil Corporation Limited', 'sector': 'Energy', 'country': 'India'},
            'ADANIPORTS.NS': {'name': 'Adani Ports and Special Economic Zone Limited', 'sector': 'Industrials', 'country': 'India'},
            'GODREJCP.NS': {'name': 'Godrej Consumer Products Limited', 'sector': 'Consumer Defensive', 'country': 'India'},
            'BERGEPAINT.NS': {'name': 'Berger Paints India Limited', 'sector': 'Consumer Cyclical', 'country': 'India'},
            'BAJAJ-AUTO.NS': {'name': 'Bajaj Auto Limited', 'sector': 'Consumer Cyclical', 'country': 'India'},
        }
        
        # Add versions without .NS suffix for convenience
        for symbol, info in list(self.nifty_50_symbols.items()):
            if symbol.endswith('.NS'):
                symbol_no_suffix = symbol.replace('.NS', '')
                self.nifty_50_symbols[symbol_no_suffix] = info
        
        # Major crypto symbols
        self.crypto_symbols = {
            'BTC': {'name': 'Bitcoin', 'sector': 'Cryptocurrency', 'country': 'Global'},
            'ETH': {'name': 'Ethereum', 'sector': 'Cryptocurrency', 'country': 'Global'},
            'BNB': {'name': 'Binance Coin', 'sector': 'Cryptocurrency', 'country': 'Global'},
            'ADA': {'name': 'Cardano', 'sector': 'Cryptocurrency', 'country': 'Global'},
            'XRP': {'name': 'Ripple', 'sector': 'Cryptocurrency', 'country': 'Global'},
            'DOGE': {'name': 'Dogecoin', 'sector': 'Cryptocurrency', 'country': 'Global'},
            'DOT': {'name': 'Polkadot', 'sector': 'Cryptocurrency', 'country': 'Global'},
            'AVAX': {'name': 'Avalanche', 'sector': 'Cryptocurrency', 'country': 'Global'},
            'SOL': {'name': 'Solana', 'sector': 'Cryptocurrency', 'country': 'Global'},
            'MATIC': {'name': 'Polygon', 'sector': 'Cryptocurrency', 'country': 'Global'},
            'LINK': {'name': 'Chainlink', 'sector': 'Cryptocurrency', 'country': 'Global'},
            'LTC': {'name': 'Litecoin', 'sector': 'Cryptocurrency', 'country': 'Global'},
            'UNI': {'name': 'Uniswap', 'sector': 'Cryptocurrency', 'country': 'Global'},
            'ATOM': {'name': 'Cosmos', 'sector': 'Cryptocurrency', 'country': 'Global'},
            'XMR': {'name': 'Monero', 'sector': 'Cryptocurrency', 'country': 'Global'},
        }
        
        # Major US stocks
        self.us_symbols = {
            'AAPL': {'name': 'Apple Inc.', 'sector': 'Technology', 'country': 'USA'},
            'MSFT': {'name': 'Microsoft Corporation', 'sector': 'Technology', 'country': 'USA'},
            'GOOGL': {'name': 'Alphabet Inc.', 'sector': 'Communication Services', 'country': 'USA'},
            'AMZN': {'name': 'Amazon.com Inc.', 'sector': 'Consumer Cyclical', 'country': 'USA'},
            'TSLA': {'name': 'Tesla Inc.', 'sector': 'Consumer Cyclical', 'country': 'USA'},
            'NVDA': {'name': 'NVIDIA Corporation', 'sector': 'Technology', 'country': 'USA'},
            'META': {'name': 'Meta Platforms Inc.', 'sector': 'Communication Services', 'country': 'USA'},
            'NFLX': {'name': 'Netflix Inc.', 'sector': 'Communication Services', 'country': 'USA'},
            'JPM': {'name': 'JPMorgan Chase & Co.', 'sector': 'Financial Services', 'country': 'USA'},
            'JNJ': {'name': 'Johnson & Johnson', 'sector': 'Healthcare', 'country': 'USA'},
            'V': {'name': 'Visa Inc.', 'sector': 'Financial Services', 'country': 'USA'},
            'WMT': {'name': 'Walmart Inc.', 'sector': 'Consumer Defensive', 'country': 'USA'},
            'PG': {'name': 'Procter & Gamble Co.', 'sector': 'Consumer Defensive', 'country': 'USA'},
            'DIS': {'name': 'The Walt Disney Company', 'sector': 'Communication Services', 'country': 'USA'},
            'MA': {'name': 'Mastercard Incorporated', 'sector': 'Financial Services', 'country': 'USA'},
        }

    def resolve_asset(self, symbol: str) -> Optional[AssetInfo]:
        """
        Resolve an asset symbol to its canonical representation.
        
        Args:
            symbol: The symbol to resolve (may include suffixes like .NS, .BO)
            
        Returns:
            AssetInfo object or None if not found
        """
        if not symbol or not isinstance(symbol, str):
            return None
            
        symbol = symbol.strip().upper()
        
        # Check if this looks like a verb/action rather than an asset
        if self._is_action_word(symbol):
            return None
            
        # Check in Nifty 50 first (includes .NS and no-suffix versions)
        if symbol in self.nifty_50_symbols:
            info = self.nifty_50_symbols[symbol]
            return AssetInfo(
                symbol=symbol,
                name=info['name'],
                country=info['country'],
                sector=info['sector'],
                asset_type='STOCK',
                currency=_currency_from_symbol(symbol, info['country'])
            )
        
        # Check in crypto symbols
        if symbol in self.crypto_symbols:
            info = self.crypto_symbols[symbol]
            return AssetInfo(
                symbol=symbol,
                name=info['name'],
                country=info['country'],
                sector=info['sector'],
                asset_type='CRYPTO',
                currency='USD'
            )
        
        # Check in US symbols
        if symbol in self.us_symbols:
            info = self.us_symbols[symbol]
            return AssetInfo(
                symbol=symbol,
                name=info['name'],
                country=info['country'],
                sector=info['sector'],
                asset_type='STOCK',
                currency='USD'
            )
        
        # Try to validate with yfinance as a fallback
        try:
            ticker = yf.Ticker(symbol)
            
            # optimizations: try fast_info first as it's faster and often sufficient for existence check
            # ignoring the specific details if we just want to support "everything"
            try:
                # fast_info is usually available even if full 'info' is not
                last_price = ticker.fast_info.get('lastPrice')
                if last_price is not None:
                    # It has a price, so it exists.
                    # Try to get more metadata if possible, but don't fail if we can't
                    long_name = symbol
                    country = 'Global'
                    sector = 'Unknown'
                    asset_type = 'STOCK' # Default
                    
                    # Try to get better metadata from info, but don't block on it
                    try:
                        info = ticker.info
                        if info:
                            long_name = info.get('longName', info.get('shortName', symbol))
                            country = info.get('country', 'Global')
                            sector = info.get('sector', 'Unknown')
                            quote_type = info.get('quoteType', 'EQUITY').upper()
                            if quote_type in ['CRYPTOCURRENCY']:
                                asset_type = 'CRYPTO'
                            elif quote_type in ['ETF', 'MUTUALFUND']:
                                asset_type = quote_type
                    except:
                        pass
                        
                    return AssetInfo(
                        symbol=symbol,
                        name=long_name,
                        country=country,
                        sector=sector,
                        asset_type=asset_type,
                        currency=_currency_from_symbol(symbol)
                    )
            except:
                # fast_info access failed, fall back to history check
                pass

            # Fallback: check history if fast_info didn't work (some edge cases)
            hist = ticker.history(period="1d")
            if not hist.empty:
                 # It has history, so it exists
                return AssetInfo(
                    symbol=symbol,
                    name=symbol,
                    country='Global',
                    sector='Unknown',
                    asset_type='STOCK',
                    currency=_currency_from_symbol(symbol)
                )

        except Exception:
            # If yfinance allows it, we want it, but if it crashes, we can't do much
            pass
            
        return None
    
    def _is_action_word(self, symbol: str) -> bool:
        """
        Check if the symbol looks like an action/verb rather than an asset.
        
        Args:
            symbol: Symbol to check
            
        Returns:
            True if it appears to be an action word
        """
        action_words = {
            'BUY', 'SELL', 'TRADE', 'HOLD', 'INCREASE', 'DECREASE', 'ADD', 'REMOVE',
            'LONG', 'SHORT', 'PUT', 'CALL', 'OPTIONS', 'SWAP', 'EXCHANGE', 'TRANSFER',
            'PURCHASE', 'ACQUIRE', 'LIQUIDATE', 'REBALANCE', 'ALLOCATE', 'DIVERSIFY',
            'HEDGE', 'PROTECT', 'SPECULATE', 'MARGIN', 'LEVERAGE', 'COVER'
        }
        return symbol in action_words
    
    def extract_assets_from_text(self, text: str) -> List[AssetInfo]:
        """
        Extract asset symbols from decision text and resolve them canonically.
        
        Args:
            text: The decision text to parse
            
        Returns:
            List of resolved AssetInfo objects
        """
        if not text:
            return []
        
        text_upper = text.upper()
        found_assets = []
        
        # Look for common ticker patterns (2-5 uppercase letters, possibly with suffixes)
        # Fixed to ensure the first part is actual letters, not dots
        ticker_pattern = r'\b([A-Z]{2,5}(?:\.[A-Z]{1,3})?)\b'
        matches = re.findall(ticker_pattern, text_upper)
        
        for match in matches:
            asset_info = self.resolve_asset(match)
            if asset_info and asset_info.is_valid:
                # Avoid duplicates
                if not any(a.symbol == asset_info.symbol for a in found_assets):
                    found_assets.append(asset_info)
        
        # Also check for common company names that might not be in ticker format
        company_names = {
            'APPLE': 'AAPL',
            'MICROSOFT': 'MSFT', 
            'GOOGLE': 'GOOGL',
            'ALPHABET': 'GOOGL',
            'AMAZON': 'AMZN',
            'TESLA': 'TSLA',
            'NVIDIA': 'NVDA',
            'META': 'META',
            'FACEBOOK': 'META',
            'NETFLIX': 'NFLX',
            'RELIANCE': 'RELIANCE.NS',
            'TCS': 'TCS.NS',
            'INFOSYS': 'INFY.NS',
            'HDFC BANK': 'HDFCBANK.NS',
            'ICICI BANK': 'ICICIBANK.NS',
            'STATE BANK OF INDIA': 'SBIN.NS',
            'BHARTI AIRTEL': 'BHARTIARTL.NS',
            'HINDUSTAN UNILEVER': 'HINDUNILVR.NS',
            'ITC': 'ITC.NS',
            'KOTAK MAHINDRA': 'KOTAKBANK.NS',
            'LARSEN AND TOUBRO': 'LT.NS',
            'ASIAN PAINTS': 'ASIANPAINT.NS',
            'AXIS BANK': 'AXISBANK.NS',
            'MARUTI SUZUKI': 'MARUTI.NS',
            'SUN PHARMACEUTICAL': 'SUNPHARMA.NS',
            'TITAN COMPANY': 'TITAN.NS',
            'ULTRATECH CEMENT': 'ULTRACEMCO.NS',
            'WIPRO': 'WIPRO.NS',
            'NESTLE INDIA': 'NESTLEIND.NS',
            'HCL TECHNOLOGIES': 'HCLTECH.NS',
            'TATA STEEL': 'TATASTEEL.NS',
            'TECH MAHINDRA': 'TECHM.NS',
            'BAJAJ FINANCE': 'BAJFINANCE.NS',
            'MAHINDRA AND MAHINDRA': 'M&M.NS',
            'OIL AND NATURAL GAS': 'ONGC.NS',
            'POWER GRID': 'POWERGRID.NS',
            'COAL INDIA': 'COALINDIA.NS',
            'GRASIM': 'GRASIM.NS',
            'VEDANTA': 'VEDL.NS',
            'JSW STEEL': 'JSWSTEEL.NS',
            'APOLLO HOSPITALS': 'APOLLOHOSP.NS',
            'UPL': 'UPL.NS',
            'BHARAT PETROLEUM': 'BPCL.NS',
            'DIVIS LABORATORIES': 'DIVISLAB.NS',
            'BRITANNIA': 'BRITANNIA.NS',
            'SHREE CEMENT': 'SHREECEM.NS',
            'DR REDDYS': 'DRREDDY.NS',
            'TATA MOTORS': 'TATAMOTORS.NS',
            'BAJAJ FINSERV': 'BAJAJFINSV.NS',
            'EICHER MOTORS': 'EICHERMOT.NS',
            'INDUSIND BANK': 'INDUSINDBK.NS',
            'SBI LIFE': 'SBILIFE.NS',
            'HDFC LIFE': 'HDFCLIFE.NS',
            'CIPLA': 'CIPLA.NS',
            'HERO MOTOCORP': 'HEROMOTOCO.NS',
            'INDIAN OIL': 'IOC.NS',
            'ADANI PORTS': 'ADANIPORTS.NS',
            'GODREJ CONSUMER': 'GODREJCP.NS',
            'BERGER PAINTS': 'BERGEPAINT.NS',
            'BAJAJ AUTO': 'BAJAJ-AUTO.NS',
        }
        
        text_words = text_upper.split()
        for i, word in enumerate(text_words):
            # Check for company name patterns
            for company_name, ticker in company_names.items():
                if company_name.replace(' ', '') in word or company_name.replace(' ', '_') in word:
                    asset_info = self.resolve_asset(ticker)
                    if asset_info and asset_info.is_valid:
                        if not any(a.symbol == asset_info.symbol for a in found_assets):
                            found_assets.append(asset_info)
        
        return found_assets
    
    def validate_decision_structure(self, decision_text: str) -> Tuple[str, str, Decimal]:
        """
        Parse user decisions into a strict structured form.

        Args:
            decision_text: The raw decision text

        Returns:
            Tuple of (action, asset_symbol, allocation_change_pct)
        """
        decision_text = decision_text.strip().lower()

        # Extract multiple asset-action pairs from the decision text
        multiple_actions = self._parse_multiple_actions(decision_text)

        if multiple_actions:
            # If multiple actions are found, return the first one for backward compatibility
            # But we'll also store all actions for more complex processing
            first_action = multiple_actions[0]
            action, asset_symbol, allocation_change_pct = first_action
            return action, asset_symbol, allocation_change_pct
        else:
            # Original logic for single action
            # Determine action - handle compound phrases like "sell or short"
            if any(word in decision_text for word in ['buy', 'increase', 'add', 'purchase', 'invest', 'long']):
                action = 'buy'
            elif any(word in decision_text for word in ['sell', 'decrease', 'reduce', 'trim', 'remove', 'short']):
                action = 'sell'
            else:
                action = 'rebalance'  # Default action

            # Extract asset symbol
            asset_symbol = None
            assets = self.extract_assets_from_text(decision_text)
            if assets:
                asset_symbol = assets[0].symbol  # Use the first asset found
            else:
                # If no specific asset found, try to extract from common patterns
                # Look for patterns like "sell AAPL", "buy TSLA", etc.
                ticker_pattern = r'\b([A-Z]{2,5}(?:\.[A-Z]{1,3})?)\b'
                matches = re.findall(ticker_pattern, decision_text.upper())
                if matches:
                    # Check if the match is not an action word
                    for match in matches:
                        if not self._is_action_word(match):
                            asset_symbol = match
                            break

            # Extract percentage change
            percent_pattern = r'(\d+\.?\d*)\s*(?:%|percent|pct)'
            percent_match = re.search(percent_pattern, decision_text)
            allocation_change_pct = Decimal('0.0')

            if percent_match:
                try:
                    allocation_change_pct = Decimal(percent_match.group(1)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                except:
                    allocation_change_pct = Decimal('0.0')

            # If no percentage found, try to infer from common phrases
            if allocation_change_pct == Decimal('0.0'):
                # Look for common phrases like "small amount", "large position", etc.
                if any(phrase in decision_text for phrase in ['small', 'little', 'tiny']):
                    allocation_change_pct = Decimal('1.0')
                elif any(phrase in decision_text for phrase in ['medium', 'moderate', 'average']):
                    allocation_change_pct = Decimal('5.0')
                elif any(phrase in decision_text for phrase in ['large', 'big', 'significant']):
                    allocation_change_pct = Decimal('10.0')
                elif any(phrase in decision_text for phrase in ['huge', 'massive', 'substantial']):
                    allocation_change_pct = Decimal('20.0')
                else:
                    # Default allocation change for general statements
                    allocation_change_pct = Decimal('5.0')

            # For sell actions, make the percentage negative
            if action == 'sell':
                allocation_change_pct = -abs(allocation_change_pct)

            # Ensure allocation_change_pct is always a Decimal, even if it's zero
            if allocation_change_pct is None or allocation_change_pct == Decimal('0.0'):
                # Default to 5% for general sell statements without specific amounts
                allocation_change_pct = Decimal('-5.0') if action == 'sell' else Decimal('5.0')

            return action, asset_symbol or 'UNKNOWN', allocation_change_pct

    def _parse_multiple_actions(self, decision_text: str) -> List[Tuple[str, str, Decimal]]:
        """
        Parse multiple buy/sell actions from a single decision text.

        Args:
            decision_text: The raw decision text

        Returns:
            List of tuples (action, asset_symbol, allocation_change_pct)
        """
        decision_text = decision_text.strip()
        actions = []

        import re

        # First, let's try to find all action-asset-percent combinations in the text
        # Pattern: (buy|sell|etc) (asset) (number)(optional %)
        # Handle various formats like "Buy AAPL 3%", "buy aapl 3 percent", etc.

        # Pattern 1: action asset number% (e.g., "Buy AAPL 3%")
        pattern1 = r'(buy|sell|short|long|increase|decrease|add|reduce)\s+([A-Z]{1,5}(?:\.[A-Z]{1,3})?)\s+(\d+(?:\.\d+)?)\s*(?:%|percent|pct)?'
        matches1 = re.findall(pattern1, decision_text, re.IGNORECASE)

        # Pattern 2: action number% asset (e.g., "Buy 3% AAPL")
        pattern2 = r'(buy|sell|short|long|increase|decrease|add|reduce)\s+(\d+(?:\.\d+)?)\s*(?:%|percent|pct)?\s+([A-Z]{1,5}(?:\.[A-Z]{1,3})?)'
        matches2 = re.findall(pattern2, decision_text, re.IGNORECASE)

        # Pattern 3: action asset by number% (e.g., "Buy AAPL by 3%")
        pattern3 = r'(buy|sell|short|long|increase|decrease|add|reduce)\s+([A-Z]{1,5}(?:\.[A-Z]{1,3})?)\s+(?:up\s+to\s+|by\s+)?(\d+(?:\.\d+)?)\s*(?:%|percent|pct)?'
        matches3 = re.findall(pattern3, decision_text, re.IGNORECASE)

        # Combine all matches
        matches = matches1 + matches2 + matches3

        # Swap asset and pct positions for pattern2 matches (since asset was in 3rd position)
        final_matches = []
        for match in matches1 + matches3:
            final_matches.append(match)  # These are already in (action, asset, pct) format
        for action, pct, asset in matches2:
            final_matches.append((action, asset, pct))  # Reorder to (action, asset, pct)

        for action, asset, pct_str in final_matches:
            # Convert percentage string to Decimal
            if pct_str:
                pct = Decimal(pct_str)
            else:
                # Use default percentage based on action type
                pct = self._extract_default_percentage(action)

            # Validate asset exists
            asset_info = self.resolve_asset(asset)
            if asset_info and asset_info.is_valid:
                # For sell actions, make percentage negative
                if action.lower() in ['sell', 'decrease', 'reduce', 'short']:
                    pct = -abs(pct)

                # Only add if not already in the list (avoid duplicates)
                if not any(a[1] == asset_info.symbol and a[0] == action.lower() for a in actions):
                    actions.append((action.lower(), asset_info.symbol, pct.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)))

        return actions

    def _extract_default_percentage(self, action: str) -> Decimal:
        """
        Extract a default percentage based on the action type.

        Args:
            action: The action word (buy, sell, etc.)

        Returns:
            Decimal percentage value
        """
        # Default allocation based on action
        if 'sell' in action.lower() or 'reduce' in action.lower():
            return Decimal('5.0')  # Default 5% for sell actions
        else:
            return Decimal('5.0')  # Default 5% for buy actions

    def _extract_percentage_for_asset(self, decision_text: str, action: str, asset: str) -> Decimal:
        """
        Extract the percentage associated with a specific action-asset pair in the text.

        Args:
            decision_text: The full decision text
            action: The action word (buy, sell, etc.)
            asset: The asset symbol

        Returns:
            Decimal percentage value
        """
        # Look for patterns like "buy AAPL 5%" or "sell MSFT 3%"
        import re

        # Search for the specific action-asset combination and its associated percentage
        pattern = rf'{action}\s+{asset}\s+(\d+(?:\.\d+)?)\s*(?:%|percent|pct)?'
        match = re.search(pattern, decision_text, re.IGNORECASE)

        if match:
            return Decimal(match.group(1)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        else:
            # If no specific percentage found, use default based on action
            if 'small' in decision_text or 'little' in decision_text:
                return Decimal('1.0')
            elif 'medium' in decision_text or 'moderate' in decision_text:
                return Decimal('5.0')
            elif 'large' in decision_text or 'big' in decision_text:
                return Decimal('10.0')
            elif 'huge' in decision_text or 'massive' in decision_text:
                return Decimal('20.0')
            else:
                # Default allocation change
                return Decimal('5.0')


# Global instance
ASSET_RESOLVER = CanonicalAssetResolver()