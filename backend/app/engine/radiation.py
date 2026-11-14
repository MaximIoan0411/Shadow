"""Detectorul de furtună. TASK T25."""


def mean_24h(rates: list[float]) -> float:
    raise NotImplementedError("T25")


def is_alert(recent_rates: list[float], mean: float, threshold_ratio: float, consecutive: int) -> bool:
    """True dacă ultimele `consecutive` citiri sunt toate >= threshold_ratio × mean."""
    raise NotImplementedError("T25")
