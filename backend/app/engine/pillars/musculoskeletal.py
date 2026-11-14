from itertools import combinations

from ..derived import (
    LOADING_FULL_REPS,
    LOADING_REF_SESSION_RAW,
    LOADING_REF_SESSION_SCORE,
    LOADING_SPLIT_BONUS,
    LOADING_SPLIT_GAP_H,
    LOADING_SPLIT_RATE_FACTOR,
    LOADING_TAIL_WEIGHT,
    LOADING_WATCH_FRACTION,
)
from ..types import PillarScore

PROJECTION_NOTE = (
    "Estimate, not a measurement: bone density cannot be measured on board. The benefit of splitting the training "
    "is shown only in animals (Robling 2002)."
)


def session_score(sets: list[dict]) -> float:
    """Σ reps × load, with diminishing returns after the first LOADING_FULL_REPS reps of every set (bone responds
    mostly to the first loading cycles), scaled so that a normal session gives LOADING_REF_SESSION_SCORE."""
    raw = 0.0
    for s in sets:
        reps, load = int(s.get("reps", 0)), float(s.get("load_kg", 0.0))
        effective = min(reps, LOADING_FULL_REPS) + LOADING_TAIL_WEIGHT * max(reps - LOADING_FULL_REPS, 0)
        raw += effective * load
    return round(raw / LOADING_REF_SESSION_RAW * LOADING_REF_SESSION_SCORE, 1)


def is_split(session_hours: list[float]) -> bool:
    return any(abs(a - b) >= LOADING_SPLIT_GAP_H for a, b in combinations(session_hours, 2))


def daily_loading(session_scores: list[tuple[float, float]]) -> float:
    """(hour of day, score) for the sessions of the day: the sum, +20% when two sessions are at least 4 hours apart."""
    total = sum(score for _hour, score in session_scores)
    if is_split([hour for hour, _score in session_scores]):
        total *= 1 + LOADING_SPLIT_BONUS
    return round(total, 1)


def split_recommended(completed_sessions: int) -> bool:
    return completed_sessions < 2


def projection(adherence: float, split: bool, params: dict) -> tuple[float, float]:
    """(loss %/month with the current plan, with the split training). The rate moves from the ARED value towards the
    pre-ARED one as adherence drops; the split plan is assumed a little better. Estimate, not a measurement."""
    adherence = min(max(adherence, 0.0), 1.0)
    ared, pre_ared = params["rata_cu_ARED_sold_total"], params["rata_pre_ARED_trohanter_max"]
    current = ared + (1 - adherence) * (pre_ared - ared)
    with_split = current * LOADING_SPLIT_RATE_FACTOR
    if split:
        current = with_split
    return round(current, 2), round(with_split, 2)


def score(loading_today: float, target: float) -> PillarScore:
    value = round(min(100.0, loading_today / target * 100), 1) if target else None
    if value is None:
        return PillarScore(score=None, status="unknown", headline="No exercise plan")
    if loading_today < target * LOADING_WATCH_FRACTION:
        return PillarScore(
            score=value, status="watch", headline=f"Bone loading {loading_today:.0f}/{target:.0f}: below plan"
        )
    return PillarScore(score=value, status="ok", headline=f"Bone loading {loading_today:.0f}/{target:.0f}: on track")
