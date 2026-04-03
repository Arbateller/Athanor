"""
simulation.py — Backtesting / simulation logic
Imported by main.py
"""

from __future__ import annotations
import numpy as np
import math
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict
import yfinance as yf


def _clean(v):
    if v is None: return None
    try:
        f = float(v)
        return None if (math.isnan(f) or math.isinf(f)) else round(f, 4)
    except: return None


# ─── SINGLE POSITION ──────────────────────────────────────────────────────────

def simulate_position(
    ticker:    str,
    buy_date:  str,          # "YYYY-MM-DD"
    quantity:  float,        # lots / shares
    sell_date: Optional[str] = None,  # None = today
) -> Dict:
    """
    Simulate holding `quantity` shares of `ticker` from buy_date to sell_date.
    Returns day-by-day portfolio value and summary metrics.
    """
    ticker = ticker.upper().strip()

    # Fetch full history from buy_date to today
    end_dt  = datetime.strptime(sell_date, "%Y-%m-%d") if sell_date else datetime.utcnow()
    start_dt = datetime.strptime(buy_date, "%Y-%m-%d") - timedelta(days=5)  # buffer for weekends

    hist = yf.Ticker(ticker).history(
        start=start_dt.strftime("%Y-%m-%d"),
        end=(end_dt + timedelta(days=1)).strftime("%Y-%m-%d"),
        interval="1d",
        auto_adjust=True,
    )

    if hist.empty:
        raise ValueError(f"No price data for {ticker} in the given date range.")

    # Filter to buy_date onward
    hist.index = hist.index.tz_localize(None) if hist.index.tzinfo else hist.index
    buy_dt     = datetime.strptime(buy_date, "%Y-%m-%d")
    hist       = hist[hist.index >= buy_dt]

    if hist.empty:
        raise ValueError(f"No data for {ticker} on or after {buy_date}.")

    closes = hist["Close"].values
    dates  = [str(d)[:10] for d in hist.index]

    buy_price    = float(closes[0])
    current_price = float(closes[-1])
    cost_basis   = buy_price * quantity

    # Day-by-day series
    series = []
    peak   = cost_basis
    max_dd = 0.0

    for i, (d, c) in enumerate(zip(dates, closes)):
        val        = float(c) * quantity
        pnl        = val - cost_basis
        pnl_pct    = (pnl / cost_basis) * 100 if cost_basis else 0
        peak       = max(peak, val)
        drawdown   = ((peak - val) / peak) * 100 if peak else 0
        max_dd     = max(max_dd, drawdown)
        series.append({
            "date":      d,
            "price":     round(float(c), 4),
            "value":     round(val, 2),
            "pnl":       round(pnl, 2),
            "pnl_pct":   round(pnl_pct, 2),
            "drawdown":  round(drawdown, 2),
        })

    total_pnl     = (current_price - buy_price) * quantity
    total_pnl_pct = ((current_price - buy_price) / buy_price) * 100 if buy_price else 0
    peak_value    = max(s["value"] for s in series)
    lowest_value  = min(s["value"] for s in series)
    peak_date     = series[[s["value"] for s in series].index(peak_value)]["date"]
    low_date      = series[[s["value"] for s in series].index(lowest_value)]["date"]

    return {
        "ticker":         ticker,
        "buy_date":       dates[0],
        "buy_price":      round(buy_price, 4),
        "current_price":  round(current_price, 4),
        "quantity":       quantity,
        "cost_basis":     round(cost_basis, 2),
        "current_value":  round(current_price * quantity, 2),
        "total_pnl":      round(total_pnl, 2),
        "total_pnl_pct":  round(total_pnl_pct, 2),
        "peak_value":     round(peak_value, 2),
        "peak_date":      peak_date,
        "lowest_value":   round(lowest_value, 2),
        "low_date":       low_date,
        "max_drawdown":   round(max_dd, 2),
        "days_held":      len(series),
        "series":         series,
    }


# ─── PORTFOLIO ────────────────────────────────────────────────────────────────

