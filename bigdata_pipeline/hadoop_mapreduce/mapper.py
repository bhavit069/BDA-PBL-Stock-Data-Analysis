#!/usr/bin/env python3
"""
mapper.py - Hadoop Streaming MapReduce Mapper
--------------------------------------------
Reads raw CSV stock rows from standard input, parses the attributes:
Date, Ticker, Open, High, Low, Close, Adj Close, Volume

Emits Key-Value pairs:
Key:   Ticker
Value: Date,Open,High,Low,Close,Volume
"""

import sys

def mapper():
    first_line = True
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        
        # Skip CSV header
        if first_line and "Date" in line and "Ticker" in line:
            first_line = False
            continue

        parts = line.split(",")
        if len(parts) >= 8:
            date, ticker, open_p, high_p, low_p, close_p, adj_close, volume = parts[:8]
            # Key: Ticker
            # Value: Date \t Open \t High \t Low \t Close \t Volume
            print(f"{ticker}\t{date},{open_p},{high_p},{low_p},{close_p},{volume}")

if __name__ == "__main__":
    mapper()
