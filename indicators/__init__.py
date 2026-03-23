# Import adapters to trigger self-registration
import indicators.rsi   # noqa: F401
import indicators.macd  # noqa: F401

from indicators.registry import calculate_all
from indicators.signal import generate_signal

__all__ = ["calculate_all", "generate_signal"]
