def mean_24h(rates: list[float]) -> float:
    return sum(rates) / len(rates) if rates else 0.0


def is_alert(recent_rates: list[float], mean: float, threshold_ratio: float, consecutive: int) -> bool:
    """True when the last `consecutive` readings are all >= threshold_ratio × mean."""
    if mean <= 0 or len(recent_rates) < consecutive:
        return False
    return all(r >= threshold_ratio * mean for r in recent_rates[-consecutive:])


def event_dose_msv(points: list[tuple[float, float]]) -> float:
    """Dose accumulated over the readings (hours since the first one, µSv/h), in mSv, by the trapezoid rule."""
    total = 0.0
    for (t0, r0), (t1, r1) in zip(points, points[1:], strict=False):
        total += (r0 + r1) / 2 * (t1 - t0)
    return total / 1000
