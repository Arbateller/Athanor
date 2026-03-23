def generate_signal(indicators: dict[str, float | None]) -> tuple[str, str]:
    """Determine a trading signal from indicator values."""
    rsi = indicators.get("rsi_14")
    macd_hist = indicators.get("macd_hist")

    if rsi is None or macd_hist is None:
        return "UNKNOWN", "Not enough data"

    bullish = macd_hist > 0
    bearish = macd_hist < 0

    if rsi < 30 and bullish:
        return "STRONG BUY",  f"RSI {rsi} oversold + MACD bullish"
    if rsi < 45 and bullish:
        return "BUY",         f"RSI {rsi} low + MACD bullish momentum"
    if rsi > 70 and bearish:
        return "STRONG SELL", f"RSI {rsi} overbought + MACD bearish"
    if rsi > 55 and bearish:
        return "SELL",        f"RSI {rsi} high + MACD bearish momentum"
    return "HOLD", f"RSI {rsi} neutral, no clear signal"
