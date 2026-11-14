"""Santinela: NightSignal (Alavi et al. 2022), temperatura, indicele de stres. TASK T14."""
from ..types import Baseline, Finding, PillarScore, Point


def night_signal(crew_id: str, nights: list[Point], base: Baseline, *, yellow_delta: float, red_delta: float,
                 red_nights: int, day: int) -> Finding | None:
    """Galben: ultima noapte >= +yellow_delta (sau o noapte >= +red_delta) → nivel 1, recomandarea immune-1-1.
    Roșu: ultimele `red_nights` nopți toate >= +red_delta → nivel 2, immune-2-1. None dacă nu e nimic sau
    baseline-ul nu e gata."""
    raise NotImplementedError("T14")


def stress_index(fatigue_index: float | None, isolation_days: int, dose_ratio: float | None) -> float:
    """0..100 din oboseala tastării, zilele de izolare și raportul dozei de radiații față de medie."""
    raise NotImplementedError("T14")


def score(nights: list[Point], base: Baseline, finding: Finding | None) -> PillarScore:
    raise NotImplementedError("T14")
