// app.js - Big Data Stock Analytics & Tableau Dashboard Frontend Controller

let currentTicker = 'AAPL';
let currentTimeframe = 'ALL';
let allSummary = {};
let currentStockData = [];
let comparisonData = {};
let correlationData = {};

// Chart instances
let priceChartInstance = null;
let returnsHistInstance = null;
let volatilityChartInstance = null;
let multiStockChartInstance = null;
let riskReturnScatterInstance = null;

// Palette for multi-stock comparison
const TICKER_COLORS = {
  'AAPL': '#3B82F6',
  'MSFT': '#10B981',
  'GOOGL': '#F59E0B',
  'AMZN': '#EC4899',
  'TSLA': '#EF4444',
  'NVDA': '#8B5CF6',
  'META': '#06B6D4',
  'JPM': '#64748B',
  'SPY': '#FFFFFF',
  'QQQ': '#F97316'
};

document.addEventListener('DOMContentLoaded', () => {
  initDashboard();
});

async function initDashboard() {
  try {
    const res = await fetch('/api/tickers');
    const data = await res.json();
    if (data.status === 'success') {
      allSummary = data.summary;
      renderTickerButtons(data.tickers);
      renderPeerTable(allSummary);
      await loadStockData(currentTicker);
      await loadComparisonData();
      await loadCorrelationData();
    }
  } catch (err) {
    console.error('Error initializing dashboard:', err);
  }
}

function renderTickerButtons(tickers) {
  const container = document.getElementById('ticker-buttons-container');
  container.innerHTML = '';
  tickers.forEach(t => {
    const btn = document.createElement('button');
    btn.className = `ticker-btn ${t === currentTicker ? 'active' : ''}`;
    btn.innerText = t;
    btn.onclick = () => selectTicker(t);
    container.appendChild(btn);
  });
}

async function selectTicker(ticker) {
  currentTicker = ticker;
  document.querySelectorAll('.ticker-btn').forEach(btn => {
    btn.classList.toggle('active', btn.innerText === ticker);
  });
  await loadStockData(ticker);
}

function setTimeframe(tf) {
  currentTimeframe = tf;
  document.querySelectorAll('.tf-btn').forEach(btn => {
    btn.classList.toggle('active', btn.innerText === tf);
  });
  updatePriceChart();
  updateVolatilityChart();
  updateReturnsHist();
}

function filterByTimeframe(data) {
  if (!data || data.length === 0) return [];
  if (currentTimeframe === 'ALL') return data;

  const totalPoints = data.length;
  let pointsToTake = totalPoints;

  if (currentTimeframe === '1M') pointsToTake = 21;
  else if (currentTimeframe === '6M') pointsToTake = 126;
  else if (currentTimeframe === '1Y') pointsToTake = 252;
  else if (currentTimeframe === '3Y') pointsToTake = 252 * 3;
  else if (currentTimeframe === '5Y') pointsToTake = 252 * 5;

  return data.slice(-Math.min(totalPoints, pointsToTake));
}

async function loadStockData(ticker) {
  try {
    const res = await fetch(`/api/stocks/${ticker}`);
    const json = await res.json();
    if (json.status === 'success') {
      currentStockData = json.data;
      updateKPICards(json.summary);
      updatePriceChart();
      updateVolatilityChart();
      updateReturnsHist();
    }
  } catch (err) {
    console.error(`Error loading data for ${ticker}:`, err);
  }
}

