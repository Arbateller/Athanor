"""
fetcher.py - Stock Data Fetcher with RSI + MACD Indicators
Run from inside the fetcher/ folder:
    python fetcher.py
"""

import yfinance as yf
import schedule
import time
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "config", ".env"))

from cache import cache

TRACKED_STOCKS = os.getenv("TRACKED_STOCKS", "AAPL,GOOGL,MSFT,TSLA,AMZN").split(",")
FETCH_INTERVAL = int(os.getenv("FETCH_INTERVAL", 60))


# ─── INDICATORS ───────────────────────────────────────────────────────────────

def calculate_rsi(closes: list, period: int = 14) -> float | None:
    """Calculate RSI-14."""
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, period + 1):
        diff = closes[-(period + 1 - i + 1)] - closes[-(period + 1 - i + 2)]  
        if diff >= 0:
            gains.append(diff)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(diff))

    # Simpler calculation
    diffs = [closes[i] - closes[i - 1] for i in range(-period, 0)]
    gains = [d for d in diffs if d > 0]
    losses = [abs(d) for d in diffs if d < 0]

    avg_gain = sum(gains) / period if gains else 0
    avg_loss = sum(losses) / period if losses else 0

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


def calculate_ema(closes: list, period: int) -> list:
    """Calculate EMA for a given period."""
    if len(closes) < period:
        return []
    ema = [sum(closes[:period]) / period]
    multiplier = 2 / (period + 1)
    for price in closes[period:]:
        ema.append((price - ema[-1]) * multiplier + ema[-1])
    return ema


def calculate_macd(closes: list, fast: int = 12, slow: int = 26, signal: int = 9):
    """Calculate MACD line, signal line, and histogram."""
    if len(closes) < slow + signal:
        return None, None, None

    ema_fast = calculate_ema(closes, fast)
    ema_slow = calculate_ema(closes, slow)

    # Align lengths
    min_len = min(len(ema_fast), len(ema_slow))
    ema_fast = ema_fast[-min_len:]
    ema_slow = ema_slow[-min_len:]

    macd_line = [f - s for f, s in zip(ema_fast, ema_slow)]

    if len(macd_line) < signal:
        return None, None, None

    signal_line = calculate_ema(macd_line, signal)
    if not signal_line:
        return None, None, None

    histogram = macd_line[-1] - signal_line[-1]

    return (
        round(macd_line[-1], 4),
        round(signal_line[-1], 4),
        round(histogram, 4),
    )


def get_signal(rsi: float | None, macd_hist: float | None) -> dict:
    """
    Generate BUY / SELL / HOLD signal based on RSI + MACD.

    Rules:
      STRONG BUY  → RSI < 30 (oversold) AND MACD histogram > 0 (bullish momentum)
      BUY         → RSI < 45 AND MACD histogram > 0
      STRONG SELL → RSI > 70 (overbought) AND MACD histogram < 0 (bearish momentum)
      SELL        → RSI > 55 AND MACD histogram < 0
      HOLD        → Everything else
    """
    if rsi is None or macd_hist is None:
        return {"signal": "UNKNOWN", "reason": "Not enough data", "emoji": "❓"}

    bullish_macd = macd_hist > 0
    bearish_macd = macd_hist < 0

    if rsi < 30 and bullish_macd:
        return {
            "signal": "STRONG BUY",
            "reason": f"RSI {rsi} is oversold + MACD turning bullish",
            "emoji": "🟢🟢"
        }
    elif rsi < 45 and bullish_macd:
        return {
            "signal": "BUY",
            "reason": f"RSI {rsi} is low + MACD bullish momentum",
            "emoji": "🟢"
        }
    elif rsi > 70 and bearish_macd:
        return {
            "signal": "STRONG SELL",
            "reason": f"RSI {rsi} is overbought + MACD turning bearish",
            "emoji": "🔴🔴"
        }
    elif rsi > 55 and bearish_macd:
        return {
            "signal": "SELL",
            "reason": f"RSI {rsi} is high + MACD bearish momentum",
            "emoji": "🔴"
        }
    else:
        return {
            "signal": "HOLD",
            "reason": f"RSI {rsi} is neutral, no clear signal",
            "emoji": "🟡"
        }


# ─── FETCHER ──────────────────────────────────────────────────────────────────

