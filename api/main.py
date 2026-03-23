"""
main.py - FastAPI REST API
Run with:
    uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import os
import sys
import math
import numpy as np

def safe_float(val):
    try:
        v = float(val)
        return 0.0 if math.isnan(v) or math.isinf(v) else v
    except:
        return 0.0

def safe_int(val):
    try:
        v = float(val)
        return 0 if math.isnan(v) or math.isinf(v) else int(v)
    except:
        return 0

def clean(val):
    """Return None if NaN/Inf, else rounded float."""
    if val is None:
        return None
    try:
        v = float(val)
        return None if (math.isnan(v) or math.isinf(v)) else round(v, 4)
    except:
        return None

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fetcher"))

from cache import cache

app = FastAPI(title="Stock Market API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── HEALTH ───────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "status":    "running",
        "redis":     cache.is_connected(),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "docs":      "/docs",
    }


# ─── STOCKS ───────────────────────────────────────────────────────────────────

@app.get("/stocks")
def get_all_stocks():
    cached = cache.get_all_stocks()
    return {
        "count":     len(cached) if cached else 0,
        "stocks":    cached or {},
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@app.get("/stocks/list")
def get_stocks_flat():
    cached = cache.get_all_stocks()
    if not cached:
        return []

    result = []
    for ticker, data in cached.items():
        try:
            result.append({
                "Ticker":        str(data.get("ticker", ticker) or ticker),
                "Name":          str(data.get("name", ticker) or ticker),
                "Price":         safe_float(data.get("price")),
                "Change":        safe_float(data.get("change")),
                "Change %":      safe_float(data.get("change_pct")),
                "Open":          safe_float(data.get("open")),
                "High":          safe_float(data.get("high")),
                "Low":           safe_float(data.get("low")),
                "Prev Close":    safe_float(data.get("prev_close")),
                "Volume":        safe_int(data.get("volume")),
                "Market Cap":    safe_int(data.get("market_cap")),
                "52W High":      safe_float(data.get("52w_high")),
                "52W Low":       safe_float(data.get("52w_low")),
                "Currency":      str(data.get("currency") or "USD"),
                "Exchange":      str(data.get("exchange") or ""),
                "Last Updated":  str(data.get("fetched_at") or ""),
            })
        except Exception as e:
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
            {
                "date":   str(d)[:10],
                "open":   round(r["Open"], 2),
                "high":   round(r["High"], 2),
                "low":    round(r["Low"], 2),
                "close":  round(r["Close"], 2),
                "volume": int(r["Volume"]),
            }
            for d, r in hist.iterrows()
        ]
        return {"ticker": ticker.upper(), "period": period, "count": len(records), "data": records}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── ON-DEMAND INDICATORS ─────────────────────────────────────────────────────

@app.get("/stock/{ticker}/compute-indicators")
def compute_indicators(
    ticker:     str,
    indicators: str = Query("RSI,MACD", description="Comma-separated: RSI,MACD,BB,SMA,EMA,STOCH,ATR,FIBONACCI"),
    period:     str = Query("3mo"),
    interval:   str = Query("1d"),
    sma_period: int = Query(20),
    ema_period: int = Query(20),
):
    import yfinance as yf

    ticker = ticker.upper().strip()
    requested = [i.strip().upper() for i in indicators.split(",")]

    try:
        hist = yf.Ticker(ticker).history(period=period, interval=interval)
        if hist.empty:
            raise HTTPException(status_code=404, detail=f"No history for {ticker}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    closes  = np.array(hist["Close"].values, dtype=float)
    highs   = np.array(hist["High"].values,  dtype=float)
    lows    = np.array(hist["Low"].values,   dtype=float)
    volumes = np.array(hist["Volume"].values, dtype=float)
    dates   = [str(d)[:10] for d in hist.index]
    n       = len(closes)

    # Base OHLCV
    base = [
        {
            "date":   dates[i],
            "open":   round(float(hist["Open"].values[i]), 2),
            "high":   round(float(highs[i]), 2),
            "low":    round(float(lows[i]), 2),
            "close":  round(float(closes[i]), 2),
            "volume": int(volumes[i]),
        }
        for i in range(n)
    ]

    result   = {"ticker": ticker, "period": period, "count": n, "data": base, "indicators": {}}
    ind_data = result["indicators"]

    # ── RSI ───────────────────────────────────────────────────────────────────
    if "RSI" in requested:
        period_rsi = 14
        rsi_vals   = [None] * n
        if n > period_rsi:
            deltas = np.diff(closes)
            gains  = np.where(deltas > 0, deltas, 0.0)
            losses = np.where(deltas < 0, -deltas, 0.0)
            avg_g  = np.mean(gains[:period_rsi])
            avg_l  = np.mean(losses[:period_rsi])
            for i in range(period_rsi, n):
                if i > period_rsi:
                    avg_g = (avg_g * (period_rsi - 1) + gains[i - 1]) / period_rsi
                    avg_l = (avg_l * (period_rsi - 1) + losses[i - 1]) / period_rsi
                rs           = avg_g / avg_l if avg_l != 0 else float("inf")
                rsi_vals[i]  = clean(100 - (100 / (1 + rs)))
        ind_data["RSI"] = {"period": period_rsi, "values": rsi_vals}

    # ── MACD ──────────────────────────────────────────────────────────────────
    if "MACD" in requested:
        def ema_series(arr, span):
            k   = 2 / (span + 1)
            out = [None] * len(arr)
            for i, v in enumerate(arr):
                if i == 0:
                    out[i] = v
                else:
                    out[i] = v * k + out[i - 1] * (1 - k)
            return out

        ema12    = ema_series(closes, 12)
        ema26    = ema_series(closes, 26)
        macd_l   = [clean(ema12[i] - ema26[i]) for i in range(n)]
        valid    = [v for v in macd_l if v is not None]
        signal_l = [None] * n
        if len(valid) >= 9:
            sig_raw  = ema_series([v for v in macd_l if v is not None], 9)
            sig_idx  = 0
            for i in range(n):
                if macd_l[i] is not None:
                    signal_l[i] = clean(sig_raw[sig_idx])
                    sig_idx += 1
        hist_l   = [clean(macd_l[i] - signal_l[i]) if macd_l[i] is not None and signal_l[i] is not None else None for i in range(n)]
        ind_data["MACD"] = {"macd": macd_l, "signal": signal_l, "histogram": hist_l}

    # ── Bollinger Bands ───────────────────────────────────────────────────────
    if "BB" in requested:
        bb_period = 20
        upper     = [None] * n
        middle    = [None] * n
        lower     = [None] * n
        for i in range(bb_period - 1, n):
            window  = closes[i - bb_period + 1:i + 1]
            m       = float(np.mean(window))
            std     = float(np.std(window))
            middle[i] = clean(m)
            upper[i]  = clean(m + 2 * std)
            lower[i]  = clean(m - 2 * std)
        ind_data["BB"] = {"period": bb_period, "upper": upper, "middle": middle, "lower": lower}

    # ── SMA ───────────────────────────────────────────────────────────────────
    if "SMA" in requested:
        sma = [None] * n
        for i in range(sma_period - 1, n):
            sma[i] = clean(float(np.mean(closes[i - sma_period + 1:i + 1])))
        ind_data["SMA"] = {"period": sma_period, "values": sma}

    # ── EMA ───────────────────────────────────────────────────────────────────
    if "EMA" in requested:
        k   = 2 / (ema_period + 1)
        ema = [None] * n
        for i in range(n):
            if i == 0:
                ema[i] = clean(float(closes[i]))
            else:
                prev   = ema[i - 1] if ema[i - 1] is not None else float(closes[i])
                ema[i] = clean(float(closes[i]) * k + prev * (1 - k))
        ind_data["EMA"] = {"period": ema_period, "values": ema}

    # ── Stochastic ────────────────────────────────────────────────────────────
    if "STOCH" in requested:
        stoch_period = 14
        k_vals       = [None] * n
        d_vals       = [None] * n
        for i in range(stoch_period - 1, n):
            h14    = float(np.max(highs[i - stoch_period + 1:i + 1]))
            l14    = float(np.min(lows[i - stoch_period + 1:i + 1]))
            if h14 != l14:
                k_vals[i] = clean((float(closes[i]) - l14) / (h14 - l14) * 100)
        valid_k = [v for v in k_vals if v is not None]
        if len(valid_k) >= 3:
            d_raw = []
            for i in range(len(valid_k)):
                if i >= 2:
                    d_raw.append(clean(np.mean(valid_k[i - 2:i + 1])))
                else:
                    d_raw.append(None)
            d_idx = 0
            for i in range(n):
                if k_vals[i] is not None:
                    d_vals[i] = d_raw[d_idx]
                    d_idx += 1
        ind_data["STOCH"] = {"period": stoch_period, "k": k_vals, "d": d_vals}

    # ── ATR ───────────────────────────────────────────────────────────────────
    if "ATR" in requested:
        atr_period = 14
        atr_vals   = [None] * n
        trs        = []
        for i in range(1, n):
            tr = max(
                float(highs[i])  - float(lows[i]),
                abs(float(highs[i])  - float(closes[i - 1])),
                abs(float(lows[i])   - float(closes[i - 1])),
            )
            trs.append(tr)
        if len(trs) >= atr_period:
            atr = float(np.mean(trs[:atr_period]))
            atr_vals[atr_period] = clean(atr)
            for i in range(atr_period + 1, n):
                atr = (atr * (atr_period - 1) + trs[i - 1]) / atr_period
                atr_vals[i] = clean(atr)
        ind_data["ATR"] = {"period": atr_period, "values": atr_vals}

    # ── Fibonacci ─────────────────────────────────────────────────────────────
    if "FIBONACCI" in requested:
        high_val = float(np.max(highs))
        low_val  = float(np.min(lows))
        diff     = high_val - low_val
        levels   = {
            "0.0":   round(high_val, 4),
            "0.236": round(high_val - 0.236 * diff, 4),
            "0.382": round(high_val - 0.382 * diff, 4),
            "0.5":   round(high_val - 0.5   * diff, 4),
            "0.618": round(high_val - 0.618 * diff, 4),
            "0.786": round(high_val - 0.786 * diff, 4),
            "1.0":   round(low_val, 4),
        }
        ind_data["FIBONACCI"] = {"high": round(high_val, 4), "low": round(low_val, 4), "levels": levels}

    return result