function updateKPICards(summary) {
  if (!summary) return;

  // Price & Daily Return
  document.getElementById('kpi-price').innerText = `$${summary.latest_close.toFixed(2)}`;
  document.getElementById('kpi-date').innerText = `As of ${summary.latest_date}`;

  const returnBadge = document.getElementById('kpi-return');
  const retVal = summary.latest_return_pct;
  returnBadge.innerText = `${retVal >= 0 ? '+' : ''}${retVal.toFixed(2)}%`;
  returnBadge.className = `badge ${retVal >= 0 ? 'badge-bullish' : 'badge-bearish'}`;

  // Trend
  document.getElementById('kpi-trend').innerText = summary.trend_direction;
  const trendCard = document.getElementById('kpi-card-trend');
  trendCard.className = `kpi-card ${summary.trend_direction.includes('Bullish') ? 'bullish' : 'bearish'}`;

  const crossoverBadge = document.getElementById('kpi-crossover');
  crossoverBadge.innerText = summary.latest_crossover !== 'Neutral' ? summary.latest_crossover : 'SMA-50 > SMA-200';
  crossoverBadge.className = `badge ${summary.trend_direction.includes('Bullish') ? 'badge-bullish' : 'badge-bearish'}`;

  const sma50Diff = ((summary.latest_close - summary.current_sma_50) / summary.current_sma_50) * 100;
  document.getElementById('kpi-sma50-diff').innerText = `vs 50-SMA: ${sma50Diff >= 0 ? '+' : ''}${sma50Diff.toFixed(1)}%`;

  // Volatility
  document.getElementById('kpi-volatility').innerText = `${summary.current_vol_21d_pct.toFixed(1)}%`;
  document.getElementById('kpi-vol-50d').innerText = `50d: ${summary.current_vol_50d_pct.toFixed(1)}%`;

  const volBadge = document.getElementById('kpi-vol-badge');
  if (summary.current_vol_21d_pct < 20) {
    volBadge.innerText = 'Low Volatility';
    volBadge.className = 'badge badge-bullish';
  } else if (summary.current_vol_21d_pct <= 35) {
    volBadge.innerText = 'Moderate Volatility';
    volBadge.className = 'badge badge-neutral';
  } else {
    volBadge.innerText = 'High Volatility';
    volBadge.className = 'badge badge-bearish';
  }

  // Cross-stock compare
  document.getElementById('kpi-beta').innerText = `β ${summary.beta.toFixed(2)}`;
  document.getElementById('kpi-sharpe').innerText = `Sharpe: ${summary.sharpe_ratio.toFixed(2)}`;
  document.getElementById('kpi-total-return').innerText = `Total: +${summary.total_return_pct.toFixed(1)}%`;

  // Trend summary box
  document.getElementById('trend-signal-label').innerText = summary.trend_direction;
  document.getElementById('trend-signal-label').style.color = summary.trend_direction.includes('Bullish') ? 'var(--bullish)' : 'var(--bearish)';
  document.getElementById('trend-sma50-val').innerText = `$${summary.current_sma_50.toFixed(2)}`;
  document.getElementById('trend-sma200-val').innerText = `$${summary.current_sma_200.toFixed(2)}`;
  document.getElementById('trend-sma50-spread').innerText = `${sma50Diff >= 0 ? '+' : ''}${sma50Diff.toFixed(2)}%`;
  document.getElementById('trend-sma50-spread').style.color = sma50Diff >= 0 ? 'var(--bullish)' : 'var(--bearish)';
  document.getElementById('trend-crossover-val').innerText = summary.latest_crossover;

  // Volatility diagnostics box
  document.getElementById('vol-diag-21d').innerText = `${summary.current_vol_21d_pct.toFixed(2)}%`;
  document.getElementById('vol-diag-50d').innerText = `${summary.current_vol_50d_pct.toFixed(2)}%`;
  document.getElementById('vol-diag-overall').innerText = `${summary.overall_vol_pct.toFixed(2)}%`;
  document.getElementById('vol-diag-maxdd').innerText = `${summary.max_drawdown_pct.toFixed(2)}%`;

  const volDiagClass = document.getElementById('vol-diag-class');
  volDiagClass.innerText = summary.overall_vol_pct > 35 ? 'Aggressive / High Risk' : summary.overall_vol_pct > 20 ? 'Moderate Growth Risk' : 'Conservative / Defensive';
  volDiagClass.className = `badge ${summary.overall_vol_pct > 35 ? 'badge-bearish' : 'badge-bullish'}`;
}

