from typing import Protocol


class Indicator(Protocol):
    """Protocol that all indicator adapters must satisfy."""

    @property
    def name(self) -> str: ...

    @property
    def min_data_points(self) -> int: ...

    @property
    def output_keys(self) -> list[str]: ...

    def calculate(self, closes: list[float]) -> dict[str, float | None]: ...
