#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'apps', 'api'))

from risk import fetch_prices

def test_indian_tickers():
    """Test fetching prices for Indian tickers"""
    # Common Indian tickers without suffix
    indian_tickers = ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK']

    print("Testing Indian tickers without .NS suffix:")
    for ticker in indian_tickers:
        try:
            print(f"Fetching {ticker}...")
            result = fetch_prices([ticker], lookback_days=30, interval="1d")
            print(f"✓ {ticker}: SUCCESS - {len(result.prices)} rows")
        except Exception as e:
            print(f"✗ {ticker}: FAILED - {str(e)}")

    print("\nTesting Indian tickers with .NS suffix:")
    indian_tickers_ns = [f"{ticker}.NS" for ticker in indian_tickers]
    for ticker in indian_tickers_ns:
        try:
            print(f"Fetching {ticker}...")
            result = fetch_prices([ticker], lookback_days=30, interval="1d")
            print(f"✓ {ticker}: SUCCESS - {len(result.prices)} rows")
        except Exception as e:
            print(f"✗ {ticker}: FAILED - {str(e)}")

if __name__ == "__main__":
    test_indian_tickers()