function updatePriceChart() {
  const filtered = filterByTimeframe(currentStockData);
  if (!filtered || filtered.length === 0) return;

  const labels = filtered.map(r => r.Date);
  const prices = filtered.map(r => r.Close);
  const sma20 = filtered.map(r => r.SMA_20);
  const sma50 = filtered.map(r => r.SMA_50);
  const sma200 = filtered.map(r => r.SMA_200);

  const showSma20 = document.getElementById('toggle-sma20').checked;
  const showSma50 = document.getElementById('toggle-sma50').checked;
  const showSma200 = document.getElementById('toggle-sma200').checked;

  const datasets = [
    {
      label: `${currentTicker} Close Price`,
      data: prices,
      borderColor: '#3B82F6',
      backgroundColor: 'rgba(59, 130, 246, 0.08)',
      fill: true,
      borderWidth: 2,
      pointRadius: 0,
      tension: 0.1
    }
  ];

  if (showSma20) {
    datasets.push({
      label: '20-Day SMA',
      data: sma20,
      borderColor: '#06B6D4',
      borderWidth: 1.5,
      pointRadius: 0,
      borderDash: [3, 3]
    });
  }

  if (showSma50) {
    datasets.push({
      label: '50-Day SMA (Medium Trend)',
      data: sma50,
      borderColor: '#F59E0B',
      borderWidth: 2,
      pointRadius: 0
    });
  }

  if (showSma200) {
    datasets.push({
      label: '200-Day SMA (Macro Trend)',
      data: sma200,
      borderColor: '#EF4444',
      borderWidth: 2,
      pointRadius: 0
    });
  }

  const ctx = document.getElementById('trendPriceChart').getContext('2d');
  if (priceChartInstance) priceChartInstance.destroy();

  priceChartInstance = new Chart(ctx, {
    type: 'line',
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { labels: { color: '#9CA3AF', font: { family: 'Inter', size: 12 } } },
        tooltip: {
          backgroundColor: '#151A23',
          borderColor: '#262E3D',
          borderWidth: 1,
          titleColor: '#F3F4F6',
          bodyColor: '#9CA3AF',
          callbacks: {
            label: (item) => ` ${item.dataset.label}: $${item.parsed.y.toFixed(2)}`
          }
        }
      },
      scales: {
        x: { grid: { color: '#1F2937' }, ticks: { color: '#6B7280', maxTicksLimit: 10 } },
        y: { grid: { color: '#1F2937' }, ticks: { color: '#6B7280', callback: v => `$${v}` } }
      }
    }
  });
}

function updateVolatilityChart() {
  const filtered = filterByTimeframe(currentStockData);
  if (!filtered || filtered.length === 0) return;

  const labels = filtered.map(r => r.Date);
  const vol21 = filtered.map(r => (r.Annualized_Vol_21d || 0) * 100);
  const vol50 = filtered.map(r => (r.Annualized_Vol_50d || 0) * 100);

  const ctx = document.getElementById('volatilityChart').getContext('2d');
  if (volatilityChartInstance) volatilityChartInstance.destroy();

  volatilityChartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: '21-Day Annualized Volatility (%)',
          data: vol21,
          borderColor: '#F59E0B',
          backgroundColor: 'rgba(245, 158, 11, 0.05)',
          fill: true,
          borderWidth: 1.8,
          pointRadius: 0
        },
        {
          label: '50-Day Annualized Volatility (%)',
          data: vol50,
          borderColor: '#8B5CF6',
          borderWidth: 2,
          pointRadius: 0
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { labels: { color: '#9CA3AF', font: { family: 'Inter', size: 12 } } },
        tooltip: {
          backgroundColor: '#151A23',
          borderColor: '#262E3D',
          borderWidth: 1,
          callbacks: {
            label: (item) => ` ${item.dataset.label}: ${item.parsed.y.toFixed(2)}%`
          }
        }
      },
      scales: {
        x: { grid: { color: '#1F2937' }, ticks: { color: '#6B7280', maxTicksLimit: 8 } },
        y: { grid: { color: '#1F2937' }, ticks: { color: '#6B7280', callback: v => `${v}%` } }
      }
    }
  });
}

