"""Tastatura: trăsăturile tastării, indicele de oboseală, PVT-B. TASK T19 (tastare) și T20 (PVT)."""
from dataclasses import dataclass

from ..types import Finding, PillarScore


@dataclass(frozen=True)
class KeyEventIn:
    t_down_ms: float
    t_up_ms: float
    key_class: str


def accumulate(acc: dict, events: list[KeyEventIn]) -> dict:
    """Adaugă un lot la acumulatorii sesiunii (vezi coloanele KeystrokeSession). Pauzele > FLIGHT_PAUSE_MS nu intră
    în flight. Întoarce acumulatorii noi + trăsăturile derivate (hold/flight mean/sd, backspace_rate, keys_per_min)."""
    raise NotImplementedError("T19")


def fatigue_index(features: dict, baseline: dict) -> tuple[float, dict[str, float]]:
    """(0..100, deviation_z pe trăsătură). Cântăresc mai mult hold și viteza; backspace puțin."""
    raise NotImplementedError("T19")


def pvt_summary(trials: list[dict], *, lapse_ms: float) -> dict:
    """mean_rt_ms, mean_speed (media 1/RT în 1/s), lapses (RT >= lapse_ms), false_starts, n_trials."""
    raise NotImplementedError("T20")


def pvt_finding(crew_id: str, speed: float, base_speed: float, base_sd: float, *, reliable_change_sd: float, day: int) -> Finding | None:
    raise NotImplementedError("T20")


def score(fatigue: float | None, pvt_dev_sd: float | None) -> PillarScore:
    raise NotImplementedError("T19")
