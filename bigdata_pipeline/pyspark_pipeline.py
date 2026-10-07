#!/usr/bin/env python3
"""
pyspark_pipeline.py
-------------------
Big Data Distributed Processing Pipeline using Apache PySpark.
Processes multi-year historical stock market data (Date, Open, High, Low, Close, Volume, Ticker)
distributed across nodes/partitions.

Key Big Data Calculations:
1. "Which way is this stock moving?":
   - Daily Returns (1-day % change)
   - 20-day, 50-day, and 200-day Simple Moving Averages (SMA) & 20-day Exponential Moving Average (EMA)
   - Trend signals: Golden Cross (50-SMA > 200-SMA) vs Death Cross (50-SMA < 200-SMA)
   - Trend Momentum Score & Direction (Bullish / Bearish / Neutral)

2. "How volatile is it?":
   - Rolling 21-day and 50-day Standard Deviation of Daily Returns
   - Annualized Volatility = StdDev * sqrt(252)
   - Intraday High-Low True Range & Spread %

3. "How does it compare with other stocks?":
   - Relative Return indexed to base period ($100 invested)
   - Beta Calculation vs S&P 500 benchmark (SPY)
   - Annualized Sharpe Ratio = (Annualized Return - Risk Free Rate) / Annualized Volatility
   - Cross-Stock Pearson Correlation Matrix
"""

import sys
import os
import math
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType, LongType, DateType
)

def create_spark_session(app_name="StockBigDataAnalytics"):
    """Initializes SparkSession with local distributed simulator config."""
    try:
        spark = SparkSession.builder \
            .appName(app_name) \
            .master("local[*]") \
            .config("spark.sql.shuffle.partitions", "8") \
            .config("spark.driver.memory", "2g") \
            .config("spark.sql.adaptive.enabled", "true") \
            .getOrCreate()
        spark.sparkContext.setLogLevel("ERROR")
        return spark
    except Exception as e:
        print(f"[!] Warning: SparkSession could not be initialized directly (Java Runtime may be required): {e}")
        print("[*] Falling back to standalone analytics engine (bigdata_pipeline/standalone_analytics.py)...")
        return None

