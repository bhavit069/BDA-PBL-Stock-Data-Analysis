// server.js - Zero-dependency High-Performance Stock Analytics Server
const http = require('http');
const fs = require('fs');
const path = require('path');
const { exec } = require('child_process');
const url = require('url');

const PORT = process.env.PORT || 3000;
const BASE_DIR = path.resolve(__dirname, '..');
const PUBLIC_DIR = path.join(__dirname, 'public');
const EXPORT_DIR = path.join(__dirname, 'exported_analytics');

const CSV_FILE = path.join(EXPORT_DIR, 'processed_stock_analytics.csv');
const SUMMARY_FILE = path.join(EXPORT_DIR, 'stock_summary_metrics.json');
const CORRELATION_FILE = path.join(EXPORT_DIR, 'correlation_matrix.json');

// In-memory cache
let cachedData = null;
let cachedSummary = null;
let cachedCorrelation = null;

function loadData() {
  try {
    if (fs.existsSync(SUMMARY_FILE)) {
      cachedSummary = JSON.parse(fs.readFileSync(SUMMARY_FILE, 'utf8'));
    }
    if (fs.existsSync(CORRELATION_FILE)) {
      cachedCorrelation = JSON.parse(fs.readFileSync(CORRELATION_FILE, 'utf8'));
    }
    if (fs.existsSync(CSV_FILE)) {
      const csvText = fs.readFileSync(CSV_FILE, 'utf8');
      const lines = csvText.trim().split('\n');
      const headers = lines[0].split(',').map(h => h.trim());
      
      const rows = [];
      for (let i = 1; i < lines.length; i++) {
        const parts = lines[i].split(',');
        if (parts.length === headers.length) {
          const row = {};
          headers.forEach((h, idx) => {
            const val = parts[idx].trim();
            const num = Number(val);
            row[h] = isNaN(num) || h === 'Date' || h === 'Ticker' || h.includes('Trend') || h.includes('Signal') ? val : num;
          });
          rows.push(row);
        }
      }
      cachedData = rows;
      console.log(`[Server] Loaded ${cachedData.length} records into memory.`);
    }
  } catch (err) {
    console.error('[Server] Error loading dataset cache:', err.message);
  }
}

// Initial load
loadData();

const MIME_TYPES = {
  '.html': 'text/html',
  '.css': 'text/css',
  '.js': 'application/javascript',
  '.json': 'application/json',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.svg': 'image/svg+xml',
  '.csv': 'text/csv'
};

function sendJSON(res, statusCode, data) {
  res.writeHead(statusCode, {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type'
  });
  res.end(JSON.stringify(data));
}

const server = http.createServer((req, res) => {
  const parsedUrl = url.parse(req.url, true);
  const pathname = parsedUrl.pathname;

  // Enable CORS Preflight
  if (req.method === 'OPTIONS') {
    res.writeHead(204, {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type'
    });
    return res.end();
  }

  // REST API 1: /api/tickers
  if (pathname === '/api/tickers' && req.method === 'GET') {
    if (!cachedSummary) loadData();
    return sendJSON(res, 200, {
      status: 'success',
      tickers: Object.keys(cachedSummary || {}),
      summary: cachedSummary
    });
  }

  // REST API 2: /api/stocks/:ticker
  if (pathname.startsWith('/api/stocks/') && req.method === 'GET') {
    const ticker = pathname.replace('/api/stocks/', '').toUpperCase();
    if (!cachedData) loadData();

    const stockRows = cachedData.filter(r => r.Ticker === ticker);
    if (stockRows.length === 0) {
      return sendJSON(res, 404, { status: 'error', message: `Ticker ${ticker} not found.` });
    }

    const summary = cachedSummary ? cachedSummary[ticker] : null;
    return sendJSON(res, 200, {
      status: 'success',
      ticker,
      count: stockRows.length,
      summary,
      data: stockRows
    });
  }

  // REST API 3: /api/comparison
  if (pathname === '/api/comparison' && req.method === 'GET') {
    if (!cachedData) loadData();

    const tickers = Object.keys(cachedSummary || {});
    const comparisonSeries = {};

    tickers.forEach(t => {
      const rows = cachedData.filter(r => r.Ticker === t);
      comparisonSeries[t] = rows.map(r => ({
        date: r.Date,
        close: r.Close,
        normalized: r.Normalized_100,
        daily_return: r.Daily_Return,
        volatility_50d: r.Annualized_Vol_50d
      }));
    });

    return sendJSON(res, 200, {
      status: 'success',
      summary: cachedSummary,
      series: comparisonSeries
    });
  }

  // REST API 4: /api/correlation
  if (pathname === '/api/correlation' && req.method === 'GET') {
    if (!cachedCorrelation) loadData();
    return sendJSON(res, 200, {
      status: 'success',
      correlation: cachedCorrelation
    });
  }

  // REST API 5: /api/export/tableau-csv
  if (pathname === '/api/export/tableau-csv' && req.method === 'GET') {
    if (fs.existsSync(CSV_FILE)) {
      res.writeHead(200, {
        'Content-Type': 'text/csv',
        'Content-Disposition': 'attachment; filename="tableau_stock_analytics.csv"'
      });
      return fs.createReadStream(CSV_FILE).pipe(res);
    } else {
      res.writeHead(404, { 'Content-Type': 'text/plain' });
      return res.end('CSV Export not found.');
    }
  }

  // REST API 6: /api/pipeline/run
  if (pathname === '/api/pipeline/run' && req.method === 'POST') {
    const scriptPath = path.join(BASE_DIR, 'bigdata_pipeline', 'standalone_analytics.py');
    const pythonBin = path.join(BASE_DIR, 'venv', 'bin', 'python3');
    const pyCmd = fs.existsSync(pythonBin) ? pythonBin : 'python3';

    exec(`${pyCmd} ${scriptPath}`, (error, stdout, stderr) => {
      if (error) {
        return sendJSON(res, 500, { status: 'error', message: error.message, stderr });
      }
      loadData();
      return sendJSON(res, 200, { status: 'success', message: 'Big Data Pipeline executed successfully!', output: stdout });
    });
    return;
  }

  // Serve Static Frontend Assets
  let reqPath = pathname === '/' ? '/index.html' : pathname;
  let filePath = path.join(PUBLIC_DIR, reqPath);

  fs.stat(filePath, (err, stats) => {
    if (err || !stats.isFile()) {
      res.writeHead(404, { 'Content-Type': 'text/plain' });
      return res.end('404 Not Found');
    }

    const ext = path.extname(filePath).toLowerCase();
    const contentType = MIME_TYPES[ext] || 'application/octet-stream';

    res.writeHead(200, { 'Content-Type': contentType });
    fs.createReadStream(filePath).pipe(res);
  });
});

server.listen(PORT, () => {
  console.log(`[+] Stock Big Data Analytics Dashboard Server running on http://localhost:${PORT}`);
});
