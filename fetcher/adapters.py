"""
indicators/adapters.py

Adapter pattern for technical indicators.
Each adapter implements a common interface:
  - NAME        : str  — unique identifier
  - LABEL       : str  — human-readable name
  - VARIABLES   : list — variable names this adapter exposes
  - calculate() — compute from OHLC arrays, return {var: last_value}
  - describe()  — return metadata dict

Adding a new indicator = create a new class + register it below.
"""

from __future__ import annotations
import numpy as np
import math
from abc import ABC, abstractmethod
from typing import Dict, List, Optional


# ─── BASE INTERFACE ───────────────────────────────────────────────────────────

class IndicatorAdapter(ABC):
    """Common interface every indicator adapter must implement."""

    NAME:      str        # e.g. "RSI"
    LABEL:     str        # e.g. "RSI (14)"
    VARIABLES: List[str]  # e.g. ["RSI"]
    PARAMS:    Dict       # default params, e.g. {"period": 14}

    @abstractmethod
    def calculate(
        self,
        closes: np.ndarray,
        highs:  np.ndarray,
        lows:   np.ndarray,
    ) -> Dict[str, Optional[float]]:
        """
        Compute indicator and return a dict of {variable_name: last_value}.
        Return None for variables that could not be computed.
        """

    def describe(self) -> Dict:
        return {
            "name":      self.NAME,
            "label":     self.LABEL,
            "variables": self.VARIABLES,
            "params":    self.PARAMS,
        }


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def _clean(val) -> Optional[float]:
    if val is None:
        return None
    try:
        v = float(val)
        return None if (math.isnan(v) or math.isinf(v)) else round(v, 4)
    except Exception:
        return None

def _last(arr: list) -> Optional[float]:
    """Return last non-None value in list."""
    for v in reversed(arr):
        if v is not None:
            return v
    return None

def _ema_series(values: list, span: int) -> list:
    k = 2 / (span + 1)
    out = [None] * len(values)
    for i, v in enumerate(values):
        out[i] = v * k + out[i - 1] * (1 - k) if i > 0 else float(v)
    return out


# ─── RSI ──────────────────────────────────────────────────────────────────────

class RSIAdapter(IndicatorAdapter):
    """Relative Strength Index (14-period)."""

    NAME      = "RSI"
    LABEL     = "RSI (14)"
    VARIABLES = ["RSI"]
    PARAMS    = {"period": 14}

    def calculate(self, closes, highs, lows):
        period = self.PARAMS["period"]
        n      = len(closes)
        if n <= period:
            return {"RSI": None}

        deltas = np.diff(closes)
        gains  = np.where(deltas > 0, deltas, 0.0)
        losses = np.where(deltas < 0, -deltas, 0.0)
        avg_g  = float(np.mean(gains[:period]))
        avg_l  = float(np.mean(losses[:period]))

        rsi = None
        for i in range(period, n):
            if i > period:
                avg_g = (avg_g * (period - 1) + gains[i - 1]) / period
                avg_l = (avg_l * (period - 1) + losses[i - 1]) / period
            rs  = avg_g / avg_l if avg_l != 0 else float("inf")
            rsi = _clean(100 - (100 / (1 + rs)))

        return {"RSI": rsi}


# ─── MACD ─────────────────────────────────────────────────────────────────────

class MACDAdapter(IndicatorAdapter):
    """MACD (12, 26, 9)."""

    NAME      = "MACD"
    LABEL     = "MACD (12/26/9)"
    VARIABLES = ["MACD_LINE", "MACD_SIGNAL", "MACD_HIST"]
    PARAMS    = {"fast": 12, "slow": 26, "signal": 9}

    def calculate(self, closes, highs, lows):
        n    = len(closes)
        e12  = _ema_series(closes.tolist(), self.PARAMS["fast"])
        e26  = _ema_series(closes.tolist(), self.PARAMS["slow"])
        macd = [_clean(e12[i] - e26[i]) for i in range(n)]

        sig_input = [v for v in macd if v is not None]
        sig_arr   = [None] * n
        if len(sig_input) >= self.PARAMS["signal"]:
            sig_raw = _ema_series(sig_input, self.PARAMS["signal"])
            idx = 0
            for i in range(n):
                if macd[i] is not None:
                    sig_arr[i] = _clean(sig_raw[idx])
                    idx += 1

        hist = [
            _clean(macd[i] - sig_arr[i])
            if macd[i] is not None and sig_arr[i] is not None
            else None
            for i in range(n)
        ]

        return {
            "MACD_LINE":   _last(macd),
            "MACD_SIGNAL": _last(sig_arr),
            "MACD_HIST":   _last(hist),
        }


# ─── Bollinger Bands ──────────────────────────────────────────────────────────

class BollingerBandsAdapter(IndicatorAdapter):
    """Bollinger Bands (20, 2σ)."""

    NAME      = "BB"
    LABEL     = "Bollinger Bands (20)"
    VARIABLES = ["BB_UPPER", "BB_MIDDLE", "BB_LOWER"]
    PARAMS    = {"period": 20, "std_dev": 2}

    def calculate(self, closes, highs, lows):
        period = self.PARAMS["period"]
        n      = len(closes)
        upper = middle = lower = None

        for i in range(period - 1, n):
            window = closes[i - period + 1:i + 1]
            m      = float(np.mean(window))
            std    = float(np.std(window))
            middle = _clean(m)
            upper  = _clean(m + self.PARAMS["std_dev"] * std)
            lower  = _clean(m - self.PARAMS["std_dev"] * std)

        return {"BB_UPPER": upper, "BB_MIDDLE": middle, "BB_LOWER": lower}


