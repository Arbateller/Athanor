from indicators.registry import register


class RSIIndicator:
    name = "RSI-14"
    min_data_points = 15
    output_keys = ["rsi_14"]

    def calculate(self, closes: list[float]) -> dict[str, float | None]:
        period = 14
        diffs = [closes[i] - closes[i - 1] for i in range(-period, 0)]
        gains = [d for d in diffs if d > 0]
        losses = [abs(d) for d in diffs if d < 0]
        avg_gain = sum(gains) / period if gains else 0
        avg_loss = sum(losses) / period if losses else 0
        if avg_loss == 0:
            return {"rsi_14": 100.0}
        return {"rsi_14": round(100 - (100 / (1 + avg_gain / avg_loss)), 2)}


register(RSIIndicator())
