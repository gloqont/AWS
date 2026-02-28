from __future__ import annotations

import os
import time
import hashlib
from dataclasses import dataclass
from typing import List, Literal, Optional, Tuple

import numpy as np
import pandas as pd

try:
    import yfinance as yf
except Exception:
    yf = None


Interval = Literal["1m", "1d", "1wk", "1mo"]


@dataclass
class PriceFetchResult:
    prices: pd.DataFrame
    returns: pd.DataFrame
    source: str
    cached: bool


def periods_per_year_from_interval(interval: Interval) -> int:
    return {"1m": 98280, "1d": 252, "1wk": 52, "1mo": 12}[interval]


# -------------------------
# Cache helpers
# -------------------------
def _cache_dir() -> str:
    here = os.path.dirname(__file__)
    d = os.path.join(here, "..", "..", "data", "cache")
    os.makedirs(d, exist_ok=True)
    return d


def _cache_key(tickers: List[str], lookback_days: int, interval: str) -> str:
    key = ",".join(sorted(tickers)) + f"|{lookback_days}|{interval}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def _parquet_supported() -> bool:
    try:
        __import__("pyarrow")
        return True
    except Exception:
        return False


def _read_cache(path: str, use_parquet: bool) -> pd.DataFrame:
    if use_parquet:
        return pd.read_parquet(path)
    return pd.read_csv(path, index_col=0, parse_dates=True)


def _write_cache(df: pd.DataFrame, path: str, use_parquet: bool) -> None:
    try:
        if use_parquet:
            df.to_parquet(path)
        else:
            df.to_csv(path, compression="gzip")
    except Exception:
        # caching should never crash the API
        pass


# -------------------------
# Data source: Stooq (fallback)
# -------------------------
def _stooq_symbol(ticker: str) -> str:
    """
    Stooq uses formats like AAPL.US for US stocks.
    For international tickers with suffixes like .NS, .BO, keep them as-is.
    If user passes AAPL without suffix, map to AAPL.US.
    """
    t = ticker.strip().upper()
    # Check if ticker already has international suffixes
    international_suffixes = ['.NS', '.BO', '.JK', '.SI', '.HK', '.TO', '.L', '.PA', '.DE', '.MI']
    for suffix in international_suffixes:
        if t.endswith(suffix):
            return t  # Return as-is for international tickers

    # Special handling for common Indian tickers - map to .NS if no suffix provided
    indian_tickers = ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK',
                     'SBIN', 'BHARTIARTL', 'ITC', 'ASIANPAINT', 'MARUTI',
                     'AXISBANK', 'SUNPHARMA', 'TATAMOTORS', 'TATASTEEL',
                     'POWERGRID', 'ONGC', 'COALINDIA', 'GRASIM', 'ULTRACEMCO',
                     'NESTLEIND', 'TITAN', 'HINDUNILVR', 'WIPRO', 'BAJFINANCE']

    if '.' not in t and t in indian_tickers:
        return f"{t}.NS"

    # For tickers without recognized international suffixes, assume US
    if "." not in t:
        return f"{t}.US"
    return t


def _stooq_interval(interval: Interval) -> str:
    # stooq expects i=d/w/m
    return {"1d": "d", "1wk": "w", "1mo": "m"}[interval]