def fetch_single_stock(ticker: str) -> dict | None:
    try:
        stock = yf.Ticker(ticker)
        fast = stock.fast_info

        price      = getattr(fast, "last_price", None) or 0
        open_      = getattr(fast, "open", None) or 0
        high       = getattr(fast, "day_high", None) or 0
        low        = getattr(fast, "day_low", None) or 0
        prev_close = getattr(fast, "previous_close", None) or 0
        volume     = getattr(fast, "last_volume", None) or 0
        market_cap = getattr(fast, "market_cap", None) or 0
        year_high  = getattr(fast, "year_high", None) or 0
        year_low   = getattr(fast, "year_low", None) or 0
        currency   = getattr(fast, "currency", "USD") or "USD"
        exchange   = getattr(fast, "exchange", "N/A") or "N/A"

        change = round(price - prev_close, 2) if price and prev_close else 0
        change_pct = round((change / prev_close) * 100, 2) if prev_close else 0

        # Fetch 60 days of history to calculate indicators
        hist = stock.history(period="60d", interval="1d")
        closes = list(hist["Close"].values) if not hist.empty else []

        rsi = calculate_rsi(closes) if len(closes) >= 15 else None
        macd_line, signal_line, macd_hist = calculate_macd(closes) if len(closes) >= 35 else (None, None, None)
        signal = get_signal(rsi, macd_hist)

        return {
            "ticker":      ticker.upper(),
            "name":        ticker.upper(),
            "price":       round(price, 2),
            "open":        round(open_, 2),
            "high":        round(high, 2),
            "low":         round(low, 2),
            "prev_close":  round(prev_close, 2),
            "change":      change,
            "change_pct":  change_pct,
            "volume":      int(volume),
            "market_cap":  int(market_cap),
            "pe_ratio":    None,
            "52w_high":    round(year_high, 2),
            "52w_low":     round(year_low, 2),
            "currency":    currency,
            "exchange":    exchange,
            "indicators": {
                "rsi_14":       rsi,
                "macd_line":    macd_line,
                "macd_signal":  signal_line,
                "macd_hist":    macd_hist,
            },
            "signal":      signal["signal"],
            "signal_emoji": signal["emoji"],
            "signal_reason": signal["reason"],
            "fetched_at":  datetime.utcnow().isoformat() + "Z",
        }

    except Exception as e:
        print(f"[Fetcher] ❌ Error fetching {ticker}: {e}")
        return None


def fetch_all_stocks():
    print(f"\n[Fetcher] 🔄 Fetching {len(TRACKED_STOCKS)} stocks at {datetime.now().strftime('%H:%M:%S')}")
    all_data = {}
    success_count = 0

    for ticker in TRACKED_STOCKS:
        ticker = ticker.strip().upper()
        data = fetch_single_stock(ticker)
        if data:
            cache.set_stock(ticker, data)
            all_data[ticker] = data
            success_count += 1
            sign = "+" if data["change"] >= 0 else ""
            print(
                f"[Fetcher] {data['signal_emoji']} {ticker:<10} "
                f"${data['price']:<10} {sign}{data['change_pct']}% | "
                f"RSI: {data['indicators']['rsi_14']} | "
                f"Signal: {data['signal']}"
            )
        else:
            print(f"[Fetcher] ❌ {ticker} - Failed")
        time.sleep(1)

    if all_data:
        cache.set_all_stocks(all_data)

    # Print alerts for actionable signals
    alerts = [
        d for d in all_data.values()
        if d["signal"] in ("BUY", "STRONG BUY", "SELL", "STRONG SELL")
    ]
    if alerts:
        print("\n" + "=" * 50)
        print("   ⚠️  ALERTS — Action Required")
        print("=" * 50)
        for a in alerts:
            print(f"  {a['signal_emoji']}  {a['ticker']:<10} {a['signal']:<12} → {a['signal_reason']}")
        print("=" * 50)

    print(f"\n[Fetcher] Done: {success_count}/{len(TRACKED_STOCKS)} stocks updated\n")


def main():
    print("=" * 50)
    print("   📈 Stock Fetcher with Indicators")
    print("=" * 50)

    if not cache.is_connected():
        print("[Fetcher] ❌ Cannot connect to Redis! Start it first.")
        sys.exit(1)

    print(f"[Fetcher] ✅ Redis connected")
    print(f"[Fetcher] 📊 Tracking: {', '.join(TRACKED_STOCKS)}")
    print(f"[Fetcher] ⏱  Fetch interval: {FETCH_INTERVAL}s")
    print(f"[Fetcher] 📐 Indicators: RSI-14, MACD (12/26/9)")
    print("-" * 50)

    fetch_all_stocks()
    schedule.every(FETCH_INTERVAL).seconds.do(fetch_all_stocks)

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()