function updateReturnsHist() {
  const filtered = filterByTimeframe(currentStockData);
  if (!filtered || filtered.length === 0) return;

  const returns = filtered.map(r => (r.Daily_Return || 0) * 100);
  
  // Create 12 bins
  const binCount = 12;
  const min = Math.min(...returns);
  const max = Math.max(...returns);
  const step = (max - min) / binCount;

  const bins = new Array(binCount).fill(0);
  const binLabels = [];

  for (let i = 0; i < binCount; i++) {
    const low = min + i * step;
    const high = low + step;
    binLabels.push(`${low.toFixed(1)}%`);
  }

  returns.forEach(r => {
    let idx = Math.floor((r - min) / step);
    if (idx >= binCount) idx = binCount - 1;
    if (idx >= 0) bins[idx]++;
  });

  const ctx = document.getElementById('returnsHistChart').getContext('2d');
  if (returnsHistInstance) returnsHistInstance.destroy();

  returnsHistInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: binLabels,
      datasets: [{
        label: 'Frequency (Days)',
        data: bins,
        backgroundColor: binLabels.map(l => parseFloat(l) >= 0 ? '#10B981' : '#EF4444'),
        borderRadius: 4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false }
      },
      scales: {
        x: { grid: { display: false }, ticks: { color: '#6B7280', font: { size: 9 }, maxTicksLimit: 6 } },
        y: { grid: { color: '#1F2937' }, ticks: { color: '#6B7280', font: { size: 9 } } }
      }
    }
  });
}

async function loadComparisonData() {
  try {
    const res = await fetch('/api/comparison');
    const json = await res.json();
    if (json.status === 'success') {
      comparisonData = json;
      renderMultiStockChart(json.series);
      renderRiskReturnScatter(json.summary);
    }
  } catch (err) {
    console.error('Error loading comparison data:', err);
  }
}

function renderMultiStockChart(seriesObj) {
  const tickers = Object.keys(seriesObj);
  if (tickers.length === 0) return;

  const dates = seriesObj[tickers[0]].map(d => d.date);

  const datasets = tickers.map(t => {
    const color = TICKER_COLORS[t] || '#9CA3AF';
    const isPrimary = t === currentTicker || t === 'SPY';
    return {
      label: t,
      data: seriesObj[t].map(d => d.normalized),
      borderColor: color,
      borderWidth: isPrimary ? 2.5 : 1.2,
      pointRadius: 0,
      tension: 0.1
    };
  });

  const ctx = document.getElementById('multiStockChart').getContext('2d');
  if (multiStockChartInstance) multiStockChartInstance.destroy();

  multiStockChartInstance = new Chart(ctx, {
    type: 'line',
    data: { labels: dates, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { labels: { color: '#9CA3AF', font: { family: 'Inter', size: 11 }, boxWidth: 12 } },
        tooltip: {
          backgroundColor: '#151A23',
          borderColor: '#262E3D',
          borderWidth: 1,
          callbacks: {
            label: (item) => ` ${item.dataset.label}: $${item.parsed.y.toFixed(1)} (${(item.parsed.y - 100).toFixed(1)}%)`
          }
        }
      },
      scales: {
        x: { grid: { color: '#1F2937' }, ticks: { color: '#6B7280', maxTicksLimit: 12 } },
        y: { grid: { color: '#1F2937' }, ticks: { color: '#6B7280', callback: v => `$${v}` } }
      }
    }
  });
}

function renderRiskReturnScatter(summaryObj) {
  const tickers = Object.keys(summaryObj);
  const scatterData = tickers.map(t => {
    const s = summaryObj[t];
    return {
      x: s.overall_vol_pct,
      y: s.annualized_return_pct,
      ticker: t,
      sharpe: s.sharpe_ratio,
      beta: s.beta
    };
  });

  const ctx = document.getElementById('riskReturnScatterChart').getContext('2d');
  if (riskReturnScatterInstance) riskReturnScatterInstance.destroy();

  riskReturnScatterInstance = new Chart(ctx, {
    type: 'scatter',
    data: {
      datasets: [{
        label: 'Stocks (Annual Vol vs Annual Return)',
        data: scatterData,
        backgroundColor: scatterData.map(d => TICKER_COLORS[d.ticker] || '#3B82F6'),
        pointRadius: 8,
        pointHoverRadius: 11
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#151A23',
          borderColor: '#262E3D',
          borderWidth: 1,
          callbacks: {
            label: (item) => {
              const raw = item.raw;
              return [
                ` Stock: ${raw.ticker}`,
                ` Annual Return: ${raw.y.toFixed(1)}%`,
                ` Annual Volatility: ${raw.x.toFixed(1)}%`,
                ` Sharpe Ratio: ${raw.sharpe.toFixed(2)}`,
                ` Beta vs SPY: ${raw.beta.toFixed(2)}`
              ];
            }
          }
        }
      },
      scales: {
        x: {
          title: { display: true, text: 'Annualized Volatility (%) - Risk', color: '#9CA3AF' },
          grid: { color: '#1F2937' },
          ticks: { color: '#6B7280', callback: v => `${v}%` }
        },
        y: {
          title: { display: true, text: 'Annualized Return (%) - Reward', color: '#9CA3AF' },
          grid: { color: '#1F2937' },
          ticks: { color: '#6B7280', callback: v => `${v}%` }
        }
      }
    }
  });
}