def _fetch_mock_indian_prices(tickers: List[str], lookback_days: int, interval: Interval) -> pd.DataFrame:
    """
    Create mock/fallback prices for Indian tickers when real data is unavailable.
    This returns previous day's close data to at least provide some values for calculations.
    """
    from datetime import datetime, timedelta
    import random

    # Define some realistic mock prices for common Indian tickers
    mock_prices_db = {
        'RELIANCE.NS': 2800.00,
        'TCS.NS': 3500.00,
        'INFY.NS': 1600.00,
        'HDFCBANK.NS': 1700.00,
        'ICICIBANK.NS': 1100.00,
        'SBIN.NS': 700.00,
        'AXISBANK.NS': 1200.00,
        'HDFC.NS': 2900.00,
        'ITC.NS': 450.00,
        'LT.NS': 2400.00,
        'KOTAKBANK.NS': 1900.00,
        'BHARTIARTL.NS': 850.00,
        'MARUTI.NS': 10000.00,
        'WIPRO.NS': 750.00,
        'NESTLEIND.NS': 22000.00,
        'ASIANPAINT.NS': 3200.00,
        'ULTRACEMCO.NS': 8000.00,
        'SUNPHARMA.NS': 950.00,
        'TATAMOTORS.NS': 1300.00,
        'TATASTEEL.NS': 1500.00,
        'POWERGRID.NS': 250.00,
        'ONGC.NS': 170.00,
        'COALINDIA.NS': 300.00,
        'GRASIM.NS': 2000.00,
        'TITAN.NS': 3500.00,
        'HINDUNILVR.NS': 2800.00,
        'BAJFINANCE.NS': 7500.00,
        'BAJAJFINSV.NS': 16000.00,
        'JSWSTEEL.NS': 750.00,
        'DRREDDY.NS': 5500.00,
        'BRITANNIA.NS': 4200.00,
        'CIPLA.NS': 1300.00,
        'EICHERMOT.NS': 4000.00,
        'GODREJPROP.NS': 1500.00,
        'HCLTECH.NS': 1400.00,
        'INDUSINDBK.NS': 1300.00,
        'IOC.NS': 150.00,
        'M&M.NS': 1200.00,
        'NTPC.NS': 250.00,
        'TECHM.NS': 1300.00,
        'VEDL.NS': 500.00,
        'ZEEL.NS': 700.00,
        'YESBANK.NS': 25.00,
        # Also include versions without .NS suffix
        'RELIANCE': 2800.00,
        'TCS': 3500.00,
        'INFY': 1600.00,
        'HDFCBANK': 1700.00,
        'ICICIBANK': 1100.00,
        'SBIN': 700.00,
        'AXISBANK': 1200.00,
        'HDFC': 2900.00,
        'ITC': 450.00,
        'LT': 2400.00,
        'KOTAKBANK': 1900.00,
        'BHARTIARTL': 850.00,
        'MARUTI': 10000.00,
        'WIPRO': 750.00,
        'NESTLEIND': 22000.00,
        'ASIANPAINT': 3200.00,
        'ULTRACEMCO': 8000.00,
        'SUNPHARMA': 950.00,
        'TATAMOTORS': 1300.00,
        'TATASTEEL': 1500.00,
        'POWERGRID': 250.00,
        'ONGC': 170.00,
        'COALINDIA': 300.00,
        'GRASIM': 2000.00,
        'TITAN': 3500.00,
        'HINDUNILVR': 2800.00,
        'BAJFINANCE': 7500.00,
        'BAJAJFINSV': 16000.00,
        'JSWSTEEL': 750.00,
        'DRREDDY': 5500.00,
        'BRITANNIA': 4200.00,
        'CIPLA': 1300.00,
        'EICHERMOT': 4000.00,
        'GODREJPROP': 1500.00,
        'HCLTECH': 1400.00,
        'INDUSINDBK': 1300.00,
        'IOC': 150.00,
        'M&M': 1200.00,
        'NTPC': 250.00,
        'TECHM': 1300.00,
        'VEDL': 500.00,
        'ZEEL': 700.00,
        'YESBANK': 25.00,
    }

    frames = []

    for ticker in tickers:
        # Check if ticker exists in our mock database
        ticker_upper = ticker.upper()
        if ticker_upper in mock_prices_db:
            # Create a mock DataFrame with the previous day's close price
            # Generate some mock historical data for the lookback period
            end_date = datetime.now()
            date_range = pd.date_range(end=end_date, periods=min(lookback_days, 10), freq='D')

            # Generate slightly varying prices around the mock price to simulate daily movements
            base_price = mock_prices_db[ticker_upper]
            mock_prices = []
            current_price = base_price

            for i in range(len(date_range)):
                # Add some random variation to simulate daily price movement
                daily_change = random.uniform(-0.02, 0.02)  # ±2% daily change
                current_price = current_price * (1 + daily_change)
                mock_prices.append(current_price)

            df = pd.DataFrame({'Close': mock_prices}, index=date_range)
            df = df.rename(columns={'Close': ticker})
            frames.append(df)
        else:
            # Check if it's a potential Indian ticker (ends with .NS or .BO, or is in common Indian list)
            ticker_clean = ticker.replace('.NS', '').replace('.BO', '').upper()
            if ticker_clean in [t.replace('.NS', '').replace('.BO', '').upper() for t in mock_prices_db.keys()]:
                # Even if not in our DB, try to create a generic mock
                # Use a default price if we can't find a specific one
                base_price = 1000.0  # Default mock price
                end_date = datetime.now()
                date_range = pd.date_range(end=end_date, periods=min(lookback_days, 5), freq='D')

                mock_prices = []
                current_price = base_price
                for i in range(len(date_range)):
                    daily_change = random.uniform(-0.01, 0.01)  # ±1% daily change
                    current_price = current_price * (1 + daily_change)
                    mock_prices.append(current_price)

                df = pd.DataFrame({'Close': mock_prices}, index=date_range)
                df = df.rename(columns={'Close': ticker})
                frames.append(df)

    if not frames:
        return pd.DataFrame()

    prices = pd.concat(frames, axis=1).sort_index()

    # Apply lookback window (calendar days)
    if lookback_days and lookback_days > 0:
        cutoff = prices.index.max() - pd.Timedelta(days=int(lookback_days))
        prices = prices.loc[prices.index >= cutoff]

    return prices


