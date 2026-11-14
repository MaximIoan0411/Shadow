import math
from dataclasses import dataclass
from statistics import pstdev

from ..derived import (
    FLIGHT_PAUSE_MS,
    KEYSTROKE_ALERT_FATIGUE,
    KEYSTROKE_FULL_Z,
    KEYSTROKE_WATCH_FATIGUE,
    KEYSTROKE_WEIGHTS,
    KEYSTROKE_Z_CAP,
    MIN_SPREAD,
    PVT_MIN_BASELINE_TESTS,
    PVT_MIN_SPEED_SD,
    PVT_SCORE_PENALTY_PER_SD,
)
from ..types import EvidenceItem, Finding, PillarScore, Status

TOPIC = "behavioral"
TYPING_RECOMMENDATION = "behavioral-1-1"

ACCUMULATORS = ("n_keys", "hold_sum", "hold_sumsq", "flight_n", "flight_sum", "flight_sumsq", "backspaces", "active_ms")
FEATURES = ("hold_ms_mean", "hold_ms_sd", "flight_ms_mean", "flight_ms_sd", "backspace_rate", "keys_per_min")
SLOWER_WHEN_LOWER = {"keys_per_min"}


@dataclass(frozen=True)
class KeyEventIn:
    t_down_ms: float
    t_up_ms: float
    key_class: str


def features_of(obj) -> dict:
    return {f: getattr(obj, f) for f in (*FEATURES, "n_keys")}


def _mean_sd(total: float, total_sq: float, n: int) -> tuple[float, float]:
    if n == 0:
        return 0.0, 0.0
    mean = total / n
    return mean, math.sqrt(max(total_sq / n - mean * mean, 0.0))


def accumulate(acc: dict, events: list[KeyEventIn]) -> dict:
    """Adds one batch to the session accumulators (the KeystrokeSession columns) and returns the new accumulators
    plus the derived features. hold = up − down; flight = down − previous down, across batches through
    `last_down_ms`; pauses longer than FLIGHT_PAUSE_MS (and timer resets) are not typing time."""
    a = {k: acc.get(k) or 0 for k in ACCUMULATORS}
    last = acc.get("last_down_ms")
    for e in sorted(events, key=lambda e: e.t_down_ms):
        hold = max(e.t_up_ms - e.t_down_ms, 0.0)
        a["n_keys"] += 1
        a["hold_sum"] += hold
        a["hold_sumsq"] += hold * hold
        if e.key_class == "backspace":
            a["backspaces"] += 1
        if last is not None and 0 <= e.t_down_ms - last <= FLIGHT_PAUSE_MS:
            flight = e.t_down_ms - last
            a["flight_n"] += 1
            a["flight_sum"] += flight
            a["flight_sumsq"] += flight * flight
            a["active_ms"] += flight
        last = e.t_down_ms

    hold_mean, hold_sd = _mean_sd(a["hold_sum"], a["hold_sumsq"], a["n_keys"])
    flight_mean, flight_sd = _mean_sd(a["flight_sum"], a["flight_sumsq"], a["flight_n"])
    return {
        **a,
        "last_down_ms": last,
        "hold_ms_mean": hold_mean,
        "hold_ms_sd": hold_sd,
        "flight_ms_mean": flight_mean,
        "flight_ms_sd": flight_sd,
        "backspace_rate": a["backspaces"] / a["n_keys"] if a["n_keys"] else 0.0,
        "keys_per_min": a["flight_n"] / a["active_ms"] * 60000 if a["active_ms"] > 0 else 0.0,
    }


def typing_baseline(sessions: list[dict], *, min_sessions: int) -> dict:
    """The personal typing baseline from the feature dicts of the baseline sessions: the mean of every feature and,
    for the features used by the fatigue index, the spread between sessions (never below derived.MIN_SPREAD)."""
    n = len(sessions)
    mean = {f: sum(s[f] for s in sessions) / n if n else 0.0 for f in FEATURES}
    sd = {f: max(pstdev([s[f] for s in sessions]) if n > 1 else 0.0, MIN_SPREAD[f]) for f in KEYSTROKE_WEIGHTS}
    return {
        "mean": mean,
        "sd": sd,
        "sessions": n,
        "n_keys": sum(int(s.get("n_keys", 0)) for s in sessions),
        "ready": n >= min_sessions,
    }


def fatigue_index(features: dict, baseline: dict) -> tuple[float, dict[str, float]]:
    """(0..100, deviation_z per feature). Only changes in the "tired" direction count: longer holds, longer flights,
    more backspaces, lower speed. Hold time and speed weigh the most (derived.KEYSTROKE_WEIGHTS); a weighted
    deviation of KEYSTROKE_FULL_Z personal spreads gives 100."""
    z = {f: (features[f] - baseline["mean"][f]) / baseline["sd"][f] for f in KEYSTROKE_WEIGHTS}
    worse = {f: min(max(-v if f in SLOWER_WHEN_LOWER else v, 0.0), KEYSTROKE_Z_CAP) for f, v in z.items()}
    weighted = sum(KEYSTROKE_WEIGHTS[f] * worse[f] for f in z)
    index = min(100.0, 100.0 * weighted / KEYSTROKE_FULL_Z)
    return round(index, 1), {f: round(v, 2) for f, v in z.items()}


def status_for(fatigue: float | None) -> Status:
    if fatigue is None:
        return "unknown"
    if fatigue >= KEYSTROKE_ALERT_FATIGUE:
        return "alert"
    if fatigue >= KEYSTROKE_WATCH_FATIGUE:
        return "watch"
    return "ok"


def _pct(value: float, base: float) -> float:
    return (value - base) / base * 100 if base else 0.0


