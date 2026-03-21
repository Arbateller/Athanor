"""
main.py - FastAPI REST API (fixed + robust)
Run with:
    uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fetcher.cache import cache

app = FastAPI(title="Stock Market API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "status": "running",
        "redis": cache.is_connected(),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "docs": "/docs",
    }


@app.get("/stocks")
def get_all_stocks():
    cached = cache.get_all_stocks()
    return {
        "count": len(cached) if cached else 0,
        "stocks": cached or {},
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@app.get("/stocks/list")
def get_stocks_flat():
    """Flat list optimized for Excel Power Query."""
    cached = cache.get_all_stocks()
    if not cached:
        return []

    result = []
    for ticker, data in cached.items():
        try:
            indicators = data.get("indicators") or {}
            result.append({
                "Ticker":        str(data.get("ticker", ticker) or ticker),
                "Name":          str(data.get("name", ticker) or ticker),
                "Price":         float(data.get("price") or 0),
                "Change":        float(data.get("change") or 0),
                "Change %":      float(data.get("change_pct") or 0),
                "Open":          float(data.get("open") or 0),
                "High":          float(data.get("high") or 0),
                "Low":           float(data.get("low") or 0),
                "Prev Close":    float(data.get("prev_close") or 0),
                "Volume":        int(data.get("volume") or 0),
                "Market Cap":    int(data.get("market_cap") or 0),
                "52W High":      float(data.get("52w_high") or 0),
                "52W Low":       float(data.get("52w_low") or 0),
                "RSI 14":        float(indicators["rsi_14"]) if indicators.get("rsi_14") is not None else None,
                "MACD Line":     float(indicators["macd_line"]) if indicators.get("macd_line") is not None else None,
                "MACD Signal":   float(indicators["macd_signal"]) if indicators.get("macd_signal") is not None else None,
                "MACD Hist":     float(indicators["macd_hist"]) if indicators.get("macd_hist") is not None else None,
                "Signal":        str(data.get("signal") or "UNKNOWN"),
                "Signal Reason": str(data.get("signal_reason") or ""),
                "Currency":      str(data.get("currency") or "USD"),
                "Exchange":      str(data.get("exchange") or ""),
                "Last Updated":  str(data.get("fetched_at") or ""),
            })
        except Exception as e:
            # Skip broken entries, never crash the whole endpoint
            print(f"[API] Skipping {ticker}: {e}")
            continue

    return result


@app.get("/stock/{ticker}")
def get_stock(ticker: str):
    ticker = ticker.upper().strip()
    cached = cache.get_stock(ticker)
    if cached:
        return cached
    raise HTTPException(status_code=404, detail=f"No data for {ticker}. Is the fetcher running?")


@app.get("/stock/{ticker}/history")
def get_stock_history(ticker: str, period: str = "1mo", interval: str = "1d"):
    import yfinance as yf
    try:
        hist = yf.Ticker(ticker.upper()).history(period=period, interval=interval)
        if hist.empty:
            raise HTTPException(status_code=404, detail=f"No history for {ticker}")
        records = [
            {"date": str(d)[:10], "open": round(r["Open"], 2), "high": round(r["High"], 2),
             "low": round(r["Low"], 2), "close": round(r["Close"], 2), "volume": int(r["Volume"])}
            for d, r in hist.iterrows()
        ]
        return {"ticker": ticker.upper(), "period": period, "count": len(records), "data": records}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