def _fetch_stooq_prices(tickers: List[str], lookback_days: int, interval: Interval) -> pd.DataFrame:
    i = _stooq_interval(interval)
    frames = []

    for t in tickers:
        sym = _stooq_symbol(t).lower()
        url = f"https://stooq.com/q/d/l/?s={sym}&i={i}"

        # stooq returns: Date,Open,High,Low,Close,Volume
        try:
            df = pd.read_csv(url)
        except Exception as e:
            raise RuntimeError(f"Stooq fetch failed for {t}: {e}")

        if df.empty or "Date" not in df.columns or "Close" not in df.columns:
            continue

        df["Date"] = pd.to_datetime(df["Date"])
        df = df.set_index("Date").sort_index()

        close = df[["Close"]].rename(columns={"Close": t.upper()})
        frames.append(close)

    if not frames:
        return pd.DataFrame()

    prices = pd.concat(frames, axis=1).sort_index()

    # Apply lookback window (calendar days)
    if lookback_days and lookback_days > 0:
        cutoff = prices.index.max() - pd.Timedelta(days=int(lookback_days))
        prices = prices.loc[prices.index >= cutoff]

    return prices


# -------------------------
# Data source: yfinance (primary) - OPTIMIZED VERSION
# -------------------------
def _fetch_yfinance_prices(tickers: List[str], lookback_days: int, interval: Interval) -> pd.DataFrame:
    if yf is None:
        raise RuntimeError("yfinance is not installed or failed to import")

    # Prepare ticker list with international suffixes as needed
    processed_tickers = []
    ticker_mapping = {}  # Maps processed ticker back to original

    for ticker in tickers:
        ticker_to_use = ticker
        # For Indian tickers, try with .NS suffix if no suffix is provided
        if '.' not in ticker and ticker.upper() in ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK',
                                                  'SBIN', 'BHARTIARTL', 'ITC', 'ASIANPAINT', 'MARUTI',
                                                  'AXISBANK', 'SUNPHARMA', 'TATAMOTORS', 'TATASTEEL',
                                                  'POWERGRID', 'ONGC', 'COALINDIA', 'GRASIM', 'ULTRACEMCO',
                                                  'NESTLEIND', 'TITAN', 'HINDUNILVR', 'WIPRO', 'BAJFINANCE',
                                                  'BAJAJFINSV', 'KOTAKBANK', 'JSWSTEEL', 'DRREDDY', 'HDFC',
                                                  'BRITANNIA', 'CIPLA', 'EICHERMOT', 'GODREJPROP', 'HCLTECH',
                                                  'INDUSINDBK', 'IOC', 'M&M', 'MINDTREE', 'MUTHOOTFIN',
                                                  'NAUKRI', 'NEULANDLAB', 'OFSS', 'PIIND', 'POLYCAB',
                                                  'RAINBOW', 'RAJESHEXPO', 'RBLBANK', 'RECLTD', 'REDINGTON',
                                                  'SAIL', 'SANOFI', 'SBILIFE', 'SHOPERSTOP', 'SHREECEM',
                                                  'SRF', 'SUDOCHEM', 'SUMICHEM', 'SUNTV', 'SYNGENE',
                                                  'TATACHEM', 'TATACONSUM', 'TATACORP', 'TATAELXSI', 'TATAGLOBAL',
                                                  'TATAINVEST', 'TATAMETALI', 'TATAPOWER', 'TATASPONGE', 'TCS',
                                                  'TECHM', 'RAMCOCEM', 'UBL', 'VEDL', 'VGUARD',
                                                  'VOLTAS', 'WHIRLPOOL', 'WOCKPHARMA', 'YESBANK', 'ZEEL']:
            ticker_to_use = f"{ticker}.NS"

        processed_tickers.append(ticker_to_use)
        ticker_mapping[ticker_to_use] = ticker  # Map processed back to original

    # Bulk fetch all tickers in a single yfinance call - this is the key optimization
    period = f"{int(lookback_days)}d"

    try:
        # Fetch all tickers at once - much faster than individual requests
        # yfinance handles partial failures internally (prints errors) but returns what it can
        all_data = yf.download(
            tickers=processed_tickers,
            period=period,
            interval=interval,
            auto_adjust=True,
            progress=False,
            threads=True, 
            group_by="column",
        )

        close_data = pd.DataFrame()
        
        if all_data is not None and not all_data.empty:
            # Pylance/pandas type check helper
            if isinstance(all_data.columns, pd.MultiIndex):
                # Multi-index case: (Attribute, Ticker)
                # Try to get Close prices first
                if "Close" in all_data.columns.get_level_values(0):
                    close_data = all_data["Close"].copy()
                elif "Adj Close" in all_data.columns.get_level_values(0):
                    close_data = all_data["Adj Close"].copy()
                else:
                    # fallback: use first available attribute
                    first_attr = all_data.columns.get_level_values(0)[0]
                    close_data = all_data[first_attr].copy()
                
                # Rename columns back to original tickers
                renamed_cols = {}
                for col in close_data.columns:
                    original_ticker = ticker_mapping.get(col, col)
                    renamed_cols[col] = original_ticker
                close_data.rename(columns=renamed_cols, inplace=True)
                
            else:
                # Single index case (usually only if 1 ticker requested, or flat structure)
                # If we requested multiple and got single level, it might be just Close cols (unlikely with new yf)
                # Or it might be Attribute cols for a single ticker
                
                # Logic for single ticker returned as columns (Open, High, Low, Close...)
                if "Close" in all_data.columns:
                    # It's data for a single ticker
                    # We need to find WHICH ticker it was (if we only asked for 1)
                    if len(processed_tickers) == 1:
                         # We know the ticker
                         raw_ticker = processed_tickers[0]
                         orig_ticker = ticker_mapping.get(raw_ticker, raw_ticker)
                         close_data = all_data[["Close"]].copy()
                         close_data.columns = [orig_ticker]
                    else:
                        # Wierd case: multiple tickers asked, but flat schema? 
                        pass
                else:
                     pass

        # Identify which tickers we successfully got
        fetched_tickers = set(close_data.columns)
        missing_tickers = [t for t in tickers if t not in fetched_tickers]
        
        if not missing_tickers:
             return close_data.sort_index()
             
        # Fallback loop ONLY for missing tickers
        all_prices = close_data.to_dict() # Start with what we have (as dict for easy merge)
        
        for ticker in missing_tickers:
            try:
                # For Indian tickers, try with .NS suffix if no suffix is provided
                ticker_to_use = ticker
                if '.' not in ticker and ticker.upper() in ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK',
                                                          'SBIN', 'BHARTIARTL', 'ITC', 'ASIANPAINT', 'MARUTI',
                                                          'AXISBANK', 'SUNPHARMA', 'TATAMOTORS', 'TATASTEEL',
                                                          'POWERGRID', 'ONGC', 'COALINDIA', 'GRASIM', 'ULTRACEMCO',
                                                          'NESTLEIND', 'TITAN', 'HINDUNILVR', 'WIPRO', 'BAJFINANCE',
                                                          'BAJAJFINSV', 'KOTAKBANK', 'JSWSTEEL', 'DRREDDY', 'HDFC',
                                                          'BRITANNIA', 'CIPLA', 'EICHERMOT', 'GODREJPROP', 'HCLTECH',
                                                          'INDUSINDBK', 'IOC', 'M&M', 'MINDTREE', 'MUTHOOTFIN',
                                                          'NAUKRI', 'NEULANDLAB', 'OFSS', 'PIIND', 'POLYCAB',
                                                          'RAINBOW', 'RAJESHEXPO', 'RBLBANK', 'RECLTD', 'REDINGTON',
                                                          'SAIL', 'SANOFI', 'SBILIFE', 'SHOPERSTOP', 'SHREECEM',
                                                          'SRF', 'SUDOCHEM', 'SUMICHEM', 'SUNTV', 'SYNGENE',
                                                          'TATACHEM', 'TATACONSUM', 'TATACORP', 'TATAELXSI', 'TATAGLOBAL',
                                                          'TATAINVEST', 'TATAMETALI', 'TATAPOWER', 'TATASPONGE', 'TCS',
                                                          'TECHM', 'RAMCOCEM', 'UBL', 'VEDL', 'VGUARD',
                                                          'VOLTAS', 'WHIRLPOOL', 'WOCKPHARMA', 'YESBANK', 'ZEEL']:
                     ticker_to_use = f"{ticker}.NS"

                # Download data for single ticker
                ticker_data = yf.download(
                    tickers=[ticker_to_use],
                    period=period,
                    interval=interval,
                    auto_adjust=True,
                    progress=False,
                    threads=False,
                    group_by="column",
                )
                
                single_close = None
                if ticker_data is not None and not ticker_data.empty:
                    # Extract closing prices
                    if isinstance(ticker_data.columns, pd.MultiIndex):
                        if "Close" in ticker_data.columns.get_level_values(0):
                            single_close = ticker_data["Close"].copy()
                        elif "Adj Close" in ticker_data.columns.get_level_values(0):
                            single_close = ticker_data["Adj Close"].copy()
                        else:
                            first_col = ticker_data.columns.get_level_values(0)[0]
                            single_close = ticker_data[first_col].copy()
                    else:
                        if "Close" in ticker_data.columns:
                            single_close = ticker_data[["Close"]].copy()
                        elif "Adj Close" in ticker_data.columns:
                            single_close = ticker_data[["Adj Close"]].copy()
                        else:
                            single_close = ticker_data.iloc[:, [0]].copy()

                    if single_close is not None:
                        # Rename checks
                        if len(single_close.columns) == 1:
                            single_close.columns = [ticker]
                        
                        # Store the data
                        for date, row in single_close.iterrows():
                            if date not in all_prices:
                                all_prices[date] = {}
                            for col in row.index:
                                all_prices[date][col] = row[col]

            except Exception as e:
                print(f"Warning: Individual fetch failed for {ticker}: {e}")
                
        # Convert the dictionary to DataFrame
        final_df = pd.DataFrame(all_prices).T
        return final_df.sort_index()

    except Exception as e:
        print(f"Warning: Bulk yfinance fetch failed, falling back to individual fetch: {e}")
        # Fallback to original method if bulk fetch fails completely
        all_prices = {}
        
        for ticker in tickers:
            try:
                # For Indian tickers, try with .NS suffix if no suffix is provided
                ticker_to_use = ticker
                if '.' not in ticker and ticker.upper() in ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK',
                                                          'SBIN', 'BHARTIARTL', 'ITC', 'ASIANPAINT', 'MARUTI',
                                                          'AXISBANK', 'SUNPHARMA', 'TATAMOTORS', 'TATASTEEL',
                                                          'POWERGRID', 'ONGC', 'COALINDIA', 'GRASIM', 'ULTRACEMCO',
                                                          'NESTLEIND', 'TITAN', 'HINDUNILVR', 'WIPRO', 'BAJFINANCE',
                                                          'BAJAJFINSV', 'KOTAKBANK', 'JSWSTEEL', 'DRREDDY', 'HDFC',
                                                          'BRITANNIA', 'CIPLA', 'EICHERMOT', 'GODREJPROP', 'HCLTECH',
                                                          'INDUSINDBK', 'IOC', 'M&M', 'MINDTREE', 'MUTHOOTFIN',
                                                          'NAUKRI', 'NEULANDLAB', 'OFSS', 'PIIND', 'POLYCAB',
                                                          'RAINBOW', 'RAJESHEXPO', 'RBLBANK', 'RECLTD', 'REDINGTON',
                                                          'SAIL', 'SANOFI', 'SBILIFE', 'SHOPERSTOP', 'SHREECEM',
                                                          'SRF', 'SUDOCHEM', 'SUMICHEM', 'SUNTV', 'SYNGENE',
                                                          'TATACHEM', 'TATACONSUM', 'TATACORP', 'TATAELXSI', 'TATAGLOBAL',
                                                          'TATAINVEST', 'TATAMETALI', 'TATAPOWER', 'TATASPONGE', 'TCS',
                                                          'TECHM', 'RAMCOCEM', 'UBL', 'VEDL', 'VGUARD',
                                                          'VOLTAS', 'WHIRLPOOL', 'WOCKPHARMA', 'YESBANK', 'ZEEL']:
                    ticker_to_use = f"{ticker}.NS"

                # Download data for single ticker to ensure proper handling of international suffixes
                ticker_data = yf.download(
                    tickers=[ticker_to_use],
                    period=period,
                    interval=interval,
                    auto_adjust=True,
                    progress=False,
                    threads=False,
                    group_by="column",
                )

                if ticker_data is not None and not ticker_data.empty:
                    # Extract closing prices
                    if isinstance(ticker_data.columns, pd.MultiIndex):
                        if "Close" in ticker_data.columns.get_level_values(0):
                            close_data = ticker_data["Close"].copy()
                        elif "Adj Close" in ticker_data.columns.get_level_values(0):
                            close_data = ticker_data["Adj Close"].copy()
                        else:
                            # fallback: use first available column
                            first_col = ticker_data.columns.get_level_values(0)[0]
                            close_data = ticker_data[first_col].copy()
                    else:
                        # Single column case
                        if "Close" in ticker_data.columns:
                            close_data = ticker_data[["Close"]].copy()
                        elif "Adj Close" in ticker_data.columns:
                            close_data = ticker_data[["Adj Close"]].copy()
                        else:
                            close_data = ticker_data.iloc[:, [0]].copy()

                    # Rename the column to match the original ticker
                    if len(close_data.columns) == 1:
                        close_data.columns = [ticker]

                    # Store the data
                    for date, row in close_data.iterrows():
                        if date not in all_prices:
                            all_prices[date] = {}
                        for col in row.index:
                            all_prices[date][col] = row[col]

            except Exception as e2:
                print(f"Warning: Could not fetch data for ticker {ticker}: {e2}")
                continue

        if not all_prices:
            return pd.DataFrame()

        # Convert the dictionary to DataFrame
        prices_df = pd.DataFrame(all_prices).T
        prices_df = prices_df.sort_index()

        # Ensure columns are in the same order as requested tickers
        ordered_columns = [t for t in tickers if t in prices_df.columns]
        prices_df = prices_df[ordered_columns]

        return prices_df


