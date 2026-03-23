"""
fetcher.py - Parallel Stock Fetcher (price data only)
Indicators are computed on-demand via the API.
"""

import yfinance as yf
import schedule
import time
import os
import sys
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

PROJECT_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
load_dotenv(os.path.join(PROJECT_ROOT, "config", ".env"))

from cache import cache

TRACKED_STOCKS = [s.strip().upper() for s in os.getenv("TRACKED_STOCKS", "AAPL,MSFT").split(",")]
FETCH_INTERVAL = int(os.getenv("FETCH_INTERVAL", 300))
MAX_WORKERS    = int(os.getenv("MAX_WORKERS", 10))


# ─── FETCH ONE STOCK ──────────────────────────────────────────────────────────

def fetch_single_stock(ticker: str):
    try:
        stock      = yf.Ticker(ticker)
        fast       = stock.fast_info

        price      = getattr(fast, "last_price",      None) or 0
        open_      = getattr(fast, "open",             None) or 0
        high       = getattr(fast, "day_high",         None) or 0
        low        = getattr(fast, "day_low",          None) or 0
        prev_close = getattr(fast, "previous_close",   None) or 0
        volume     = getattr(fast, "last_volume",      None) or 0
        market_cap = getattr(fast, "market_cap",       None) or 0
        year_high  = getattr(fast, "year_high",        None) or 0
        year_low   = getattr(fast, "year_low",         None) or 0
        currency   = getattr(fast, "currency",         "USD") or "USD"
        exchange   = getattr(fast, "exchange",         "N/A") or "N/A"

        change     = round(price - prev_close, 2) if price and prev_close else 0
        change_pct = round((change / prev_close) * 100, 2) if prev_close else 0

        return {
            "ticker":     ticker,
            "name":       ticker,
            "price":      round(price, 2),
            "open":       round(open_, 2),
            "high":       round(high, 2),
            "low":        round(low, 2),
            "prev_close": round(prev_close, 2),
            "change":     change,
            "change_pct": change_pct,
            "volume":     int(volume),
            "market_cap": int(market_cap),
            "52w_high":   round(year_high, 2),
            "52w_low":    round(year_low, 2),
            "currency":   currency,
            "exchange":   exchange,
            "fetched_at": datetime.utcnow().isoformat() + "Z",
        }

    except Exception as e:
        print(f"[Fetcher] ERROR {ticker}: {e}")
        return None


# ─── PARALLEL FETCH ALL ───────────────────────────────────────────────────────

def fetch_all_stocks():
    start   = datetime.now()
    total   = len(TRACKED_STOCKS)
    print(f"\n[Fetcher] Fetching {total} stocks with {MAX_WORKERS} workers...")

    all_data = {}
    success  = 0
    failed   = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(fetch_single_stock, t): t for t in TRACKED_STOCKS}

        for future in as_completed(futures):
            ticker = futures[future]
            try:
                data = future.result()
                if data:
                    cache.set_stock(ticker, data)
                    all_data[ticker] = data
                    success += 1
                    sign = "+" if data["change"] >= 0 else ""
                    print(f"  OK {ticker:<12} ${data['price']:<10} {sign}{data['change_pct']}%")
                else:
                    failed += 1
                    print(f"  FAIL {ticker} - No data")
            except Exception as e:
                failed += 1
                print(f"  FAIL {ticker} - {e}")

    if all_data:
        cache.set_all_stocks(all_data)

    elapsed = (datetime.now() - start).seconds
    print(f"\n[Fetcher] {success}/{total} stocks fetched in {elapsed}s ({failed} failed)")


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 55)
    print("   Stock Fetcher - Parallel Mode (indicators on-demand)")
    print("=" * 55)

    if not cache.is_connected():
        print("ERROR: Redis not connected. Run: redis-server")
        sys.exit(1)

    print(f"Redis connected")
    print(f"Tracking {len(TRACKED_STOCKS)} stocks")
    print(f"Workers: {MAX_WORKERS} parallel threads")
    print(f"Interval: every {FETCH_INTERVAL}s")
    print("-" * 55)

    fetch_all_stocks()
    schedule.every(FETCH_INTERVAL).seconds.do(fetch_all_stocks)

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()