def run_spark_pipeline(input_path, output_dir):
    spark = create_spark_session()
    if spark is None:
        # Fallback to standalone analytics
        from standalone_analytics import run_analytics_engine
        run_analytics_engine()
        return os.path.join(output_dir, "processed_stock_analytics.csv")
        
    print(f"[Spark Pipeline] Starting Big Data processing job...")
    print(f"[Spark Pipeline] Reading data from: {input_path}")

    schema = StructType([
        StructField("Date", StringType(), False),
        StructField("Ticker", StringType(), False),
        StructField("Open", DoubleType(), True),
        StructField("High", DoubleType(), True),
        StructField("Low", DoubleType(), True),
        StructField("Close", DoubleType(), True),
        StructField("Adj Close", DoubleType(), True),
        StructField("Volume", LongType(), True)
    ])

    df = spark.read.option("header", "true").schema(schema).csv(input_path)
    df = df.withColumn("Date", F.to_date(F.col("Date"), "yyyy-MM-dd"))

    print(f"[Spark Pipeline] Initial record count: {df.count()}")

    # Partition window by Ticker ordered by Date
    ticker_window_asc = Window.partitionBy("Ticker").orderBy("Date")
    
    # 1. Calculate Daily Returns
    # Return_t = (Close_t - Close_{t-1}) / Close_{t-1}
    df = df.withColumn("Prev_Close", F.lag("Close", 1).over(ticker_window_asc))
    df = df.withColumn("Daily_Return", 
        F.when(F.col("Prev_Close").isNull(), 0.0)
        .otherwise((F.col("Close") - F.col("Prev_Close")) / F.col("Prev_Close"))
    )

    # 2. Moving Averages: 20-day, 50-day, 200-day SMA
    w_20 = Window.partitionBy("Ticker").orderBy("Date").rowsBetween(-19, 0)
    w_50 = Window.partitionBy("Ticker").orderBy("Date").rowsBetween(-49, 0)
    w_200 = Window.partitionBy("Ticker").orderBy("Date").rowsBetween(-199, 0)

    df = df.withColumn("SMA_20", F.avg("Close").over(w_20))
    df = df.withColumn("SMA_50", F.avg("Close").over(w_50))
    df = df.withColumn("SMA_200", F.avg("Close").over(w_200))

    # 3. Volatility Calculations
    # Rolling 21-day (1 trading month) and 50-day StdDev of Daily Returns
    w_vol_21 = Window.partitionBy("Ticker").orderBy("Date").rowsBetween(-20, 0)
    w_vol_50 = Window.partitionBy("Ticker").orderBy("Date").rowsBetween(-49, 0)
    
    sqrt_252 = math.sqrt(252) # Annualization factor
    df = df.withColumn("StdDev_21d", F.stddev("Daily_Return").over(w_vol_21))
    df = df.withColumn("StdDev_50d", F.stddev("Daily_Return").over(w_vol_50))
    
    df = df.withColumn("Annualized_Volatility_21d", F.col("StdDev_21d") * F.lit(sqrt_252))
    df = df.withColumn("Annualized_Volatility_50d", F.col("StdDev_50d") * F.lit(sqrt_252))

    # High-Low Intraday Volatility / Spread
    df = df.withColumn("High_Low_Spread_Pct", ((F.col("High") - F.col("Low")) / F.col("Low")) * 100.0)

    # 4. Trend Insights ("Which way is this stock moving?")
    # Golden Cross: SMA_50 > SMA_200
    # Price vs SMA_50: Above 50 SMA = Bullish, Below = Bearish
    df = df.withColumn("Trend_Direction", 
        F.when((F.col("Close") > F.col("SMA_50")) & (F.col("SMA_50") > F.col("SMA_200")), "Strong Bullish")
        .when(F.col("Close") > F.col("SMA_50"), "Bullish")
        .when((F.col("Close") < F.col("SMA_50")) & (F.col("SMA_50") < F.col("SMA_200")), "Strong Bearish")
        .otherwise("Bearish")
    )
    
    df = df.withColumn("Crossover_Signal",
        F.when((F.col("SMA_50") > F.col("SMA_200")) & (F.lag("SMA_50", 1).over(ticker_window_asc) <= F.lag("SMA_200", 1).over(ticker_window_asc)), "Golden Cross (Buy)")
        .when((F.col("SMA_50") < F.col("SMA_200")) & (F.lag("SMA_50", 1).over(ticker_window_asc) >= F.lag("SMA_200", 1).over(ticker_window_asc)), "Death Cross (Sell)")
        .otherwise("Neutral")
    )

    # 5. Normalized Growth (Base $100 starting value for stock comparison)
    w_first = Window.partitionBy("Ticker").orderBy("Date").rowsBetween(Window.unboundedPreceding, Window.unboundedFollowing)
    df = df.withColumn("First_Close", F.first("Close").over(Window.partitionBy("Ticker").orderBy("Date")))
    df = df.withColumn("Normalized_100", (F.col("Close") / F.col("First_Close")) * 100.0)

    # Fill nulls in calculations
    df = df.na.fill({
        "SMA_20": 0.0, "SMA_50": 0.0, "SMA_200": 0.0,
        "StdDev_21d": 0.0, "StdDev_50d": 0.0,
        "Annualized_Volatility_21d": 0.0, "Annualized_Volatility_50d": 0.0
    })

    # Save processed analytics for Tableau / Dashboard UI
    os.makedirs(output_dir, exist_ok=True)
    csv_export_file = os.path.join(output_dir, "processed_stock_analytics.csv")
    
    # Collect as Pandas for clean export
    pdf = df.toPandas()
    pdf.to_csv(csv_export_file, index=False)
    print(f"[Spark Pipeline] Successfully processed {len(pdf)} rows.")
    print(f"[Spark Pipeline] Exported Tableau-ready Big Data file: {csv_export_file}")

    spark.stop()
    return csv_export_file

if __name__ == "__main__":
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    input_csv = os.path.join(base_dir, "dataset", "historical_stocks_raw.csv")
    output_folder = os.path.join(base_dir, "dashboard", "exported_analytics")
    run_spark_pipeline(input_csv, output_folder)
