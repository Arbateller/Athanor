from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fetcher.cache import cache
from fetcher.fetcher import fetch_single_stock

app = FastAPI(title='Stock Market API')

app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])

@app.get('/')
def root():
    return {'status': 'running', 'redis': cache.is_connected()}

@app.get('/stock/{ticker}')
def get_stock(ticker: str):
    ticker = ticker.upper()
    cached = cache.get_stock(ticker)
    if cached:
        cached['source'] = 'cache'
        return cached
    data = fetch_single_stock(ticker)
    if not data:
        raise HTTPException(status_code=404, detail=f'Ticker {ticker} not found')
    cache.set_stock(ticker, data)
    data['source'] = 'live'
    return data

@app.get('/stocks')
def get_all_stocks():
    cached = cache.get_all_stocks()
    return {'stocks': cached or {}, 'count': len(cached) if cached else 0}

@app.get('/stocks/list')
def get_stocks_list():
    cached = cache.get_all_stocks()
    if not cached:
        return []
    return [{'Ticker': v['ticker'], 'Name': v['name'], 'Price': v['price'],
             'Change': v['change'], 'Change %': v['change_pct'],
             'High': v['high'], 'Low': v['low'], 'Volume': v['volume'],
             'Last Updated': v['fetched_at']} for v in cached.values()]
