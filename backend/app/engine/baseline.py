"""Normalul personal din zbor. TASK T12."""
from .types import Baseline, Point


def compute(points: list[Point], *, min_n: int, min_spread: float = 0.0, exclude_days: set[int] | None = None,
            window_days: int | None = None) -> Baseline:
    """Mediana + deviația robustă (1.4826 × MAD) a ultimelor `window_days` zile, fără `exclude_days`
    (zilele aflate în alertă: altfel boala devine normalul). ready = n >= min_n."""
    raise NotImplementedError("T12")


def deviation(value: float, base: Baseline) -> float:
    """Abaterea în deviații personale: (value - median) / spread."""
    raise NotImplementedError("T12")
