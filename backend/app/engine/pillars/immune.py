import math

from ..baseline import compute
from ..derived import (
    SENTINEL_SCORE_PENALTY_PER_BPM,
    STRESS_DOSE_RATIO_FULL,
    STRESS_ISOLATION_FULL_DAYS,
    STRESS_WEIGHTS,
)
from ..types import Baseline, EvidenceItem, Finding, PillarScore, Point

TOPIC = "immune"
YELLOW_RECOMMENDATION = "immune-1-1"
RED_RECOMMENDATION = "immune-2-1"


def baseline_before(
    nights: list[Point], day: int, *, min_n: int, min_spread: float = 0.0, exclude_days: set[int] | None = None
) -> Baseline:
    return compute([p for p in nights if p.day < day], min_n=min_n, min_spread=min_spread, exclude_days=exclude_days)


def _signed(value: float, unit: str, digits: int = 1) -> str:
    return f"{value:+.{digits}f} {unit}"


def evidence(label: str, metric_key: str, unit: str, point: Point | None, base: Baseline | None) -> EvidenceItem:
    value = point.value if point else None
    median = base.median if base and base.ready and not math.isnan(base.median) else None
    if value is None or median is None:
        text = "No personal baseline yet" if value is not None else "No recent value"
    else:
        text = f"{_signed(value - median, unit)} vs your in-flight median"
    return EvidenceItem(
        metric_key=metric_key,
        label=label,
        value=value,
        unit=unit,
        baseline=None if median is None else round(median, 1),
        deviation_text=text,
    )


def _run_ending_at(nights: list[Point], day: int, median: float, threshold: float) -> list[Point]:
    by_day = {p.day: p for p in nights}
    run: list[Point] = []
    d = day
    while d in by_day and by_day[d].value - median >= threshold:
        run.append(by_day[d])
        d -= 1
    return run


def night_signal(
    crew_id: str,
    nights: list[Point],
    base: Baseline,
    *,
    yellow_delta: float,
    red_delta: float,
    red_nights: int,
    day: int,
    temperature: Point | None = None,
    temperature_base: Baseline | None = None,
    sleep: Point | None = None,
    sleep_base: Baseline | None = None,
) -> Finding | None:
    """NightSignal (Alavi et al. 2022) on the night pulse vs the personal median.
    Red: the last `red_nights` consecutive nights all >= +red_delta → level 2.
    Yellow: tonight >= +yellow_delta → level 1. None when nothing is wrong or the baseline is not ready."""
    if not base.ready or math.isnan(base.median):
        return None
    tonight = next((p for p in nights if p.day == day), None)
    if tonight is None:
        return None

    delta = tonight.value - base.median
    red_run = _run_ending_at(nights, day, base.median, red_delta)
    if len(red_run) >= red_nights:
        level, status, rec, run = 2, "alert", RED_RECOMMENDATION, red_run
    elif delta >= yellow_delta:
        level, status, rec, run = (
            1,
            "watch",
            YELLOW_RECOMMENDATION,
            _run_ending_at(nights, day, base.median, yellow_delta),
        )
    else:
        return None

    n = len(run)
    nights_text = "1 night" if n == 1 else f"{n} nights in a row"
    title = f"Night pulse {_signed(delta, 'bpm', 0)}, {nights_text}"
    if level == 2:
        explanation = (
            f"Your night pulse has been at least {red_delta:g} bpm above your personal median "
            f"({base.median:.1f} bpm) for {n} nights in a row. In the NightSignal study this pattern often "
            "came before symptoms of an infection. Tell the crew medical officer."
        )
    else:
        explanation = (
            f"Last night your pulse was {_signed(delta, 'bpm')} above your personal median "
            f"({base.median:.1f} bpm). One night can have many causes (stress, short sleep, hard exercise); "
            "the next nights will show whether it continues."
        )
    items = (
        EvidenceItem(
            metric_key="night_pulse_bpm",
            label="Night pulse",
            value=tonight.value,
            unit="bpm",
            baseline=round(base.median, 1),
            deviation_text=f"{_signed(delta, 'bpm')} above your personal median, {nights_text}",
        ),
        evidence("Temperature", "temperature_c", "°C", temperature, temperature_base),
        evidence("Sleep", "sleep_hours", "h", sleep, sleep_base),
    )
    return Finding(
        crew_id=crew_id,
        topic=TOPIC,
        level=level,
        status=status,
        title=title,
        explanation=explanation,
        evidence=items,
        recommendation_id=rec,
        day=day,
        extra={"delta_bpm": round(delta, 1), "nights": n, "median_bpm": round(base.median, 1)},
    )


def stress_index(fatigue_index: float | None, isolation_days: int, dose_ratio: float | None) -> float:
    """0..100, a weighted mean of three parts, each scaled to 0..100:
    fatigue = the typing fatigue index; isolation = days in isolation / STRESS_ISOLATION_FULL_DAYS;
    dose = (dose ratio − 1) / (STRESS_DOSE_RATIO_FULL − 1). Missing parts are left out and the
    remaining weights are rescaled. Weights: derived.STRESS_WEIGHTS (team choice)."""
    parts: dict[str, float] = {"isolation": min(max(isolation_days, 0) / STRESS_ISOLATION_FULL_DAYS, 1.0) * 100}
    if fatigue_index is not None:
        parts["fatigue"] = min(max(fatigue_index, 0.0), 100.0)
    if dose_ratio is not None:
        parts["dose"] = min(max((dose_ratio - 1) / (STRESS_DOSE_RATIO_FULL - 1), 0.0), 1.0) * 100
    total_weight = sum(STRESS_WEIGHTS[k] for k in parts)
    return round(sum(STRESS_WEIGHTS[k] * v for k, v in parts.items()) / total_weight, 1)


def score(nights: list[Point], base: Baseline, finding: Finding | None) -> PillarScore:
    if not base.ready or math.isnan(base.median) or not nights:
        return PillarScore(score=None, status="unknown", headline=f"Learning your normal ({base.n} nights so far)")
    delta = nights[-1].value - base.median
    value = round(min(100.0, max(0.0, 100.0 - SENTINEL_SCORE_PENALTY_PER_BPM * max(delta, 0.0))), 1)
    if finding is None:
        return PillarScore(score=value, status="ok", headline="Night pulse within your in-flight range")
    return PillarScore(score=value, status=finding.status, headline=finding.title)
