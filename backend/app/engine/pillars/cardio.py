import math

from ..derived import (
    CARDIO_MIN_CV,
    CARDIO_PENALTY_PER_BPM,
    CARDIO_PENALTY_PER_LN_HRV,
    CARDIO_PENALTY_SYSTOLIC,
    CARDIO_WINDOW_DAYS,
)
from ..types import Baseline, EvidenceItem, Finding, PillarScore, Point

TOPIC = "cardio"
WATCH_RECOMMENDATION = "cardio-1-1"
ALERT_RECOMMENDATION = "cardio-2-1"


def _mean_ending(points: list[Point], day: int, window: int = CARDIO_WINDOW_DAYS) -> float | None:
    values = [p.value for p in points if day - window < p.day <= day]
    return sum(values) / len(values) if len(values) >= window // 2 + 1 else None


def _cv(base: Baseline, metric: str, default_pct: float) -> float:
    """The personal coefficient of variation (spread / median), never below derived.CARDIO_MIN_CV; the default from
    parameters.json when there is no baseline."""
    if base.ready and base.median and not math.isnan(base.median):
        return max(base.spread / base.median, CARDIO_MIN_CV[metric])
    return default_pct / 100


def _ready(base: Baseline | None) -> bool:
    return base is not None and base.ready and not math.isnan(base.median)


def landing_readiness(
    resting_pulse: list[Point],
    hrv: list[Point],
    systolic: list[Point],
    bases: dict[str, Baseline],
    params: dict,
    *,
    crew_id: str = "",
    day: int | None = None,
) -> tuple[PillarScore, Finding | None]:
    """Landing readiness 0..100 against the IN-FLIGHT baseline (never the Earth one: in flight the pressure drops and
    the pulse does not rise normally). Derived thresholds from parameters.json:
    resting pulse — 7-day mean > baseline + 1×CV on `hr_min_days` days in a row → watch;
    HRV (lnRMSSD) — 7-day mean < baseline − 0.5×CV → watch; both → level 2 (cardio-2-1), one → level 1 (cardio-1-1).
    Score = 100 − penalties for the pulse above, the HRV below and a systolic drop beyond the threshold."""
    hr_base, hrv_base, sbp_base = bases.get("resting_pulse_bpm"), bases.get("hrv_lnrmssd"), bases.get("systolic_mmhg")
    if not (_ready(hr_base) and _ready(hrv_base)) or not resting_pulse or not hrv:
        return PillarScore(score=None, status="unknown", headline="Learning your in-flight normal"), None
    day = day if day is not None else max(resting_pulse[-1].day, hrv[-1].day)

    hr_limit = hr_base.median * (1 + _cv(hr_base, "resting_pulse_bpm", params["hr_cv_default_pct"]))
    hr_days = 0
    for d in range(day, day - params["hr_min_days"], -1):
        m = _mean_ending(resting_pulse, d)
        if m is None or m <= hr_limit:
            break
        hr_days += 1
    hr_flag = hr_days >= params["hr_min_days"]

    hrv_limit = hrv_base.median * (1 - 0.5 * _cv(hrv_base, "hrv_lnrmssd", params["hrv_cv_default_pct"]))
    hrv_mean = _mean_ending(hrv, day)
    hrv_flag = hrv_mean is not None and hrv_mean < hrv_limit

    hr_mean = _mean_ending(resting_pulse, day)
    sbp_mean = _mean_ending(systolic, day)
    sbp_flag = _ready(sbp_base) and sbp_mean is not None and sbp_mean - sbp_base.median <= params["sbp_drop_mmhg"]

    hr_delta = (hr_mean - hr_base.median) if hr_mean is not None else 0.0
    hrv_delta = (hrv_mean - hrv_base.median) if hrv_mean is not None else 0.0
    score = 100.0 - CARDIO_PENALTY_PER_BPM * max(hr_delta, 0.0) - CARDIO_PENALTY_PER_LN_HRV * max(-hrv_delta, 0.0)
    score = round(min(100.0, max(0.0, score - (CARDIO_PENALTY_SYSTOLIC if sbp_flag else 0.0))), 1)

    if hr_flag and hrv_flag:
        level, status, rec = 2, "alert", ALERT_RECOMMENDATION
        title = f"Resting pulse {hr_delta:+.0f} bpm and HRV down: heart deconditioning"
    elif hr_flag or hrv_flag:
        level, status, rec = 1, "watch", WATCH_RECOMMENDATION
        title = (
            f"Resting pulse {hr_delta:+.0f} bpm above your in-flight normal"
            if hr_flag
            else "Heart rate variability below your in-flight normal"
        )
    else:
        return PillarScore(score=score, status="ok", headline="Within your in-flight range"), None

    finding = Finding(
        crew_id=crew_id,
        topic=TOPIC,
        level=level,
        status=status,
        title=title,
        explanation=(
            f"Your landing readiness score is {score:.0f}/100. Compared with your own in-flight normal, "
            "your heart is adapting to weightlessness more than usual. These thresholds are derived from sports "
            "medicine and are a working hypothesis, not validated on astronauts."
        ),
        evidence=(
            EvidenceItem(
                metric_key="resting_pulse_bpm",
                label="Resting pulse (7-day mean)",
                value=round(hr_mean, 1) if hr_mean is not None else None,
                unit="bpm",
                baseline=round(hr_base.median, 1),
                deviation_text=f"{hr_delta:+.1f} bpm vs your in-flight normal",
            ),
            EvidenceItem(
                metric_key="hrv_lnrmssd",
                label="Heart rate variability (7-day mean)",
                value=round(hrv_mean, 2) if hrv_mean is not None else None,
                unit="ln(ms)",
                baseline=round(hrv_base.median, 2),
                deviation_text=f"{hrv_delta:+.2f} vs your in-flight normal",
            ),
        ),
        recommendation_id=rec,
        day=day,
        extra={"landing_readiness": score},
    )
    return PillarScore(score=score, status=status, headline=title), finding
