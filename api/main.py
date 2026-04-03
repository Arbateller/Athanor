"""
main.py - FastAPI REST API v5 (simulation + adapter pattern)
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import os, sys, math, re, time
import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "fetcher"))
sys.path.insert(0, _ROOT)

from cache      import cache
from adapters   import REGISTRY, list_adapters, compute
from simulation import simulate_position, simulate_portfolio, signal_snapshot

def _sf(v):
    try: f=float(v); return 0.0 if math.isnan(f) or math.isinf(f) else f
    except: return 0.0

def _si(v):
    try: f=float(v); return 0 if math.isnan(f) or math.isinf(f) else int(f)
    except: return 0

SIGNAL_PRIORITY = {"STRONG BUY":5,"BUY":4,"HOLD":3,"SELL":2,"STRONG SELL":1}

app = FastAPI(title="Stock Market API", version="5.0.0")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_methods=["*"],allow_headers=["*"])

# ─── HEALTH ───────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status":"running","redis":cache.is_connected(),
            "timestamp":datetime.utcnow().isoformat()+"Z","indicators":list(REGISTRY.keys())}

@app.get("/indicators")
def get_indicators():
    return {"adapters": list_adapters()}

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
                "Price":_sf(data.get("price")),"Change":_sf(data.get("change")),"Change %":_sf(data.get("change_pct")),
                "Open":_sf(data.get("open")),"High":_sf(data.get("high")),"Low":_sf(data.get("low")),
                "Prev Close":_sf(data.get("prev_close")),"Volume":_si(data.get("volume")),"Market Cap":_si(data.get("market_cap")),
                "52W High":_sf(data.get("52w_high")),"52W Low":_sf(data.get("52w_low")),
                "Currency":str(data.get("currency") or "USD"),"Exchange":str(data.get("exchange") or ""),
                "Last Updated":str(data.get("fetched_at") or ""),
            })
        except Exception as e: print(f"[API] Skipping {ticker}: {e}")
    return result

@app.get("/stock/{ticker}")
def get_stock(ticker:str):
    t=ticker.upper().strip(); d=cache.get_stock(t)
    if d: return d
    raise HTTPException(404,f"No data for {t}. Is the fetcher running?")

@app.get("/stock/{ticker}/history")
def get_stock_history(ticker:str,period:str="1mo",interval:str="1d"):
    import yfinance as yf
    try:
        hist=yf.Ticker(ticker.upper()).history(period=period,interval=interval)
        if hist.empty: raise HTTPException(404,f"No history for {ticker}")
        records=[{"date":str(d)[:10],"open":round(r["Open"],2),"high":round(r["High"],2),
                  "low":round(r["Low"],2),"close":round(r["Close"],2),"volume":int(r["Volume"])}
                 for d,r in hist.iterrows()]
        return {"ticker":ticker.upper(),"period":period,"count":len(records),"data":records}
    except HTTPException: raise
    except Exception as e: raise HTTPException(500,str(e))

@app.get("/stock/{ticker}/compute-indicators")
def compute_indicators_endpoint(
    ticker:str, indicators:str=Query("RSI,MACD"),
    period:str=Query("3mo"), interval:str=Query("1d"),
    sma_period:int=Query(20), ema_period:int=Query(20),
):
    import yfinance as yf
    ticker=ticker.upper().strip()
    names=[n.strip().upper() for n in indicators.split(",")]
    try:
        hist=yf.Ticker(ticker).history(period=period,interval=interval)
        if hist.empty: raise HTTPException(404,f"No history for {ticker}")
    except HTTPException: raise
    except Exception as e: raise HTTPException(500,str(e))

    closes=np.array(hist["Close"].values,dtype=float); highs=np.array(hist["High"].values,dtype=float)
    lows=np.array(hist["Low"].values,dtype=float); volumes=np.array(hist["Volume"].values,dtype=float)
    dates=[str(d)[:10] for d in hist.index]; n=len(closes)
    base=[{"date":dates[i],"open":round(float(hist["Open"].values[i]),2),"high":round(float(highs[i]),2),
           "low":round(float(lows[i]),2),"close":round(float(closes[i]),2),"volume":int(volumes[i])} for i in range(n)]
    ind_series=_compute_series(names,closes,highs,lows,n,sma_period,ema_period)
    return {"ticker":ticker,"period":period,"count":n,"data":base,"indicators":ind_series}


# ─── SCANNER ──────────────────────────────────────────────────────────────────

class ScanRule(BaseModel):
    formula: str
    signal:  str

class ScannerRequest(BaseModel):
    rules:      List[ScanRule]
    period:     str = "3mo"
    sma_period: int = 20
    ema_period: int = 20

def _needed_adapters(rules):
    all_text=" ".join(r.formula for r in rules); needed=[]
    for name,adapter in REGISTRY.items():
        for var in adapter.VARIABLES:
            if re.search(r'\b'+var+r'\b',all_text): needed.append(name); break
    return needed

def _eval_formula(formula,values):
    expr=re.sub(r'\bAND\b','and',formula.strip()); expr=re.sub(r'\bOR\b','or',expr)
    for name,val in sorted(values.items(),key=lambda x:-len(x[0])):
        expr=re.sub(r'\b'+name+r'\b','None' if val is None else str(round(float(val),6)),expr)
    if re.search(r'[a-zA-Z_]\w*\s*\(',expr): return False
    if re.search(r'\b(?:import|exec|eval|open|__)\b',expr): return False
    try: return bool(eval(expr,{"__builtins__":{},"None":None}))
    except: return False

def _scan_ticker(ticker,adapters_needed,period,sma_period,ema_period,stock_cache):
    import yfinance as yf
    try:
        hist=yf.Ticker(ticker).history(period=period,interval="1d")
        if hist.empty: return ticker,None,"No history"
        closes=np.array(hist["Close"].values,dtype=float); highs=np.array(hist["High"].values,dtype=float)
        lows=np.array(hist["Low"].values,dtype=float)
        params={"SMA":{"period":sma_period},"EMA":{"period":ema_period}}
        values=compute(adapters_needed,closes,highs,lows,params)
        cd=stock_cache.get(ticker,{})
        values["PRICE"]=cd.get("price"); values["CHANGE_PCT"]=cd.get("change_pct"); values["VOLUME"]=cd.get("volume")
        return ticker,values,None
    except Exception as e: return ticker,None,str(e)

@app.post("/scanner/run")
def run_scanner(req:ScannerRequest):
    t0=time.time()
    if not req.rules: raise HTTPException(400,"At least one rule is required")
    for rule in req.rules:
        if rule.signal.upper() not in SIGNAL_PRIORITY:
            raise HTTPException(400,f"Unknown signal '{rule.signal}'")
    adapters_needed=_needed_adapters(req.rules)
    has_price=any(re.search(r'\b(PRICE|CHANGE_PCT|VOLUME)\b',r.formula) for r in req.rules)
    if not adapters_needed and not has_price:
        raise HTTPException(400,"No recognized variables found")
    stocks=cache.get_all_stocks() or {}
    if not stocks: raise HTTPException(503,"No stocks in cache. Is the fetcher running?")
    results=[]
    with ThreadPoolExecutor(max_workers=20) as pool:
        futures={pool.submit(_scan_ticker,t,adapters_needed,req.period,req.sma_period,req.ema_period,stocks):t for t in stocks}
        for future in as_completed(futures):
            ticker=futures[future]; cd=stocks.get(ticker,{})
            try:
                t,values,err=future.result()
                if values is None:
                    results.append({"ticker":t,"signal":None,"priority":0,"triggered_rules":[],"error":err,"values":{},"price":cd.get("price"),"change_pct":cd.get("change_pct")})
                    continue
                triggered=[]
                for rule in req.rules:
                    if _eval_formula(rule.formula,values):
                        sig=rule.signal.upper()
                        triggered.append({"formula":rule.formula,"signal":sig,"priority":SIGNAL_PRIORITY.get(sig,0)})
                best=max(triggered,key=lambda x:x["priority"]) if triggered else None
                results.append({"ticker":t,"signal":best["signal"] if best else None,"priority":best["priority"] if best else 0,
                                 "triggered_rules":triggered,"error":None,
                                 "values":{k:(round(v,4) if v is not None else None) for k,v in values.items()},
                                 "price":values.get("PRICE"),"change_pct":values.get("CHANGE_PCT")})
            except Exception as e:
                results.append({"ticker":ticker,"signal":None,"priority":0,"triggered_rules":[],"error":str(e),"values":{},"price":cd.get("price"),"change_pct":cd.get("change_pct")})
    results.sort(key=lambda x:(-x["priority"],x["ticker"]))
    signal_counts={}
    for r in results:
        if r["signal"]: signal_counts[r["signal"]]=signal_counts.get(r["signal"],0)+1
    return {"total":len(results),"triggered_count":sum(1 for r in results if r["signal"]),
            "signal_counts":signal_counts,"elapsed":round(time.time()-t0,2),
            "timestamp":datetime.utcnow().isoformat()+"Z","results":results}


# ─── SIMULATION ───────────────────────────────────────────────────────────────

class SimPosition(BaseModel):
    ticker:    str
    buy_date:  str          # "YYYY-MM-DD"
    quantity:  float
    sell_date: Optional[str] = None

class SimRule(BaseModel):
    formula: str
    signal:  str

class SimulationRequest(BaseModel):
    positions:  List[SimPosition]
    scan_rules: Optional[List[SimRule]] = None   # for signal comparison
    sma_period: int = 20
    ema_period: int = 20

@app.post("/simulation/run")
def run_simulation(req: SimulationRequest):
    if not req.positions:
        raise HTTPException(400, "At least one position is required")

    t0 = time.time()
    positions_dict = [p.dict() for p in req.positions]

    try:
        if len(positions_dict) == 1:
            pos = positions_dict[0]
            result = simulate_position(
                ticker    = pos["ticker"],
                buy_date  = pos["buy_date"],
                quantity  = pos["quantity"],
                sell_date = pos.get("sell_date"),
            )
            mode = "single"
        else:
            result = simulate_portfolio(positions_dict)
            mode   = "portfolio"
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))

    # Signal snapshot — what signals fired on each buy date
    snapshots = []
    if req.scan_rules:
        rules_dict = [r.dict() for r in req.scan_rules]
        for pos in req.positions:
            try:
                snap = signal_snapshot(
                    ticker     = pos.ticker,
                    on_date    = pos.buy_date,
                    rules      = rules_dict,
                    sma_period = req.sma_period,
                    ema_period = req.ema_period,
                )
                snapshots.append(snap)
            except Exception as e:
                snapshots.append({"ticker": pos.ticker, "date": pos.buy_date, "error": str(e)})

    return {
        "mode":      mode,
        "result":    result,
        "snapshots": snapshots,
        "elapsed":   round(time.time() - t0, 2),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


# ─── SERIES HELPER ────────────────────────────────────────────────────────────

def _compute_series(names,closes,highs,lows,n,sma_period,ema_period):
    from adapters import _ema_series,_clean
    series={}
    if "RSI" in names:
        p=14; vals=[None]*n
        if n>p:
            d=np.diff(closes); g=np.where(d>0,d,0.); l=np.where(d<0,-d,0.)
            ag=float(np.mean(g[:p])); al=float(np.mean(l[:p]))
            for i in range(p,n):
                if i>p: ag=(ag*(p-1)+g[i-1])/p; al=(al*(p-1)+l[i-1])/p
                rs=ag/al if al!=0 else float('inf'); vals[i]=_clean(100-(100/(1+rs)))
        series["RSI"]={"values":vals}
    if "MACD" in names:
        e12=_ema_series(closes.tolist(),12); e26=_ema_series(closes.tolist(),26)
        ml=[_clean(e12[i]-e26[i]) for i in range(n)]; sl=[None]*n
        vi=[v for v in ml if v is not None]
        if len(vi)>=9:
            sr=_ema_series(vi,9); si=0
            for i in range(n):
                if ml[i] is not None: sl[i]=_clean(sr[si]); si+=1
        hl=[_clean(ml[i]-sl[i]) if ml[i] is not None and sl[i] is not None else None for i in range(n)]
        series["MACD"]={"macd":ml,"signal":sl,"histogram":hl}
    if "BB" in names:
        p=20; u,m,lo=[None]*n,[None]*n,[None]*n
        for i in range(p-1,n):
            w=closes[i-p+1:i+1]; mv=float(np.mean(w)); std=float(np.std(w))
            m[i]=_clean(mv); u[i]=_clean(mv+2*std); lo[i]=_clean(mv-2*std)
        series["BB"]={"upper":u,"middle":m,"lower":lo}
    if "SMA" in names:
        sv=[None]*n
        for i in range(sma_period-1,n): sv[i]=_clean(float(np.mean(closes[i-sma_period+1:i+1])))
        series["SMA"]={"values":sv}
    if "EMA" in names:
        k=2/(ema_period+1); ev=[None]*n
        for i in range(n):
            prev=ev[i-1] if i>0 and ev[i-1] is not None else float(closes[i])
            ev[i]=_clean(float(closes[i])*k+prev*(1-k))
        series["EMA"]={"values":ev}
    if "STOCH" in names:
        p=14; kv,dv=[None]*n,[None]*n
        for i in range(p-1,n):
            h14=float(np.max(highs[i-p+1:i+1])); l14=float(np.min(lows[i-p+1:i+1]))
            if h14!=l14: kv[i]=_clean((float(closes[i])-l14)/(h14-l14)*100)
        vk=[v for v in kv if v is not None]
        if len(vk)>=3:
            dr=[_clean(np.mean(vk[i-2:i+1])) if i>=2 else None for i in range(len(vk))]
            di=0
            for i in range(n):
                if kv[i] is not None: dv[i]=dr[di]; di+=1
        series["STOCH"]={"k":kv,"d":dv}
    if "ATR" in names:
        p=14; av=[None]*n
        trs=[max(float(highs[i])-float(lows[i]),abs(float(highs[i])-float(closes[i-1])),abs(float(lows[i])-float(closes[i-1]))) for i in range(1,n)]
        if len(trs)>=p:
            atr=float(np.mean(trs[:p])); av[p]=_clean(atr)
            for i in range(p+1,n): atr=(atr*(p-1)+trs[i-1])/p; av[i]=_clean(atr)
        series["ATR"]={"values":av}
    if "FIBONACCI" in names:
        hv=float(np.max(highs)); lv=float(np.min(lows)); diff=hv-lv
        series["FIBONACCI"]={"high":round(hv,4),"low":round(lv,4),"levels":{
            "0.0":round(hv,4),"0.236":round(hv-0.236*diff,4),"0.382":round(hv-0.382*diff,4),
            "0.5":round(hv-0.5*diff,4),"0.618":round(hv-0.618*diff,4),"0.786":round(hv-0.786*diff,4),"1.0":round(lv,4)}}
    return series