def typing_finding(crew_id: str, features: dict, baseline: dict, fatigue: float | None, *, day: int) -> Finding | None:
    status = status_for(fatigue)
    if status not in ("watch", "alert"):
        return None
    mean = baseline["mean"]
    speed_pct = _pct(features["keys_per_min"], mean["keys_per_min"])
    hold_pct = _pct(features["hold_ms_mean"], mean["hold_ms_mean"])
    if speed_pct <= -5:
        title = f"Typing {abs(speed_pct):.0f}% slower than usual"
    elif hold_pct >= 5:
        title = f"Key presses {hold_pct:.0f}% longer than usual"
    else:
        title = "Typing rhythm changed from your usual"
    return Finding(
        crew_id=crew_id,
        topic=TOPIC,
        level=1,
        status=status,
        title=title,
        explanation=(
            f"Your typing rhythm has drifted from your personal baseline (fatigue index {fatigue:.0f}/100). "
            "Typing rhythm can change with fatigue even when you feel rested. "
            "Only the timing of key presses is analysed, never what you type."
        ),
        evidence=(
            EvidenceItem(
                metric_key="keys_per_min",
                label="Typing speed",
                value=round(features["keys_per_min"], 1),
                unit="keys/min",
                baseline=round(mean["keys_per_min"], 1),
                deviation_text=f"{speed_pct:+.0f}% vs your baseline",
            ),
            EvidenceItem(
                metric_key="hold_ms_mean",
                label="Key hold time",
                value=round(features["hold_ms_mean"], 1),
                unit="ms",
                baseline=round(mean["hold_ms_mean"], 1),
                deviation_text=f"{hold_pct:+.0f}% vs your baseline",
            ),
        ),
        recommendation_id=TYPING_RECOMMENDATION,
        day=day,
        extra={"fatigue_index": fatigue, "speed_pct": round(speed_pct, 1), "hold_pct": round(hold_pct, 1)},
    )


def pvt_summary(trials: list[dict], *, lapse_ms: float) -> dict:
    """mean_rt_ms, mean_speed (mean of 1000/RT, in 1/s), lapses (no answer or RT >= lapse_ms), false_starts,
    n_trials. False starts do not count as reaction times."""
    false_starts = sum(1 for t in trials if t.get("false_start"))
    answered = [t for t in trials if not t.get("false_start")]
    rts = [t["rt_ms"] for t in answered if t.get("rt_ms") is not None and t["rt_ms"] > 0]
    lapses = sum(1 for t in answered if t.get("rt_ms") is None or t["rt_ms"] >= lapse_ms)
    return {
        "n_trials": len(trials),
        "mean_rt_ms": round(sum(rts) / len(rts), 1) if rts else 0.0,
        "mean_speed": round(sum(1000 / rt for rt in rts) / len(rts), 3) if rts else 0.0,
        "lapses": lapses,
        "false_starts": false_starts,
    }


def pvt_baseline(speeds: list[float]) -> tuple[float, float] | None:
    """(mean speed, spread) of the non-practice tests so far, or None while there are too few."""
    if len(speeds) < PVT_MIN_BASELINE_TESTS:
        return None
    return sum(speeds) / len(speeds), max(pstdev(speeds), PVT_MIN_SPEED_SD)


def pvt_finding(
    crew_id: str, speed: float, base_speed: float, base_sd: float, *, reliable_change_sd: float, day: int
) -> Finding | None:
    """Watch (level 1, behavioral-1-1) when the reaction speed drops by at least `reliable_change_sd` personal
    spreads (the reliable change threshold from parameters.json)."""
    dev = (speed - base_speed) / base_sd
    if dev > -reliable_change_sd:
        return None
    pct = _pct(speed, base_speed)
    return Finding(
        crew_id=crew_id,
        topic=TOPIC,
        level=1,
        status="watch",
        title=f"Reaction speed {abs(pct):.0f}% below your baseline",
        explanation=(
            f"Your reaction test was {abs(dev):.1f} personal spreads slower than your baseline. "
            "Reaction speed can drop with fatigue even when you feel rested."
        ),
        evidence=(
            EvidenceItem(
                metric_key="pvt_mean_speed",
                label="Reaction speed (PVT-B)",
                value=round(speed, 2),
                unit="1/s",
                baseline=round(base_speed, 2),
                deviation_text=f"{pct:+.0f}% ({dev:+.1f} SD) vs your baseline",
            ),
        ),
        recommendation_id=TYPING_RECOMMENDATION,
        day=day,
        extra={"deviation_sd": round(dev, 2)},
    )


def score(fatigue: float | None, pvt_dev_sd: float | None) -> PillarScore:
    """100 = like the personal baseline. Typing part = 100 − fatigue index; reaction-test part = 100 minus
    PVT_SCORE_PENALTY_PER_SD for every personal spread below the baseline speed; the mean of the parts available."""
    parts = []
    if fatigue is not None:
        parts.append(100.0 - fatigue)
    if pvt_dev_sd is not None:
        parts.append(max(0.0, 100.0 - PVT_SCORE_PENALTY_PER_SD * max(-pvt_dev_sd, 0.0)))
    if not parts:
        return PillarScore(score=None, status="unknown", headline="Learning your typing rhythm")
    status = status_for(fatigue) if fatigue is not None else "ok"
    if status in ("watch", "alert"):
        headline = f"Typing rhythm changed (fatigue index {fatigue:.0f}/100)"
    else:
        status = "ok"
        headline = "Typing rhythm within your usual range"
    return PillarScore(score=round(sum(parts) / len(parts), 1), status=status, headline=headline)
