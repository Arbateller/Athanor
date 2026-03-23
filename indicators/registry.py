from indicators.base import Indicator

_indicators: list[Indicator] = []


def register(indicator: Indicator) -> None:
    _indicators.append(indicator)


def get_all() -> list[Indicator]:
    return list(_indicators)


def calculate_all(closes: list[float]) -> dict[str, float | None]:
    """Run all registered indicators and merge results into one dict."""
    results = {}
    for ind in _indicators:
        if len(closes) >= ind.min_data_points:
            results.update(ind.calculate(closes))
        else:
            results.update({k: None for k in ind.output_keys})
    return results