# ─── SMA ──────────────────────────────────────────────────────────────────────

class SMAAdapter(IndicatorAdapter):
    """Simple Moving Average."""

    NAME      = "SMA"
    LABEL     = "SMA"
    VARIABLES = ["SMA"]
    PARAMS    = {"period": 20}

    def calculate(self, closes, highs, lows):
        period = self.PARAMS["period"]
        n      = len(closes)
        sma    = None
        if n >= period:
            sma = _clean(float(np.mean(closes[n - period:])))
        return {"SMA": sma}


# ─── EMA ──────────────────────────────────────────────────────────────────────

class EMAAdapter(IndicatorAdapter):
    """Exponential Moving Average."""

    NAME      = "EMA"
    LABEL     = "EMA"
    VARIABLES = ["EMA"]
    PARAMS    = {"period": 20}

    def calculate(self, closes, highs, lows):
        ema_vals = _ema_series(closes.tolist(), self.PARAMS["period"])
        return {"EMA": _last(ema_vals)}


# ─── Stochastic ───────────────────────────────────────────────────────────────

class StochasticAdapter(IndicatorAdapter):
    """Stochastic Oscillator (%K, %D)."""

    NAME      = "STOCH"
    LABEL     = "Stochastic (14)"
    VARIABLES = ["STOCH_K", "STOCH_D"]
    PARAMS    = {"period": 14, "smooth": 3}

    def calculate(self, closes, highs, lows):
        period = self.PARAMS["period"]
        n      = len(closes)
        k_vals = [None] * n

        for i in range(period - 1, n):
            h14 = float(np.max(highs[i - period + 1:i + 1]))
            l14 = float(np.min(lows[i  - period + 1:i + 1]))
            if h14 != l14:
                k_vals[i] = _clean((float(closes[i]) - l14) / (h14 - l14) * 100)

        valid_k = [v for v in k_vals if v is not None]
        d_val   = None
        if len(valid_k) >= self.PARAMS["smooth"]:
            d_val = _clean(float(np.mean(valid_k[-self.PARAMS["smooth"]:])))

        return {"STOCH_K": _last(k_vals), "STOCH_D": d_val}


# ─── ATR ──────────────────────────────────────────────────────────────────────

class ATRAdapter(IndicatorAdapter):
    """Average True Range (14)."""

    NAME      = "ATR"
    LABEL     = "ATR (14)"
    VARIABLES = ["ATR"]
    PARAMS    = {"period": 14}

    def calculate(self, closes, highs, lows):
        period = self.PARAMS["period"]
        n      = len(closes)
        if n < period + 1:
            return {"ATR": None}

        trs = [
            max(
                float(highs[i])  - float(lows[i]),
                abs(float(highs[i])  - float(closes[i - 1])),
                abs(float(lows[i])   - float(closes[i - 1])),
            )
            for i in range(1, n)
        ]

        atr = float(np.mean(trs[:period]))
        for i in range(period, len(trs)):
            atr = (atr * (period - 1) + trs[i]) / period

        return {"ATR": _clean(atr)}


# ─── Fibonacci ────────────────────────────────────────────────────────────────

class FibonacciAdapter(IndicatorAdapter):
    """Fibonacci Retracement levels over the full period."""

    NAME      = "FIBONACCI"
    LABEL     = "Fibonacci Retracement"
    VARIABLES = ["FIB_0", "FIB_236", "FIB_382", "FIB_500", "FIB_618", "FIB_786", "FIB_100"]
    PARAMS    = {}

    def calculate(self, closes, highs, lows):
        high = float(np.max(highs))
        low  = float(np.min(lows))
        diff = high - low
        return {
            "FIB_0":   _clean(high),
            "FIB_236": _clean(high - 0.236 * diff),
            "FIB_382": _clean(high - 0.382 * diff),
            "FIB_500": _clean(high - 0.500 * diff),
            "FIB_618": _clean(high - 0.618 * diff),
            "FIB_786": _clean(high - 0.786 * diff),
            "FIB_100": _clean(low),
        }


# ─── REGISTRY ─────────────────────────────────────────────────────────────────
# To add a new indicator: create a class above and add it here.

_ALL_ADAPTERS: List[IndicatorAdapter] = [
    RSIAdapter(),
    MACDAdapter(),
    BollingerBandsAdapter(),
    SMAAdapter(),
    EMAAdapter(),
    StochasticAdapter(),
    ATRAdapter(),
    FibonacciAdapter(),
]

REGISTRY: Dict[str, IndicatorAdapter] = {a.NAME: a for a in _ALL_ADAPTERS}


def get_adapter(name: str) -> Optional[IndicatorAdapter]:
    return REGISTRY.get(name.upper())


def list_adapters() -> List[Dict]:
    return [a.describe() for a in _ALL_ADAPTERS]


def compute(
    names:  List[str],
    closes: np.ndarray,
    highs:  np.ndarray,
    lows:   np.ndarray,
    params: Dict = None,
) -> Dict[str, Optional[float]]:
    """
    Run all requested adapters and merge their variable outputs.
    Optionally override adapter params via params dict:
      e.g. params={"SMA": {"period": 50}, "EMA": {"period": 20}}
    """
    params   = params or {}
    combined = {}
    for name in names:
        adapter = get_adapter(name)
        if adapter is None:
            continue
        # Apply param overrides if any
        if name in params:
            for k, v in params[name].items():
                if k in adapter.PARAMS:
                    adapter.PARAMS[k] = v
        try:
            result = adapter.calculate(closes, highs, lows)
            combined.update(result)
        except Exception as e:
            print(f"[Adapter:{name}] Error: {e}")
    return combined