async function loadCorrelationData() {
  try {
    const res = await fetch('/api/correlation');
    const json = await res.json();
    if (json.status === 'success') {
      correlationData = json.correlation;
      renderCorrelationHeatmap(json.correlation);
    }
  } catch (err) {
    console.error('Error loading correlation matrix:', err);
  }
}

function renderCorrelationHeatmap(corrObj) {
  const container = document.getElementById('correlation-heatmap-container');
  const tickers = Object.keys(corrObj);

  let html = '<table class="heatmap-table"><thead><tr><th></th>';
  tickers.forEach(t => {
    html += `<th>${t}</th>`;
  });
  html += '</tr></thead><tbody>';

  tickers.forEach(rowTicker => {
    html += `<tr><th style="background:var(--bg-main);">${rowTicker}</th>`;
    tickers.forEach(colTicker => {
      const val = corrObj[rowTicker][colTicker];
      // Color intensity based on correlation
      let bgStyle = 'rgba(59, 130, 246, 0.1)';
      if (val >= 0.8) bgStyle = 'rgba(59, 130, 246, 0.4)';
      else if (val >= 0.5) bgStyle = 'rgba(59, 130, 246, 0.25)';
      else if (val < 0.2) bgStyle = 'rgba(107, 114, 128, 0.15)';

      html += `<td style="background:${bgStyle}; font-weight:600;" title="${rowTicker} vs ${colTicker}: ${val}">${val.toFixed(2)}</td>`;
    });
    html += '</tr>';
  });

  html += '</tbody></table>';
  container.innerHTML = html;
}

function renderPeerTable(summaryObj) {
  const tbody = document.querySelector('#peer-comparison-table tbody');
  tbody.innerHTML = '';

  Object.values(summaryObj).forEach(s => {
    const tr = document.createElement('tr');
    tr.style.cursor = 'pointer';
    tr.onclick = () => selectTicker(s.ticker);

    const isBull = s.trend_direction.includes('Bullish');
    const trendClass = isBull ? 'badge-bullish' : 'badge-bearish';

    tr.innerHTML = `
      <td><strong style="color:${TICKER_COLORS[s.ticker] || '#FFF'}">${s.ticker}</strong></td>
      <td>$${s.latest_close.toFixed(2)}</td>
      <td style="color:${s.latest_return_pct >= 0 ? 'var(--bullish)' : 'var(--bearish)'}">${s.latest_return_pct >= 0 ? '+' : ''}${s.latest_return_pct.toFixed(2)}%</td>
      <td style="color:${s.annualized_return_pct >= 0 ? 'var(--bullish)' : 'var(--bearish)'}">+${s.annualized_return_pct.toFixed(1)}%</td>
      <td>${s.current_vol_50d_pct.toFixed(1)}%</td>
      <td>${s.beta.toFixed(2)}</td>
      <td style="color:${s.sharpe_ratio >= 1 ? '#34D399' : '#9CA3AF'}">${s.sharpe_ratio.toFixed(2)}</td>
      <td style="color:var(--bearish)">${s.max_drawdown_pct.toFixed(1)}%</td>
      <td><span class="badge ${trendClass}">${s.trend_direction}</span></td>
    `;
    tbody.appendChild(tr);
  });
}

async function triggerPipelineRun() {
  const icon = document.getElementById('refresh-icon');
  icon.classList.add('lucide-spin');
  try {
    const res = await fetch('/api/pipeline/run', { method: 'POST' });
    const data = await res.json();
    alert('Big Data Pipeline executed successfully! Data refreshed.');
    await initDashboard();
  } catch (err) {
    alert('Pipeline execution failed: ' + err.message);
  } finally {
    icon.classList.remove('lucide-spin');
  }
}
