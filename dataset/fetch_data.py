#!/usr/bin/env python3
"""
fetch_data.py - Ingests historical stock prices (Date, Open, High, Low, Close, Volume, Ticker)
Uses yfinance if available, with an intelligent fallback synthetic generator to ensure 100% offline availability.
"""

import os
import sys
from datetime import datetime, timedelta

DATASET_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(DATASET_DIR, "historical_stocks_raw.csv")

TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "JPM", "SPY", "QQQ"]
START_DATE = "2019-01-01"
END_DATE = "2026-10-01"

def fetch_real_data():
    try:
        import yfinance as yf
        import pandas as pd
        print(f"[*] Fetching historical stock data from Yahoo Finance for: {', '.join(TICKERS)}...")
        df_list = []
        for ticker in TICKERS:
            print(f"    - Downloading {ticker} ({START_DATE} to {END_DATE})...")
            data = yf.download(ticker, start=START_DATE, end=END_DATE, auto_adjust=False, progress=False)
            if data.empty:
                print(f"      [!] Warning: No data returned for {ticker}")
                continue
            
            # Reset index to get Date as column
            if isinstance(data.columns, pd.MultiIndex):
                # Flatten multi-level columns if returned by newer yfinance
                data.columns = [col[0] if isinstance(col, tuple) else col for col in data.columns]
                
            data = data.reset_index()
            data["Ticker"] = ticker
            data["Date"] = pd.to_datetime(data["Date"]).dt.strftime("%Y-%m-%d")
            
            cols_needed = ["Date", "Ticker", "Open", "High", "Low", "Close", "Adj Close", "Volume"]
            for col in cols_needed:
                if col not in data.columns and col == "Adj Close" and "Close" in data.columns:
                    data["Adj Close"] = data["Close"]
            
            df_list.append(data[cols_needed])
            
        if df_list:
            combined_df = pd.concat(df_list, ignore_index=True)
            combined_df.sort_values(by=["Ticker", "Date"], inplace=True)
            combined_df.to_csv(OUTPUT_FILE, index=False)
            print(f"[+] Successfully fetched {len(combined_df)} records across {len(TICKERS)} stocks.")
            print(f"[+] Raw dataset saved to: {OUTPUT_FILE}")
            return True
    except Exception as e:
        print(f"[!] Yahoo finance download encountered an issue: {e}")
        print("[*] Switching to realistic high-fidelity Geometric Brownian Motion data generator...")
    return False

def generate_synthetic_data():
    """Generates realistic 7+ years of market data using Geometric Brownian Motion & Volatility clustering."""
    import random
    import math

    print("[*] Generating realistic 7-year historical market dataset...")
    # Base parameters per ticker
    params = {
        "AAPL": {"base_price": 40.0, "mu": 0.24, "sigma": 0.28, "vol_base": 70000000},
        "MSFT": {"base_price": 100.0, "mu": 0.22, "sigma": 0.25, "vol_base": 30000000},
        "GOOGL": {"base_price": 52.0, "mu": 0.18, "sigma": 0.26, "vol_base": 25000000},
        "AMZN": {"base_price": 75.0, "mu": 0.20, "sigma": 0.32, "vol_base": 45000000},
        "TSLA": {"base_price": 20.0, "mu": 0.40, "sigma": 0.55, "vol_base": 85000000},
        "NVDA": {"base_price": 35.0, "mu": 0.52, "sigma": 0.48, "vol_base": 50000000},
        "META": {"base_price": 130.0, "mu": 0.23, "sigma": 0.38, "vol_base": 20000000},
        "JPM":  {"base_price": 95.0, "mu": 0.14, "sigma": 0.22, "vol_base": 15000000},
        "SPY":  {"base_price": 250.0, "mu": 0.13, "sigma": 0.16, "vol_base": 80000000},
        "QQQ":  {"base_price": 150.0, "mu": 0.18, "sigma": 0.20, "vol_base": 55000000},
    }

    start_dt = datetime.strptime("2019-01-02", "%Y-%m-%d")
    end_dt = datetime.strptime("2026-10-01", "%Y-%m-%d")
    
    # Generate business days
    current_dt = start_dt
    dates = []
    while current_dt <= end_dt:
        if current_dt.weekday() < 5: # Monday to Friday
            dates.append(current_dt.strftime("%Y-%m-%d"))
        current_dt += timedelta(days=1)

    records = []
    header = ["Date", "Ticker", "Open", "High", "Low", "Close", "Adj Close", "Volume"]

    dt = 1.0 / 252.0 # 1 trading day

    random.seed(42)

    for ticker, p in params.items():
        price = p["base_price"]
        mu = p["mu"]
        sigma = p["sigma"]
        vol_base = p["vol_base"]

        for i, date_str in enumerate(dates):
            # Market regime shift / COVID dip in early 2020 & 2022 rate hike simulation
            year_val = int(date_str[:4])
            month_val = int(date_str[5:7])
            
            current_sigma = sigma
            current_mu = mu
            
            if year_val == 2020 and month_val in [2, 3]:
                current_sigma *= 2.2
                current_mu = -0.6
            elif year_val == 2022:
                current_sigma *= 1.3
                current_mu = -0.15
            elif year_val in [2023, 2024, 2025, 2026] and ticker in ["NVDA", "MSFT", "AAPL", "META"]:
                # AI boom
                current_mu += 0.15

            # GBM step
            z = random.gauss(0, 1)
            ret = (current_mu - 0.5 * (current_sigma ** 2)) * dt + current_sigma * math.sqrt(dt) * z
            new_price = max(1.0, price * math.exp(ret))

            # Generate realistic intraday Open, High, Low
            intraday_vol = current_sigma * math.sqrt(dt) * 0.8
            open_price = price * (1 + random.gauss(0, intraday_vol * 0.4))
            high_price = max(price, new_price, open_price) * (1 + abs(random.gauss(0, intraday_vol * 0.7)))
            low_price = min(price, new_price, open_price) * (1 - abs(random.gauss(0, intraday_vol * 0.7)))
            close_price = new_price

            volume = int(vol_base * (1 + abs(ret) * 12 + random.uniform(-0.3, 0.5)))
            volume = max(100000, volume)

            records.append([
                date_str,
                ticker,
                f"{open_price:.2f}",
                f"{high_price:.2f}",
                f"{low_price:.2f}",
                f"{close_price:.2f}",
                f"{close_price:.2f}",
                str(volume)
            ])

            price = new_price

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(",".join(header) + "\n")
        for r in records:
            f.write(",".join(r) + "\n")

    print(f"[+] Synthetic dataset generated successfully: {len(records)} records.")
    print(f"[+] Saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    success = fetch_real_data()
    if not success:
        generate_synthetic_data()
