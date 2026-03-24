"""
main.py - FastAPI REST API v3 (multi-rule scanner)
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import os, sys, math, re, time
import numpy as np

def safe_float(val):
    try:
        v = float(val)
        return 0.0 if math.isnan(v) or math.isinf(v) else v
    except: return 0.0

def safe_int(val):
    try:
        v = float(val)
        return 0 if math.isnan(v) or math.isinf(v) else int(v)
    except: return 0

def clean(val):
    if val is None: return None
    try:
        v = float(val)
        return None if (math.isnan(v) or math.isinf(v)) else round(v, 4)
    except: return None

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fetcher"))
from cache import cache

app = FastAPI(title="Stock Market API", version="3.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Signal priority — higher = stronger/more important
SIGNAL_PRIORITY = {
    "STRONG BUY":  5,
    "BUY":         3,
    "HOLD":        1,
    "SELL":        2,
    "STRONG SELL": 4,
}

# ─── SHARED INDICATOR ENGINE ──────────────────────────────────────────────────

def _compute_indicators_into(ind_data, requested, closes, highs, lows, n, sma_period=20, ema_period=20):
    if "RSI" in requested:
        p = 14; rsi_vals = [None]*n
        if n > p:
            d = np.diff(closes)
            g = np.where(d>0,d,0.0); l = np.where(d<0,-d,0.0)
            ag = np.mean(g[:p]); al = np.mean(l[:p])
            for i in range(p,n):
                if i>p:
                    ag=(ag*(p-1)+g[i-1])/p; al=(al*(p-1)+l[i-1])/p
                rs=ag/al if al!=0 else float('inf')
                rsi_vals[i]=clean(100-(100/(1+rs)))
        ind_data["RSI"]={"period":p,"values":rsi_vals}

    if "MACD" in requested:
        def ema_s(arr,span):
            k=2/(span+1); out=[None]*len(arr)
            for i,v in enumerate(arr): out[i]=v*k+out[i-1]*(1-k) if i>0 else v
            return out
        e12=ema_s(closes,12); e26=ema_s(closes,26)
        ml=[clean(e12[i]-e26[i]) for i in range(n)]
        sl=[None]*n; valid=[v for v in ml if v is not None]
        if len(valid)>=9:
            sr=ema_s([v for v in ml if v is not None],9); si=0
            for i in range(n):
                if ml[i] is not None: sl[i]=clean(sr[si]); si+=1
        hl=[clean(ml[i]-sl[i]) if ml[i] is not None and sl[i] is not None else None for i in range(n)]
        ind_data["MACD"]={"macd":ml,"signal":sl,"histogram":hl}

    if "BB" in requested:
        bp=20; u,m,l_=[None]*n,[None]*n,[None]*n
        for i in range(bp-1,n):
            w=closes[i-bp+1:i+1]; mv=float(np.mean(w)); std=float(np.std(w))
            m[i]=clean(mv); u[i]=clean(mv+2*std); l_[i]=clean(mv-2*std)
        ind_data["BB"]={"period":bp,"upper":u,"middle":m,"lower":l_}

    if "SMA" in requested:
        sma=[None]*n
        for i in range(sma_period-1,n): sma[i]=clean(float(np.mean(closes[i-sma_period+1:i+1])))
        ind_data["SMA"]={"period":sma_period,"values":sma}

    if "EMA" in requested:
        k=2/(ema_period+1); ema=[None]*n
        for i in range(n):
            prev=ema[i-1] if i>0 and ema[i-1] is not None else float(closes[i])
            ema[i]=clean(float(closes[i])*k+prev*(1-k))
        ind_data["EMA"]={"period":ema_period,"values":ema}

    if "STOCH" in requested:
        sp=14; kv,dv=[None]*n,[None]*n
        for i in range(sp-1,n):
            h14=float(np.max(highs[i-sp+1:i+1])); l14=float(np.min(lows[i-sp+1:i+1]))
            if h14!=l14: kv[i]=clean((float(closes[i])-l14)/(h14-l14)*100)
        vk=[v for v in kv if v is not None]
        if len(vk)>=3:
            dr=[clean(np.mean(vk[i-2:i+1])) if i>=2 else None for i in range(len(vk))]
            di=0
            for i in range(n):
                if kv[i] is not None: dv[i]=dr[di]; di+=1
        ind_data["STOCH"]={"period":sp,"k":kv,"d":dv}

    if "ATR" in requested:
        ap=14; av=[None]*n
        trs=[max(float(highs[i])-float(lows[i]),abs(float(highs[i])-float(closes[i-1])),abs(float(lows[i])-float(closes[i-1]))) for i in range(1,n)]
        if len(trs)>=ap:
            atr=float(np.mean(trs[:ap])); av[ap]=clean(atr)
            for i in range(ap+1,n): atr=(atr*(ap-1)+trs[i-1])/ap; av[i]=clean(atr)
        ind_data["ATR"]={"period":ap,"values":av}


# ─── HEALTH ───────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status":"running","redis":cache.is_connected(),"timestamp":datetime.utcnow().isoformat()+"Z","docs":"/docs"}


# ─── STOCKS ───────────────────────────────────────────────────────────────────

@app.get("/stocks")
def get_all_stocks():
    cached=cache.get_all_stocks()
    return {"count":len(cached) if cached else 0,"stocks":cached or {},"timestamp":datetime.utcnow().isoformat()+"Z"}

@app.get("/stocks/list")
def get_stocks_flat():
    cached=cache.get_all_stocks()
    if not cached: return []
    result=[]
    for ticker,data in cached.items():
        try:
            result.append({
                "Ticker":str(data.get("ticker",ticker) or ticker),"Name":str(data.get("name",ticker) or ticker),
                "Price":safe_float(data.get("price")),"Change":safe_float(data.get("change")),"Change %":safe_float(data.get("change_pct")),
                "Open":safe_float(data.get("open")),"High":safe_float(data.get("high")),"Low":safe_float(data.get("low")),
                "Prev Close":safe_float(data.get("prev_close")),"Volume":safe_int(data.get("volume")),"Market Cap":safe_int(data.get("market_cap")),
                "52W High":safe_float(data.get("52w_high")),"52W Low":safe_float(data.get("52w_low")),
                "Currency":str(data.get("currency") or "USD"),"Exchange":str(data.get("exchange") or ""),"Last Updated":str(data.get("fetched_at") or ""),
            })
        except Exception as e: print(f"[API] Skipping {ticker}: {e}"); continue
    return result

@app.get("/stock/{ticker}")
def get_stock(ticker:str):
    ticker=ticker.upper().strip()
    cached=cache.get_stock(ticker)
    if cached: return cached
    raise HTTPException(status_code=404,detail=f"No data for {ticker}. Is the fetcher running?")

@app.get("/stock/{ticker}/history")
def get_stock_history(ticker:str,period:str="1mo",interval:str="1d"):
    import yfinance as yf
    try:
        hist=yf.Ticker(ticker.upper()).history(period=period,interval=interval)
        if hist.empty: raise HTTPException(status_code=404,detail=f"No history for {ticker}")
        records=[{"date":str(d)[:10],"open":round(r["Open"],2),"high":round(r["High"],2),"low":round(r["Low"],2),"close":round(r["Close"],2),"volume":int(r["Volume"])} for d,r in hist.iterrows()]
        return {"ticker":ticker.upper(),"period":period,"count":len(records),"data":records}
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500,detail=str(e))

@app.get("/stock/{ticker}/compute-indicators")
def compute_indicators(ticker:str,indicators:str=Query("RSI,MACD"),period:str=Query("3mo"),interval:str=Query("1d"),sma_period:int=Query(20),ema_period:int=Query(20)):
    import yfinance as yf
    ticker=ticker.upper().strip()
    requested=[i.strip().upper() for i in indicators.split(",")]
    try:
        hist=yf.Ticker(ticker).history(period=period,interval=interval)
        if hist.empty: raise HTTPException(status_code=404,detail=f"No history for {ticker}")
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500,detail=str(e))
    closes=np.array(hist["Close"].values,dtype=float); highs=np.array(hist["High"].values,dtype=float)
    lows=np.array(hist["Low"].values,dtype=float); volumes=np.array(hist["Volume"].values,dtype=float)
    dates=[str(d)[:10] for d in hist.index]; n=len(closes)
    base=[{"date":dates[i],"open":round(float(hist["Open"].values[i]),2),"high":round(float(highs[i]),2),"low":round(float(lows[i]),2),"close":round(float(closes[i]),2),"volume":int(volumes[i])} for i in range(n)]
    result={"ticker":ticker,"period":period,"count":n,"data":base,"indicators":{}}
    ind_data=result["indicators"]
    _compute_indicators_into(ind_data,requested,closes,highs,lows,n,sma_period,ema_period)
    if "FIBONACCI" in requested:
        hv=float(np.max(highs)); lv=float(np.min(lows)); diff=hv-lv
        ind_data["FIBONACCI"]={"high":round(hv,4),"low":round(lv,4),"levels":{"0.0":round(hv,4),"0.236":round(hv-0.236*diff,4),"0.382":round(hv-0.382*diff,4),"0.5":round(hv-0.5*diff,4),"0.618":round(hv-0.618*diff,4),"0.786":round(hv-0.786*diff,4),"1.0":round(lv,4)}}
    return result


# ─── MULTI-RULE SCANNER ───────────────────────────────────────────────────────

VARIABLE_TO_GROUP = {
    "RSI":"RSI","MACD_LINE":"MACD","MACD_SIGNAL":"MACD","MACD_HIST":"MACD",
    "BB_UPPER":"BB","BB_MIDDLE":"BB","BB_LOWER":"BB",
    "SMA":"SMA","EMA":"EMA","STOCH_K":"STOCH","STOCH_D":"STOCH","ATR":"ATR",
}

class ScanRule(BaseModel):
    formula:      str
    signal:       str   # e.g. "STRONG BUY", "BUY", "SELL", "STRONG SELL"

class ScannerRequest(BaseModel):
    rules:      List[ScanRule]
    period:     str = "3mo"
    sma_period: int = 20
    ema_period: int = 20

def _extract_needed_groups(formulas: list) -> set:
    needed = set()
    for formula in formulas:
        for var, group in VARIABLE_TO_GROUP.items():
            if re.search(r'\b' + var + r'\b', formula):
                needed.add(group)
    return needed

def _evaluate_formula(formula: str, values: dict) -> bool:
    expr = re.sub(r'\bAND\b','and', formula.strip())
    expr = re.sub(r'\bOR\b', 'or',  expr)
    for name, val in sorted(values.items(), key=lambda x: -len(x[0])):
        replacement = 'None' if val is None else str(round(float(val), 6))
        expr = re.sub(r'\b' + name + r'\b', replacement, expr)
    if re.search(r'[a-zA-Z_][a-zA-Z0-9_]*\s*\(', expr): return False
    if re.search(r'\b(?:import|exec|eval|open|__)\b', expr): return False
    try: return bool(eval(expr, {"__builtins__":{}, "None":None, "True":True, "False":False}))
    except: return False

def _scan_one_ticker(ticker, needed_groups, period, sma_period, ema_period, stock_cache):
    import yfinance as yf
    try:
        hist=yf.Ticker(ticker).history(period=period,interval="1d")
        if hist.empty: return ticker, None, "No history"
        closes=np.array(hist["Close"].values,dtype=float); highs=np.array(hist["High"].values,dtype=float)
        lows=np.array(hist["Low"].values,dtype=float); n=len(closes)
        ind_data={}
        _compute_indicators_into(ind_data,list(needed_groups),closes,highs,lows,n,sma_period,ema_period)

        def last(arr):
            for v in reversed(arr):
                if v is not None: return v
            return None

        cd=stock_cache.get(ticker,{})
        values={"PRICE":cd.get("price"),"CHANGE_PCT":cd.get("change_pct"),"VOLUME":cd.get("volume")}
        if "RSI"   in ind_data: values["RSI"]=last(ind_data["RSI"]["values"])
        if "MACD"  in ind_data:
            values["MACD_LINE"]=last(ind_data["MACD"]["macd"])
            values["MACD_SIGNAL"]=last(ind_data["MACD"]["signal"])
            values["MACD_HIST"]=last(ind_data["MACD"]["histogram"])
        if "BB"    in ind_data:
            values["BB_UPPER"]=last(ind_data["BB"]["upper"])
            values["BB_MIDDLE"]=last(ind_data["BB"]["middle"])
            values["BB_LOWER"]=last(ind_data["BB"]["lower"])
        if "SMA"   in ind_data: values["SMA"]=last(ind_data["SMA"]["values"])
        if "EMA"   in ind_data: values["EMA"]=last(ind_data["EMA"]["values"])
        if "STOCH" in ind_data:
            values["STOCH_K"]=last(ind_data["STOCH"]["k"])
            values["STOCH_D"]=last(ind_data["STOCH"]["d"])
        if "ATR"   in ind_data: values["ATR"]=last(ind_data["ATR"]["values"])
        return ticker, values, None
    except Exception as e: return ticker, None, str(e)


@app.post("/scanner/run")
def run_scanner(req: ScannerRequest):
    t_start = time.time()

    if not req.rules:
        raise HTTPException(status_code=400, detail="At least one rule is required")

    # Validate signals
    for rule in req.rules:
        if rule.signal.upper() not in SIGNAL_PRIORITY:
            raise HTTPException(status_code=400, detail=f"Unknown signal '{rule.signal}'. Use: {list(SIGNAL_PRIORITY.keys())}")

    # Collect all needed indicator groups across all rules
    all_formulas  = [r.formula for r in req.rules]
    needed_groups = _extract_needed_groups(all_formulas)
    has_price_vars = any(re.search(r'\b(PRICE|CHANGE_PCT|VOLUME)\b', f) for f in all_formulas)
    if not needed_groups and not has_price_vars:
        raise HTTPException(status_code=400, detail=f"No recognized variables found. Use: {', '.join(VARIABLE_TO_GROUP.keys())}, PRICE, CHANGE_PCT, VOLUME")

    cached_stocks = cache.get_all_stocks() or {}
    tickers = list(cached_stocks.keys())
    if not tickers:
        raise HTTPException(status_code=503, detail="No stocks in cache. Is the fetcher running?")

    results = []
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(_scan_one_ticker, t, needed_groups, req.period, req.sma_period, req.ema_period, cached_stocks): t for t in tickers}
        for future in as_completed(futures):
            ticker = futures[future]
            try:
                t, values, error = future.result()
                cd = cached_stocks.get(t, {})

                if values is None:
                    results.append({
                        "ticker": t, "signal": None, "signal_priority": 0,
                        "triggered_rules": [], "error": error or "No data",
                        "values": {}, "price": cd.get("price"), "change_pct": cd.get("change_pct"),
                    })
                    continue

                # Evaluate each rule, collect all triggered
                triggered_rules = []
                for rule in req.rules:
                    if _evaluate_formula(rule.formula, values):
                        triggered_rules.append({
                            "formula": rule.formula,
                            "signal":  rule.signal.upper(),
                            "priority": SIGNAL_PRIORITY.get(rule.signal.upper(), 0),
                        })

                # Pick strongest signal (highest priority)
                best = max(triggered_rules, key=lambda r: r["priority"]) if triggered_rules else None

                results.append({
                    "ticker":          t,
                    "signal":          best["signal"] if best else None,
                    "signal_priority": best["priority"] if best else 0,
                    "triggered_rules": triggered_rules,
                    "error":           None,
                    "values":          {k: (round(v,4) if v is not None else None) for k,v in values.items()},
                    "price":           values.get("PRICE"),
                    "change_pct":      values.get("CHANGE_PCT"),
                })
            except Exception as e:
                cd = cached_stocks.get(ticker, {})
                results.append({
                    "ticker": ticker, "signal": None, "signal_priority": 0,
                    "triggered_rules": [], "error": str(e),
                    "values": {}, "price": cd.get("price"), "change_pct": cd.get("change_pct"),
                })

    # Sort: strongest signals first, then by ticker
    results.sort(key=lambda x: (-x["signal_priority"], x["ticker"]))

    # Signal counts
    signal_counts = {}
    for r in results:
        if r["signal"]:
            signal_counts[r["signal"]] = signal_counts.get(r["signal"], 0) + 1

    return {
        "rules":          [r.dict() for r in req.rules],
        "total":          len(results),
        "triggered_count": sum(1 for r in results if r["signal"]),
        "signal_counts":  signal_counts,
        "elapsed":        round(time.time()-t_start, 2),
        "timestamp":      datetime.utcnow().isoformat()+"Z",
        "results":        results,
    }
