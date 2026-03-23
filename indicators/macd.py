from indicators.registry import register


def _ema(data: list[float], period: int) -> list[float]:
    if len(data) < period:
        return []
    ema = [sum(data[:period]) / period]
    k = 2 / (period + 1)
    for price in data[period:]:
        ema.append((price - ema[-1]) * k + ema[-1])
    return ema


class MACDIndicator:
    name = "MACD"
    min_data_points = 35
    output_keys = ["macd_line", "macd_signal", "macd_hist"]

    def calculate(self, closes: list[float]) -> dict[str, float | None]:
        fast, slow, signal = 12, 26, 9
        ema_fast = _ema(closes, fast)
        ema_slow = _ema(closes, slow)
        min_len = min(len(ema_fast), len(ema_slow))
        macd_line = [f - s for f, s in zip(ema_fast[-min_len:], ema_slow[-min_len:])]
        if len(macd_line) < signal:
            return {"macd_line": None, "macd_signal": None, "macd_hist": None}
        signal_line = _ema(macd_line, signal)
        if not signal_line:
            return {"macd_line": None, "macd_signal": None, "macd_hist": None}
        hist = macd_line[-1] - signal_line[-1]
        return {
            "macd_line": round(macd_line[-1], 4),
            "macd_signal": round(signal_line[-1], 4),
            "macd_hist": round(hist, 4),
        }


register(MACDIndicator())