def simulate_portfolio(positions: List[Dict]) -> Dict:
    """
    Simulate a multi-stock portfolio.
    Each position: { ticker, buy_date, quantity, sell_date? }
    Returns merged day-by-day portfolio value.
    """
    results   = []
    errors    = []
    all_dates = set()

    for pos in positions:
        try:
            r = simulate_position(
                ticker    = pos["ticker"],
                buy_date  = pos["buy_date"],
                quantity  = pos["quantity"],
                sell_date = pos.get("sell_date"),
            )
            results.append(r)
            for s in r["series"]:
                all_dates.add(s["date"])
        except Exception as e:
            errors.append({"ticker": pos["ticker"], "error": str(e)})

    if not results:
        raise ValueError("No valid positions could be simulated.")

    # Build merged daily series
    sorted_dates = sorted(all_dates)
    date_value: Dict[str, float] = {d: 0.0 for d in sorted_dates}
    date_cost:  Dict[str, float] = {d: 0.0 for d in sorted_dates}

    total_cost = 0.0
    for r in results:
        total_cost += r["cost_basis"]
        series_map  = {s["date"]: s["value"] for s in r["series"]}
        last_val    = r["cost_basis"]
        for d in sorted_dates:
            if d in series_map:
                last_val = series_map[d]
            date_value[d] += last_val
            date_cost[d]  += r["cost_basis"]

    # Build portfolio series
    portfolio_series = []
    peak    = total_cost
    max_dd  = 0.0

    for d in sorted_dates:
        val      = date_value[d]
        pnl      = val - total_cost
        pnl_pct  = (pnl / total_cost) * 100 if total_cost else 0
        peak     = max(peak, val)
        drawdown = ((peak - val) / peak) * 100 if peak else 0
        max_dd   = max(max_dd, drawdown)
        portfolio_series.append({
            "date":     d,
            "value":    round(val, 2),
            "pnl":      round(pnl, 2),
            "pnl_pct":  round(pnl_pct, 2),
            "drawdown": round(drawdown, 2),
        })

    final       = portfolio_series[-1] if portfolio_series else {}
    peak_value  = max(s["value"] for s in portfolio_series) if portfolio_series else 0
    low_value   = min(s["value"] for s in portfolio_series) if portfolio_series else 0
    peak_date   = next((s["date"] for s in portfolio_series if s["value"] == peak_value), None)
    low_date    = next((s["date"] for s in portfolio_series if s["value"] == low_value),  None)

    return {
        "total_cost":      round(total_cost, 2),
        "current_value":   round(final.get("value", 0), 2),
        "total_pnl":       round(final.get("pnl", 0), 2),
        "total_pnl_pct":   round(final.get("pnl_pct", 0), 2),
        "peak_value":      round(peak_value, 2),
        "peak_date":       peak_date,
        "lowest_value":    round(low_value, 2),
        "low_date":        low_date,
        "max_drawdown":    round(max_dd, 2),
        "days":            len(portfolio_series),
        "series":          portfolio_series,
        "positions":       results,
        "errors":          errors,
    }


# ─── SIGNAL SNAPSHOT (what signals were active on buy_date) ───────────────────

def signal_snapshot(
    ticker:     str,
    on_date:    str,
    rules:      List[Dict],   # [{formula, signal}]
    sma_period: int = 20,
    ema_period: int = 20,
) -> Dict:
    """
    Compute indicator values as of `on_date` and evaluate scanner rules.
    Returns what signals would have been triggered on that date.
    """
    from adapters import compute, REGISTRY
    import re

    ticker = ticker.upper().strip()
    end_dt  = datetime.strptime(on_date, "%Y-%m-%d") + timedelta(days=1)
    start_dt = datetime.strptime(on_date, "%Y-%m-%d") - timedelta(days=365)

    hist = yf.Ticker(ticker).history(
        start=start_dt.strftime("%Y-%m-%d"),
        end=end_dt.strftime("%Y-%m-%d"),
        interval="1d",
        auto_adjust=True,
    )

    if hist.empty:
        return {"date": on_date, "signals": [], "values": {}, "error": "No data"}

    hist.index = hist.index.tz_localize(None) if hist.index.tzinfo else hist.index

    closes = np.array(hist["Close"].values, dtype=float)
    highs  = np.array(hist["High"].values,  dtype=float)
    lows   = np.array(hist["Low"].values,   dtype=float)

    # Figure out which adapters we need
    all_text = " ".join(r["formula"] for r in rules)
    needed   = []
    for name, adapter in REGISTRY.items():
        for var in adapter.VARIABLES:
            if re.search(r'\b' + var + r'\b', all_text):
                needed.append(name)
                break

    params = {"SMA": {"period": sma_period}, "EMA": {"period": ema_period}}
    values = compute(needed, closes, highs, lows, params)

    # Add price info
    values["PRICE"]      = _clean(float(closes[-1]))
    values["CHANGE_PCT"] = _clean(((closes[-1] - closes[-2]) / closes[-2] * 100) if len(closes) > 1 else 0)

    SIGNAL_PRIORITY = {"STRONG BUY": 5, "BUY": 4, "HOLD": 3, "SELL": 2, "STRONG SELL": 1}

    def _eval(formula, vals):
        expr = re.sub(r'\bAND\b', 'and', formula.strip())
        expr = re.sub(r'\bOR\b',  'or',  expr)
        for name, val in sorted(vals.items(), key=lambda x: -len(x[0])):
            expr = re.sub(r'\b' + name + r'\b',
                          'None' if val is None else str(round(float(val), 6)), expr)
        if re.search(r'[a-zA-Z_]\w*\s*\(', expr): return False
        try: return bool(eval(expr, {"__builtins__": {}, "None": None}))
        except: return False

    triggered = []
    for rule in rules:
        if _eval(rule["formula"], values):
            sig = rule["signal"].upper()
            triggered.append({"formula": rule["formula"], "signal": sig,
                               "priority": SIGNAL_PRIORITY.get(sig, 0)})

    best = max(triggered, key=lambda x: x["priority"]) if triggered else None

    return {
        "date":             on_date,
        "price_on_date":    _clean(float(closes[-1])),
        "signal":           best["signal"] if best else None,
        "triggered_rules":  triggered,
        "values":           {k: (round(v, 4) if v is not None else None) for k, v in values.items()},
    }