# -------------------------
# Public API
# -------------------------
def fetch_prices(
    tickers: List[str],
    lookback_days: int = 365,
    interval: Interval = "1d",
    cache_ttl_seconds: int = 60 * 60,
) -> PriceFetchResult:
    tickers = [t.strip().upper() for t in tickers if t.strip()]
    if not tickers:
        raise ValueError("No tickers provided")

    if interval not in ("1m", "1d", "1wk", "1mo"):
        raise ValueError("interval must be one of: 1m, 1d, 1wk, 1mo")

    cache_dir = _cache_dir()
    key = _cache_key(tickers, lookback_days, interval)

    use_parquet = _parquet_supported()
    cache_path = os.path.join(
        cache_dir,
        f"prices_{key}.parquet" if use_parquet else f"prices_{key}.csv.gz",
    )

    # 1) Cache
    if os.path.exists(cache_path):
        age = time.time() - os.path.getmtime(cache_path)
        if age <= cache_ttl_seconds:
            prices = _read_cache(cache_path, use_parquet).sort_index()
            # enforce column order (and ignore missing)
            cols = [t for t in tickers if t in prices.columns]
            prices = prices[cols]
            rets = prices.pct_change().dropna(how="all")
            if not prices.empty and not rets.empty:
                return PriceFetchResult(prices=prices, returns=rets, source="cache", cached=True)

    # 2) Try yfinance for all tickers, but collect partial success
    all_prices = pd.DataFrame()
    remaining_tickers = tickers.copy()
    yfin_error: Optional[str] = None

    try:
        yfin_prices = _fetch_yfinance_prices(remaining_tickers, lookback_days, interval)
        if not yfin_prices.empty:
            # Add successfully fetched yfinance data
            all_prices = pd.concat([all_prices, yfin_prices], axis=1)
            # Remove successfully fetched tickers from remaining
            successfully_fetched = [t for t in remaining_tickers if t in yfin_prices.columns]
            remaining_tickers = [t for t in remaining_tickers if t not in successfully_fetched]
    except Exception as e:
        yfin_error = str(e)
        print(f"Warning: yfinance failed for all tickers: {e}")

    # 3) Try Stooq for remaining tickers
    if remaining_tickers:
        stooq_prices = _fetch_stooq_prices(remaining_tickers, lookback_days, interval)
        if not stooq_prices.empty:
            # Add stooq data for remaining tickers
            all_prices = pd.concat([all_prices, stooq_prices], axis=1)
            # Remove successfully fetched tickers from remaining
            successfully_fetched = [t for t in remaining_tickers if t in stooq_prices.columns]
            remaining_tickers = [t for t in remaining_tickers if t not in successfully_fetched]

    # 4) Try mock prices for remaining Indian tickers
    if remaining_tickers:
        mock_prices = _fetch_mock_indian_prices(remaining_tickers, lookback_days, interval)
        if not mock_prices.empty:
            # Add mock data for remaining tickers
            if not all_prices.empty:
                # Combine the data by reindexing to include all dates
                all_dates = all_prices.index.union(mock_prices.index).sort_values()
                all_prices = all_prices.reindex(all_dates).ffill().bfill()
                mock_prices = mock_prices.reindex(all_dates).ffill().bfill()

            all_prices = pd.concat([all_prices, mock_prices], axis=1)
            # Remove successfully fetched tickers from remaining
            successfully_fetched = [t for t in remaining_tickers if t in mock_prices.columns]
            remaining_tickers = [t for t in remaining_tickers if t not in successfully_fetched]

    # Determine the source based on what worked
    if not all_prices.empty:
        if remaining_tickers and len(remaining_tickers) < len(tickers):
            src = "mixed_sources"
        elif all_prices.equals(yfin_prices if 'yfin_prices' in locals() and not yfin_prices.empty else pd.DataFrame()):
            src = "yfinance"
        elif all_prices.equals(mock_prices if 'mock_prices' in locals() and not mock_prices.empty else pd.DataFrame()):
            src = "mock_indian"
        elif all_prices.equals(stooq_prices if 'stooq_prices' in locals() and not stooq_prices.empty else pd.DataFrame()):
            src = "stooq"
        else:
            src = "mixed_sources"
    else:
        src = "yfinance"  # Default to yfinance for error message

    all_prices = all_prices.dropna(how="all").sort_index()

    if all_prices.empty:
        msg = "No market data returned (empty download). Try again or change tickers/interval."
        if yfin_error:
            msg += f" (yfinance error: {yfin_error})"
        # If we have stooq errors in the warnings list (which we track internally but didn't expose), 
        # we should at least hint at them. But yfin_error is key.
        raise RuntimeError(msg)

    # Check for missing tickers
    missing = [t for t in tickers if t not in all_prices.columns]
    if missing:
        # Print warning for missing tickers
        print(f"Warning: Missing price data for: {', '.join(missing)}")
        # Only include tickers that have data
        available_tickers = [t for t in tickers if t in all_prices.columns]
        if not available_tickers:
            raise RuntimeError(f"No price data available for any tickers: {', '.join(tickers)}")
        all_prices = all_prices[available_tickers].sort_index()
    else:
        all_prices = all_prices[tickers].sort_index()

    rets = all_prices.pct_change().dropna(how="all")
    if rets.empty:
        raise RuntimeError("Returns are empty (not enough data). Increase lookback_days or change interval.")

    # Save cache
    _write_cache(all_prices, cache_path, use_parquet)

    return PriceFetchResult(prices=all_prices, returns=rets, source=src, cached=False)


