#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'apps', 'api'))

from risk import fetch_prices

def test_previous_day_closing_prices():
    """Test fetching previous day closing prices for various tickers"""
    # Test with US tickers first
    us_tickers = ['AAPL', 'GOOGL', 'MSFT']
    print("Testing fetching previous day closing prices for US tickers:")
    for ticker in us_tickers:
        try:
            print(f"Fetching previous day closing price for {ticker}...")
            result = fetch_prices([ticker], lookback_days=1, interval="1d")
            if not result.prices.empty:
                last_price = result.prices.iloc[-1][ticker]
                print(f"✓ {ticker}: SUCCESS - Previous day closing price: {last_price}")
            else:
                print(f"✗ {ticker}: FAILED - No data returned")
        except Exception as e:
            print(f"✗ {ticker}: FAILED - {str(e)}")

    # Test with Indian tickers
    indian_tickers = ['RELIANCE.NS', 'TCS.NS', 'INFY.NS']
    print("\nTesting fetching previous day closing prices for Indian tickers:")
    for ticker in indian_tickers:
        try:
            print(f"Fetching previous day closing price for {ticker}...")
            result = fetch_prices([ticker], lookback_days=1, interval="1d")
            if not result.prices.empty:
                last_price = result.prices.iloc[-1][ticker]
                print(f"✓ {ticker}: SUCCESS - Previous day closing price: {last_price}")
            else:
                print(f"✗ {ticker}: FAILED - No data returned")
        except Exception as e:
            print(f"✗ {ticker}: FAILED - {str(e)}")

if __name__ == "__main__":
    test_previous_day_closing_prices()
