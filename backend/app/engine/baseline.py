import math
from statistics import median

from .types import Baseline, Point

MAD_TO_SD = 1.4826


def compute(
    points: list[Point],
    *,
    min_n: int,
    min_spread: float = 0.0,
    exclude_days: set[int] | None = None,
    window_days: int | None = None,
) -> Baseline:
    excluded = exclude_days or set()
    kept = [p for p in points if p.day not in excluded]
    if window_days is not None and points:
        last_day = max(p.day for p in points)
        kept = [p for p in kept if p.day > last_day - window_days]

    values = [p.value for p in kept]
    if not values:
        return Baseline(median=math.nan, spread=min_spread, n=0, ready=False)

    mid = median(values)
    mad = median(abs(v - mid) for v in values)
    return Baseline(median=mid, spread=max(MAD_TO_SD * mad, min_spread), n=len(values), ready=len(values) >= min_n)


def deviation(value: float, base: Baseline) -> float:
    if base.spread == 0 or math.isnan(base.median):
        return math.nan
    return (value - base.median) / base.spread
