# 📈 Stock Market Data Pipeline
### Complete Setup Guide — From Zero to Live Data

---

## 📁 Project Structure

```
stock_project/
├── config/
│   └── .env.example        ← Copy to .env and configure
├── fetcher/
│   ├── fetcher.py          ← Pulls data from Yahoo Finance
│   └── cache.py            ← Redis cache manager
├── api/
│   └── main.py             ← FastAPI REST server
├── dashboard/
│   └── index.html          ← Web dashboard (open in browser)
├── excel/
│   └── StockFetcher.bas    ← Excel VBA macro
└── requirements.txt        ← Python dependencies
```

---

## 🛠 STEP 1 — Install Required Software

### A. Python 3.11+
Download from: https://www.python.org/downloads/
→ ✅ Check "Add Python to PATH" during install

### B. VS Code (Recommended IDE)
Download from: https://code.visualstudio.com/
Extensions to install:
- Python (Microsoft)
- Pylance
- REST Client

### C. Redis
**Windows:**
1. Download Redis for Windows: https://github.com/microsoftarchive/redis/releases
2. Or use WSL: `wsl --install` then `sudo apt install redis-server`
3. Start it: `redis-server`

**Mac:**
```bash
brew install redis
brew services start redis
```

---

## 🐍 STEP 2 — Set Up Python Environment

Open a terminal in VS Code (Ctrl+`) and run:

```bash
# Navigate to project folder
cd stock_project

# Create virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install all dependencies
pip install -r requirements.txt
```

---

## ⚙️ STEP 3 — Configure Your Settings

```bash
# Copy example config
cp config/.env.example config/.env
```

Open `config/.env` and edit:
```
TRACKED_STOCKS=AAPL,GOOGL,MSFT,TSLA,AMZN   ← Your stocks
FETCH_INTERVAL=60                             ← How often to fetch (seconds)
REDIS_HOST=localhost                          ← Redis location
```

---

## 🔴 STEP 4 — Start Redis

```bash
# Windows (if installed as service)
redis-server

# Mac
brew services start redis

# Test it's running:
redis-cli ping
# Should return: PONG
```

---

## 📡 STEP 5 — Start the Fetcher Service

Open a **new terminal** (keep it running):

```bash
cd stock_project
source venv/bin/activate   # or venv\Scripts\activate on Windows
python fetcher/fetcher.py
```

You should see:
```
==================================================
   📈 Stock Fetcher Service Starting...
==================================================
[Fetcher] ✅ Redis connected
[Fetcher] 📊 Tracking: AAPL, GOOGL, MSFT, TSLA...
[Fetcher] ⏱  Fetch interval: 60s
--------------------------------------------------
[Fetcher] ✅ AAPL   $185.23    +0.45%
[Fetcher] ✅ GOOGL  $141.80    -0.12%
...
```

---

## 🌐 STEP 6 — Start the API Server

Open another **new terminal**:

```bash
cd stock_project
source venv/bin/activate
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

Test it:
- Open browser → http://localhost:8000
- View all stocks → http://localhost:8000/stocks
- Single stock → http://localhost:8000/stock/AAPL
- History → http://localhost:8000/stock/AAPL/history
- Auto-docs → http://localhost:8000/docs  ← Very useful!

---

## 📊 STEP 7A — Connect Excel (Power Query)

This is the EASIEST and most reliable way to get data into Excel:

1. Open Excel
2. Click **Data** tab → **Get Data** → **From Other Sources** → **From Web**
3. Enter URL: `http://localhost:8000/stocks/list`
4. Click OK → Power Query opens
5. Click **"List"** in the left panel
6. Click **"To Table"** button
7. Expand the record columns (click the expand icon)
8. Click **Close & Load**
9. Data appears as a formatted table! ✅

**To refresh:** Right-click the table → **Refresh**
**Auto refresh:** Data → Queries & Connections → right-click → Properties → set refresh interval

---

## 📊 STEP 7B — Connect Excel (VBA Macro)

For more control with VBA:

1. Open Excel → Press **Alt+F11** (VBA Editor)
2. Click **Insert** → **Module**
3. Open `excel/StockFetcher.bas` and paste the contents
4. Press **F5** or click Run → **FetchAllStocks**

---

## 🖥️ STEP 7C — Web Dashboard

Simply open `dashboard/index.html` in your browser!

It will:
- Auto-load all tracked stocks as cards
- Show a sortable data table
- Refresh every 60 seconds automatically
- Allow manual ticker lookup

---

## 🔧 Common Issues

| Problem | Solution |
|---------|----------|
| `redis.ConnectionError` | Start Redis: `redis-server` |
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` |
| Empty data in Excel | Make sure fetcher.py is running |
| API not reachable | Check uvicorn is running on port 8000 |
| yfinance rate limit | Reduce fetch frequency (FETCH_INTERVAL=120) |

---

## 🚀 Running Everything (Quick Reference)

Open 2 terminals simultaneously:

**Terminal 1 — Fetcher:**
```bash
cd stock_project && source venv/bin/activate
python fetcher/fetcher.py
```

**Terminal 2 — API:**
```bash
cd stock_project && source venv/bin/activate
uvicorn api.main:app --reload --port 8000
```

Then open `dashboard/index.html` in browser or connect Excel.

---

## 📈 API Endpoints Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |
| GET | `/stocks` | All tracked stocks |
| GET | `/stocks/list` | Flat list (for Excel) |
| GET | `/stock/{ticker}` | Single stock |
| GET | `/stock/{ticker}?force_refresh=true` | Bypass cache |
| GET | `/stock/{ticker}/history?period=1mo` | Price history |
| GET | `/docs` | Interactive API docs |
