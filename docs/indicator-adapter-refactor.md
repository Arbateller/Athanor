# Indicator Adapter Refactor

## What Changed

The indicator calculation logic (RSI, MACD, signal generation) was extracted from `fetcher/fetcher.py` into a standalone `indicators/` module using an adapter pattern.

### Before

`fetcher/fetcher.py` handled everything: data fetching, indicator calculation, and signal generation — all in one file (~220 lines).

### After

```
fetcher/fetcher.py       → Fetch only. No indicator logic.
indicators/
├── __init__.py          → Public API (calculate_all, generate_signal)
├── base.py              → Indicator Protocol (adapter interface)
├── registry.py          → Adapter registry + orchestrator
├── rsi.py               → RSI-14 adapter
├── macd.py              → MACD adapter
└── signal.py            → Signal generation
```

`fetcher.py` now calls two functions:

```python
from indicators import calculate_all, generate_signal

indicator_values = calculate_all(closes)
signal, reason   = generate_signal(indicator_values)
```

## How the Adapter Pattern Works

Each indicator is a class that satisfies the `Indicator` Protocol defined in `base.py`:

| Property/Method    | Purpose                                          |
|--------------------|--------------------------------------------------|
| `name`             | Human-readable name (e.g. `"RSI-14"`)            |
| `min_data_points`  | Minimum closing prices needed to calculate        |
| `output_keys`      | Keys produced in the output dict (e.g. `["rsi_14"]`) |
| `calculate(closes)`| Returns a dict of computed values                 |

Adapters self-register by calling `register()` at module level. The registry's `calculate_all()` runs every registered adapter and merges results into a single dict.

## Adding a New Indicator

1. Create `indicators/your_indicator.py`:

```python
from indicators.registry import register

class YourIndicator:
    name = "Bollinger Bands"
    min_data_points = 20
    output_keys = ["bb_upper", "bb_middle", "bb_lower"]

    def calculate(self, closes: list[float]) -> dict[str, float | None]:
        # your calculation here
        return {"bb_upper": ..., "bb_middle": ..., "bb_lower": ...}

register(YourIndicator())
```

2. Add one import to `indicators/__init__.py`:

```python
import indicators.your_indicator
```

That's it. No changes to fetcher, registry, API, or existing adapters. The new keys automatically flow through Redis to the API and dashboard.

## Critical Points

- **Redis format is unchanged.** The `indicators` dict in Redis still contains the same keys: `rsi_14`, `macd_line`, `macd_signal`, `macd_hist`. API and dashboard require no changes.
- **`output_keys` must match `calculate()` return keys.** If they diverge, `calculate_all()` will produce `None` entries for missing keys when data is insufficient.
- **Self-registration happens on import.** Adapter modules must be imported in `indicators/__init__.py` to be active. If an import is missing, that indicator silently won't run.
- **Signal generation is separate from indicators.** `signal.py` reads from the merged indicator dict by key name. When adding new indicators, update signal logic in `signal.py` if you want them to influence trading signals.
- **Thread safety.** Registration happens once at import time before any threads start. `calculate_all()` is stateless and safe to call from multiple threads concurrently (as the fetcher does via `ThreadPoolExecutor`).

## Current Indicators

| Indicator | Class           | Output Keys                                | Min Data Points |
|-----------|-----------------|--------------------------------------------|-----------------|
| RSI-14    | `RSIIndicator`  | `rsi_14`                                   | 15              |
| MACD      | `MACDIndicator` | `macd_line`, `macd_signal`, `macd_hist`    | 35              |
