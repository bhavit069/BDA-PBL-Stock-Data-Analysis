# Tableau Dashboard Guide: Big Data Stock Analytics

This guide provides step-by-step instructions for connecting **Tableau Desktop / Tableau Public** to the Big Data pipeline outputs generated in `bhavit/dashboard/exported_analytics/processed_stock_analytics.csv`.

---

## 1. Connecting Data Source in Tableau
1. Open **Tableau Desktop** (or **Tableau Public**).
2. Under **Connect** > **To a File**, select **Text File**.
3. Navigate to:
   `bhavit/dashboard/exported_analytics/processed_stock_analytics.csv`
4. Confirm the schema types:
   - `Date`: Date (`yyyy-MM-dd`)
   - `Ticker`: String / Dimension
   - `Open`, `High`, `Low`, `Close`, `Adj Close`: Number (decimal)
   - `Volume`: Number (whole)
   - `Daily_Return`: Number (decimal)
   - `SMA_20`, `SMA_50`, `SMA_200`: Number (decimal)
   - `Annualized_Vol_21d`, `Annualized_Vol_50d`: Number (decimal)
   - `Trend_Direction`: String / Dimension
   - `Crossover_Signal`: String / Dimension
   - `Normalized_100`: Number (decimal)

---

## 2. Creating Calculated Fields in Tableau

If you want to compute these metrics natively inside Tableau using Tableau Table Calculations:

### 1. Daily Return:
```tableau
// [Daily Return]
(SUM([Close]) - LOOKUP(SUM([Close]), -1)) / LOOKUP(SUM([Close]), -1)
```
*Compute Using: Specific Dimensions > Date*

### 2. 50-Day Simple Moving Average (SMA 50):
```tableau
// [50-Day Moving Average]
WINDOW_AVG(SUM([Close]), -49, 0)
```
*Compute Using: Specific Dimensions > Date*

### 3. 200-Day Simple Moving Average (SMA 200):
```tableau
// [200-Day Moving Average]
WINDOW_AVG(SUM([Close]), -199, 0)
```
*Compute Using: Specific Dimensions > Date*

### 4. 50-Day Annualized Rolling Volatility:
```tableau
// [50-Day Annualized Volatility]
WINDOW_STDEV([Daily Return], -49, 0) * SQRT(252)
```
*Compute Using: Specific Dimensions > Date*

---

## 3. Building the 3 Core Analytical Views

### Worksheet 1: "Which way is this stock moving?" (Trend & Moving Averages)
- **Columns**: `Date` (Continuous Day/Month)
- **Rows**: `SUM(Close)`, `SUM(SMA_50)`, `SUM(SMA_200)`
- **Chart Type**: Dual Axis Line Chart (Synchronize Axis)
- **Color**:
  - `Close`: Blue (`#3B82F6`)
  - `SMA_50`: Amber (`#F59E0B`)
  - `SMA_200`: Red (`#EF4444`)
- **Filters**: `Ticker` (Single value dropdown), `Date` Range slider.

---

### Worksheet 2: "How volatile is it?" (Risk & Volatility Spectrum)
- **Columns**: `Date` (Continuous)
- **Rows**: `AVG(Annualized_Vol_21d)`, `AVG(Annualized_Vol_50d)`
- **Chart Type**: Dual line area chart with reference band at 20% (Low Volatility) and 35% (High Volatility).
- **Secondary Card**: High-Low Intraday Spread `AVG(High_Low_Spread_Pct)`.

---

### Worksheet 3: "How does it compare with other stocks?" (Cross-Stock Benchmark)
- **Columns**: `Date` (Continuous)
- **Rows**: `AVG(Normalized_100)`
- **Color**: `Ticker` (Multi-line comparison)
- **Scatter Plot View**:
  - **Columns**: `AVG(Annualized_Vol_50d)` (Risk / X-Axis)
  - **Rows**: `AVG(Daily_Return) * 252` (Annualized Return / Y-Axis)
  - **Detail**: `Ticker`
  - **Size**: `AVG(Volume)`
  - **Color**: `AVG(Beta)`

---

## 4. Assembling the Tableau Interactive Dashboard
1. Create a new **Dashboard** canvas (Recommended resolution: `1600 x 1000`).
2. Drag **Worksheet 1 (Trend)** to top-left.
3. Drag **Worksheet 2 (Volatility)** to bottom-left.
4. Drag **Worksheet 3 (Peer Comparison)** to the right panel.
5. Apply `Ticker` filter to **"All Using Related Data Sources"** to achieve synchronized cross-filtering.
6. Export as `.twbx` (Tableau Packaged Workbook) or Publish to **Tableau Public**.
