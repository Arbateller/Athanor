"""
fetcher.py - Stock Data Fetcher (yfinance 1.2.0 compatible)
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

        return {
            "ticker":     ticker.upper(),
            "name":       ticker.upper(),
            "price":      round(price, 2),
            "open":       round(open_, 2),
            "high":       round(high, 2),
            "low":        round(low, 2),
            "prev_close": round(prev_close, 2),
            "change":     change,
            "change_pct": change_pct,
            "volume":     int(volume),
            "market_cap": int(market_cap),
            "pe_ratio":   None,
            "52w_high":   round(year_high, 2),
            "52w_low":    round(year_low, 2),
            "currency":   currency,
            "exchange":   exchange,
            "fetched_at": datetime.utcnow().isoformat() + "Z",
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
            print(f"[Fetcher] ✅ {ticker:<6} ${data['price']:<10} {sign}{data['change_pct']}%")
        else:
            print(f"[Fetcher] ❌ {ticker} - Failed")
        time.sleep(1)

    if all_data:
        cache.set_all_stocks(all_data)

    print(f"[Fetcher] Done: {success_count}/{len(TRACKED_STOCKS)} stocks updated\n")


def main():
    print("=" * 50)
    print("   📈 Stock Fetcher Service Starting...")
    print("=" * 50)

    if not cache.is_connected():
        print("[Fetcher] ❌ Cannot connect to Redis! Start it first.")
        sys.exit(1)

    print(f"[Fetcher] ✅ Redis connected")
    print(f"[Fetcher] 📊 Tracking: {', '.join(TRACKED_STOCKS)}")
    print(f"[Fetcher] ⏱  Fetch interval: {FETCH_INTERVAL}s")
    print("-" * 50)

    fetch_all_stocks()
    schedule.every(FETCH_INTERVAL).seconds.do(fetch_all_stocks)

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()
