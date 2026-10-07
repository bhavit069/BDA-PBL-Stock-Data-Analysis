#!/usr/bin/env python3
"""
standalone_analytics.py
-----------------------
High-performance Big Data Analytics Engine for multi-year stock market time-series.
Calculates all pipeline metrics, trend insights, volatility measures, and comparative risk metrics.
Generates Tableau-optimized CSV exports and JSON summary matrices.
"""

import os
import json
import math
import numpy as np
import pandas as pd

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RAW_DATA_PATH = os.path.join(BASE_DIR, "dataset", "historical_stocks_raw.csv")
EXPORT_DIR = os.path.join(BASE_DIR, "dashboard", "exported_analytics")
CSV_EXPORT_PATH = os.path.join(EXPORT_DIR, "processed_stock_analytics.csv")
SUMMARY_EXPORT_PATH = os.path.join(EXPORT_DIR, "stock_summary_metrics.json")
CORRELATION_EXPORT_PATH = os.path.join(EXPORT_DIR, "correlation_matrix.json")

RISK_FREE_RATE = 0.045 # 4.5% annual risk-free rate assumption

def run_analytics_engine():
    print(f"[*] Starting Big Data Analytics Engine...")
    print(f"    - Input dataset: {RAW_DATA_PATH}")
    
    if not os.path.exists(RAW_DATA_PATH):
        raise FileNotFoundError(f"Raw dataset not found at {RAW_DATA_PATH}. Run fetch_data.py first.")

    os.makedirs(EXPORT_DIR, exist_ok=True)

    df = pd.read_csv(RAW_DATA_PATH)
    df["Date"] = pd.to_datetime(df["Date"])
    df.sort_values(by=["Ticker", "Date"], inplace=True)

    processed_dfs = []
    summary_metrics = {}

    # Benchmark daily returns for Beta calculation (SPY)
    spy_df = df[df["Ticker"] == "SPY"].copy().sort_values("Date")
    spy_df["SPY_Return"] = spy_df["Close"].pct_change().fillna(0.0)
    spy_returns_map = dict(zip(spy_df["Date"], spy_df["SPY_Return"]))
    spy_variance = spy_df["SPY_Return"].var() if len(spy_df) > 1 else 1.0

    tickers = sorted(df["Ticker"].unique())

    # Daily returns pivot for correlation matrix
    returns_pivot = {}

    for ticker in tickers:
        tdf = df[df["Ticker"] == ticker].copy().sort_values("Date").reset_index(drop=True)
        
        # 1. Daily Returns & Cumulative Returns
        tdf["Prev_Close"] = tdf["Close"].shift(1)
        tdf["Daily_Return"] = (tdf["Close"] - tdf["Prev_Close"]) / tdf["Prev_Close"]
        tdf["Daily_Return"] = tdf["Daily_Return"].fillna(0.0)
        tdf["Cumulative_Return"] = (1 + tdf["Daily_Return"]).cumprod() - 1.0

        # Normalized Base $100 starting investment
        first_close = tdf["Close"].iloc[0]
        tdf["Normalized_100"] = (tdf["Close"] / first_close) * 100.0

        # 2. Moving Averages (20, 50, 200 SMA & 20 EMA)
        tdf["SMA_20"] = tdf["Close"].rolling(window=20, min_periods=1).mean()
        tdf["SMA_50"] = tdf["Close"].rolling(window=50, min_periods=1).mean()
        tdf["SMA_200"] = tdf["Close"].rolling(window=200, min_periods=1).mean()
        tdf["EMA_20"] = tdf["Close"].ewm(span=20, adjust=False).mean()

        # 3. Volatility Calculations (Annualized = StdDev * sqrt(252))
        sqrt_252 = math.sqrt(252)
        tdf["StdDev_21d"] = tdf["Daily_Return"].rolling(window=21, min_periods=2).std().fillna(0.0)
        tdf["StdDev_50d"] = tdf["Daily_Return"].rolling(window=50, min_periods=2).std().fillna(0.0)
        tdf["Annualized_Vol_21d"] = tdf["StdDev_21d"] * sqrt_252
        tdf["Annualized_Vol_50d"] = tdf["StdDev_50d"] * sqrt_252
        tdf["High_Low_Spread_Pct"] = ((tdf["High"] - tdf["Low"]) / tdf["Low"]) * 100.0

        # 4. Trend Insights ("Which way is this stock moving?")
        tdf["Trend_Direction"] = "Neutral"
        strong_bull = (tdf["Close"] > tdf["SMA_50"]) & (tdf["SMA_50"] > tdf["SMA_200"])
        bull = (tdf["Close"] > tdf["SMA_50"]) & ~strong_bull
        strong_bear = (tdf["Close"] < tdf["SMA_50"]) & (tdf["SMA_50"] < tdf["SMA_200"])
        bear = (tdf["Close"] < tdf["SMA_50"]) & ~strong_bear

        tdf.loc[strong_bull, "Trend_Direction"] = "Strong Bullish"
        tdf.loc[bull, "Trend_Direction"] = "Bullish"
        tdf.loc[strong_bear, "Trend_Direction"] = "Strong Bearish"
        tdf.loc[bear, "Trend_Direction"] = "Bearish"

        # Golden Cross & Death Cross Detection
        prev_sma50 = tdf["SMA_50"].shift(1)
        prev_sma200 = tdf["SMA_200"].shift(1)
        tdf["Crossover_Signal"] = "Neutral"
        golden_mask = (tdf["SMA_50"] > tdf["SMA_200"]) & (prev_sma50 <= prev_sma200)
        death_mask = (tdf["SMA_50"] < tdf["SMA_200"]) & (prev_sma50 >= prev_sma200)
        tdf.loc[golden_mask, "Crossover_Signal"] = "Golden Cross (Bullish)"
        tdf.loc[death_mask, "Crossover_Signal"] = "Death Cross (Bearish)"

        # 5. Risk and Beta vs Benchmark SPY
        tdf["SPY_Return"] = tdf["Date"].map(spy_returns_map).fillna(0.0)
        cov_matrix = np.cov(tdf["Daily_Return"], tdf["SPY_Return"])
        cov_stock_spy = cov_matrix[0, 1] if cov_matrix.shape == (2, 2) else 0.0
        beta_val = cov_stock_spy / spy_variance if spy_variance > 0 else 1.0

        # Overall summary metrics for this stock
        trading_days = len(tdf)
        years = max(0.1, trading_days / 252.0)
        total_ret = (tdf["Close"].iloc[-1] / tdf["Close"].iloc[0]) - 1.0
        annualized_return = ((1.0 + max(-0.99, total_ret)) ** (1.0 / years)) - 1.0
        overall_vol = tdf["Daily_Return"].std() * sqrt_252
        sharpe_ratio = (annualized_return - RISK_FREE_RATE) / overall_vol if overall_vol > 0 else 0.0

        # Max Drawdown
        cum_max = tdf["Close"].cummax()
        drawdown = (tdf["Close"] - cum_max) / cum_max
        max_drawdown = drawdown.min()

        latest_row = tdf.iloc[-1]
        summary_metrics[ticker] = {
            "ticker": ticker,
            "latest_date": latest_row["Date"].strftime("%Y-%m-%d"),
            "latest_close": round(float(latest_row["Close"]), 2),
            "prev_close": round(float(latest_row["Prev_Close"]), 2),
            "latest_return_pct": round(float(latest_row["Daily_Return"]) * 100, 2),
            "total_return_pct": round(float(total_ret) * 100, 2),
            "annualized_return_pct": round(float(annualized_return) * 100, 2),
            "current_sma_20": round(float(latest_row["SMA_20"]), 2),
            "current_sma_50": round(float(latest_row["SMA_50"]), 2),
            "current_sma_200": round(float(latest_row["SMA_200"]), 2),
            "current_vol_21d_pct": round(float(latest_row["Annualized_Vol_21d"]) * 100, 2),
            "current_vol_50d_pct": round(float(latest_row["Annualized_Vol_50d"]) * 100, 2),
            "overall_vol_pct": round(float(overall_vol) * 100, 2),
            "beta": round(float(beta_val), 2),
            "sharpe_ratio": round(float(sharpe_ratio), 2),
            "max_drawdown_pct": round(float(max_drawdown) * 100, 2),
            "trend_direction": str(latest_row["Trend_Direction"]),
            "latest_crossover": str(latest_row["Crossover_Signal"]),
            "avg_volume": int(tdf["Volume"].mean()),
            "data_points": int(len(tdf))
        }

        returns_pivot[ticker] = tdf.set_index("Date")["Daily_Return"]
        processed_dfs.append(tdf)

    # Combined master dataframe for Tableau and Dashboard
    final_df = pd.concat(processed_dfs, ignore_index=True)
    final_df["Date"] = final_df["Date"].dt.strftime("%Y-%m-%d")
    final_df.to_csv(CSV_EXPORT_PATH, index=False)
    print(f"[+] Exported Tableau-compatible Big Data CSV: {CSV_EXPORT_PATH} ({len(final_df)} rows)")

    # Correlation Matrix
    returns_df = pd.DataFrame(returns_pivot).dropna()
    corr_matrix = returns_df.corr().round(3).to_dict()

    with open(SUMMARY_EXPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(summary_metrics, f, indent=2)
    print(f"[+] Saved Stock Summary Metrics JSON: {SUMMARY_EXPORT_PATH}")

    with open(CORRELATION_EXPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(corr_matrix, f, indent=2)
    print(f"[+] Saved Cross-Stock Correlation Matrix JSON: {CORRELATION_EXPORT_PATH}")

    print("[*] Big Data Processing Engine completed successfully!")

if __name__ == "__main__":
    run_analytics_engine()