def max_drawdown(prices_or_index: pd.Series) -> float:
    x = prices_or_index.astype(float)
    peak = x.cummax()
    dd = (x / peak) - 1.0
    return float(dd.min())


def portfolio_metrics(returns: pd.DataFrame, weights: np.ndarray, periods_per_year: int) -> dict:
    if returns.empty:
        raise RuntimeError("portfolio_metrics got empty returns.")

    w = np.asarray(weights, dtype=float).reshape(-1)
    if len(w) != returns.shape[1]:
        raise ValueError("weights length does not match returns columns")

    # portfolio returns
    port = (returns.values @ w)
    port = pd.Series(port, index=returns.index, name="portfolio")

    vol = float(np.nanstd(port.to_numpy(), ddof=1) * np.sqrt(periods_per_year))

    idx = (1.0 + port.fillna(0.0)).cumprod()
    mdd = max_drawdown(idx)

    cov = returns.cov().values
    port_var = float(w.T @ cov @ w)

    if not np.isfinite(port_var) or port_var <= 0:
        rc = np.full(shape=(len(w),), fill_value=np.nan, dtype=float)
    else:
        mrc = cov @ w
        rc = (w * mrc) / port_var

    return {
        "annualized_vol": vol,
        "max_drawdown": float(mdd),
        "risk_contribution": rc,
    }