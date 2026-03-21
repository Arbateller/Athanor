"""
main.py - FastAPI REST API
Exposes stock data from Redis cache as HTTP endpoints.

Run with:
    uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

API Docs available at:
    http://localhost:8000/docs
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fetcher.cache import cache
from fetcher.fetcher import fetch_single_stock

app = FastAPI(
    title="Stock Market API",
    description="Real-time stock data API powered by Yahoo Finance + Redis",
    version="1.0.0",
)

# Allow all origins (needed for Excel Power Query and web dashboard)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Models ───────────────────────────────────────────────────────────────────

class StockResponse(BaseModel):
    ticker: str
    name: str
    price: float
    open: float
    high: float
    low: float
    prev_close: float
    change: float
    change_pct: float
    volume: int
    market_cap: Optional[int]
    pe_ratio: Optional[float]
    week_52_high: float
    week_52_low: float
    currency: str
    exchange: str
    fetched_at: str
    source: str  # "cache" or "live"


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
def root():
    """Health check endpoint."""
    return {
        "status": "running",
        "service": "Stock Market API",
        "redis": "connected" if cache.is_connected() else "disconnected",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
def health():
    """Detailed health check."""
    return {
        "api": "ok",
        "redis": cache.is_connected(),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@app.get("/stock/{ticker}", tags=["Stocks"])
def get_stock(ticker: str, force_refresh: bool = False):
    """
    Get current stock data for a single ticker.

    - **ticker**: Stock symbol (e.g. AAPL, TSLA, MSFT)
    - **force_refresh**: Set to true to skip cache and fetch live
    """
    ticker = ticker.upper().strip()

    # Try cache first (unless force refresh)
    if not force_refresh:
        cached = cache.get_stock(ticker)
        if cached:
            cached["source"] = "cache"
            cached["52w_high"] = cached.pop("52w_high", 0)
            cached["52w_low"] = cached.pop("52w_low", 0)
            return cached

    # Cache miss — fetch live
    data = fetch_single_stock(ticker)
    if not data:
        raise HTTPException(
            status_code=404,
            detail=f"Could not fetch data for ticker '{ticker}'. Check the symbol is valid."
        )

    # Store in cache for next request
    cache.set_stock(ticker, data)
    data["source"] = "live"
    return data


@app.get("/stocks", tags=["Stocks"])
def get_all_stocks():
    """
    Get all currently tracked stocks.
    Returns cached data if available.
    """
    cached = cache.get_all_stocks()
    if cached:
        return {
            "count": len(cached),
            "source": "cache",
            "stocks": cached,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

    return {
        "count": 0,
        "source": "cache",
        "stocks": {},
        "message": "No data yet. Make sure the fetcher service is running.",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@app.get("/stocks/list", tags=["Stocks"])
def get_stocks_flat():
    """
    Get all stocks as a flat list.
    This format is optimized for Excel Power Query import.
    """
    cached = cache.get_all_stocks()
    if not cached:
        return []

    result = []
    for ticker, data in cached.items():
        indicators = data.get("indicators") or {}
        result.append({
            "Ticker":        data.get("ticker", ticker),
            "Name":          data.get("name", ""),
            "Price":         data.get("price", 0),
            "Change":        data.get("change", 0),
            "Change %":      data.get("change_pct", 0),
            "Open":          data.get("open", 0),
            "High":          data.get("high", 0),
            "Low":           data.get("low", 0),
            "Prev Close":    data.get("prev_close", 0),
            "Volume":        data.get("volume", 0),
            "Market Cap":    data.get("market_cap", 0),
            "52W High":      data.get("52w_high", 0),
            "52W Low":       data.get("52w_low", 0),
            "RSI 14":        indicators.get("rsi_14", None),
            "MACD Line":     indicators.get("macd_line", None),
            "MACD Signal":   indicators.get("macd_signal", None),
            "MACD Hist":     indicators.get("macd_hist", None),
            "Signal":        data.get("signal", "UNKNOWN"),
            "Signal Reason": data.get("signal_reason", ""),
            "Currency":      data.get("currency", "USD"),
            "Exchange":      data.get("exchange", ""),
            "Last Updated":  data.get("fetched_at", ""),
        })

    return result


@app.get("/stock/{ticker}/history", tags=["Stocks"])
def get_stock_history(ticker: str, period: str = "1mo", interval: str = "1d"):
    """
    Get historical price data for a ticker.

    - **period**: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y
    - **interval**: 1m, 5m, 15m, 1h, 1d, 1wk, 1mo
    """
    import yfinance as yf

    try:
        stock = yf.Ticker(ticker.upper())
        hist = stock.history(period=period, interval=interval)

        if hist.empty:
            raise HTTPException(status_code=404, detail=f"No history found for {ticker}")

        records = []
        for date, row in hist.iterrows():
            records.append({
                "date": str(date)[:10],
                "open": round(row["Open"], 2),
                "high": round(row["High"], 2),
                "low": round(row["Low"], 2),
                "close": round(row["Close"], 2),
                "volume": int(row["Volume"]),
            })

        return {
            "ticker": ticker.upper(),
            "period": period,
            "interval": interval,
            "count": len(records),
            "data": records,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
