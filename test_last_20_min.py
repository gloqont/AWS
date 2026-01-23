#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'apps', 'api'))

from risk import fetch_prices

def test_last_20_min_prices():
    """Test fetching last 20 minutes of prices for Indian and USA tickers"""
    # US tickers
    us_tickers = ['AAPL', 'GOOGL']
    print("Testing fetching last 20 minutes of prices for US tickers:")
    for ticker in us_tickers:
        try:
            print(f"Fetching last 20 min prices for {ticker}...")
            # For intraday data, use period="1d" and interval="1m" to get 1-minute bars for the last day
            result = fetch_prices([ticker], lookback_days=1, interval="1m")
            if not result.prices.empty:
                # Get the last 20 rows (last 20 minutes)
                last_20 = result.prices.tail(20)
                print(f"✓ {ticker}: SUCCESS - Last 20 minutes: {len(last_20)} data points")
                print(f"  Latest price: {last_20.iloc[-1][ticker]}")
            else:
                print(f"✗ {ticker}: FAILED - No data returned")
        except Exception as e:
            print(f"✗ {ticker}: FAILED - {str(e)}")

    # Indian tickers
    indian_tickers = ['RELIANCE.NS', 'TCS.NS']
    print("\nTesting fetching last 20 minutes of prices for Indian tickers:")
    for ticker in indian_tickers:
        try:
            print(f"Fetching last 20 min prices for {ticker}...")
            result = fetch_prices([ticker], lookback_days=1, interval="1m")
            if not result.prices.empty:
                # Get the last 20 rows (last 20 minutes)
                last_20 = result.prices.tail(20)
                print(f"✓ {ticker}: SUCCESS - Last 20 minutes: {len(last_20)} data points")
                print(f"  Latest price: {last_20.iloc[-1][ticker]}")
            else:
                print(f"✗ {ticker}: FAILED - No data returned")
        except Exception as e:
            print(f"✗ {ticker}: FAILED - {str(e)}")

if __name__ == "__main__":
    test_last_20_min_prices()
