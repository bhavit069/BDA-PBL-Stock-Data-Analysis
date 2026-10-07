#!/usr/bin/env python3
"""
reducer.py - Hadoop Streaming MapReduce Reducer
----------------------------------------------
Aggregates time-series stock price data grouped by Ticker.
Computes:
1. Daily Return: (Close - PrevClose) / PrevClose
2. 20-day, 50-day, 200-day Moving Averages (SMA)
3. 21-day and 50-day Annualized Volatility (StdDev * sqrt(252))
4. Trend direction & Golden/Death Cross signals

Output format:
Ticker,Date,Close,Daily_Return,SMA_20,SMA_50,SMA_200,Vol_21d,Vol_50d,Trend
"""

import sys
import math

def calculate_stddev(values):
    n = len(values)
    if n < 2:
        return 0.0
    mean_val = sum(values) / n
    variance = sum((x - mean_val) ** 2 for x in values) / (n - 1)
    return math.sqrt(variance)

def process_ticker(ticker, rows):
    # Sort chronologically by date
    rows.sort(key=lambda r: r["date"])

    prev_close = None
    close_history = []
    returns_history = []
    sqrt_252 = math.sqrt(252)

    for r in rows:
        date = r["date"]
        close = r["close"]
        open_p = r["open"]
        high_p = r["high"]
        low_p = r["low"]
        volume = r["volume"]

        # 1. Daily Return
        if prev_close is None or prev_close == 0:
            daily_return = 0.0
        else:
            daily_return = (close - prev_close) / prev_close
        
        close_history.append(close)
        returns_history.append(daily_return)

        # 2. Moving Averages
        sma_20 = sum(close_history[-20:]) / min(len(close_history), 20)
        sma_50 = sum(close_history[-50:]) / min(len(close_history), 50)
        sma_200 = sum(close_history[-200:]) / min(len(close_history), 200)

        # 3. Volatility
        vol_21d = calculate_stddev(returns_history[-21:]) * sqrt_252 if len(returns_history) >= 2 else 0.0
        vol_50d = calculate_stddev(returns_history[-50:]) * sqrt_252 if len(returns_history) >= 2 else 0.0

        # 4. Trend Direction
        if close > sma_50 and sma_50 > sma_200:
            trend = "Strong Bullish"
        elif close > sma_50:
            trend = "Bullish"
        elif close < sma_50 and sma_50 < sma_200:
            trend = "Strong Bearish"
        else:
            trend = "Bearish"

        print(f"{ticker},{date},{open_p:.2f},{high_p:.2f},{low_p:.2f},{close:.2f},{volume},{daily_return:.6f},{sma_20:.2f},{sma_50:.2f},{sma_200:.2f},{vol_21d:.4f},{vol_50d:.4f},{trend}")
        prev_close = close

def main():
    current_ticker = None
    current_rows = []

    # Print CSV header
    print("Ticker,Date,Open,High,Low,Close,Volume,Daily_Return,SMA_20,SMA_50,SMA_200,Annualized_Vol_21d,Annualized_Vol_50d,Trend_Direction")

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        
        parts = line.split("\t")
        if len(parts) != 2:
            continue
        
        ticker, val_str = parts
        val_parts = val_str.split(",")
        if len(val_parts) < 6:
            continue

        try:
            row_dict = {
                "date": val_parts[0],
                "open": float(val_parts[1]),
                "high": float(val_parts[2]),
                "low": float(val_parts[3]),
                "close": float(val_parts[4]),
                "volume": int(float(val_parts[5]))
            }
        except ValueError:
            continue

        if current_ticker == ticker:
            current_rows.append(row_dict)
        else:
            if current_ticker and current_rows:
                process_ticker(current_ticker, current_rows)
            current_ticker = ticker
            current_rows = [row_dict]

    if current_ticker and current_rows:
        process_ticker(current_ticker, current_rows)

if __name__ == "__main__":
    main()
