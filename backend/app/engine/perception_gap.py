from .derived import PERCEPTION_GAP_ALERT, PERCEPTION_GAP_WATCH, PERCEPTION_SIGNAL_BELOW, PERCEPTION_WEIGHTS
from .types import Status

MOOD_TO_SCORE = 20


def compute(
    mood: int | None, objective_scores: dict[str, float], details: dict[str, str] | None = None
) -> tuple[float | None, float | None, float | None, Status, str, list[str]]:
    """Returns (self_score, objective_score, gap, status, explanation, contributing_signals).
    self = mood × 20; objective = weighted mean of the available scores (derived.PERCEPTION_WEIGHTS);
    gap = self − objective; watch / alert from derived.PERCEPTION_GAP_*. `details` = a short text per score
    (e.g. "Night pulse: +7.0 bpm"), listed as a cause when that score is below PERCEPTION_SIGNAL_BELOW."""
    details = details or {}
    self_score = float(mood * MOOD_TO_SCORE) if mood is not None else None
    scores = {k: v for k, v in objective_scores.items() if v is not None}
    weights = {k: PERCEPTION_WEIGHTS.get(k, 1.0) for k in scores}
    total = sum(weights.values())
    objective = round(sum(scores[k] * weights[k] for k in scores) / total, 1) if total else None

    signals = [
        details.get(k, k) for k, v in sorted(scores.items(), key=lambda kv: kv[1]) if v < PERCEPTION_SIGNAL_BELOW
    ]

    if self_score is None or objective is None:
        return (
            self_score,
            objective,
            None,
            "unknown",
            "Not enough data yet to compare how you feel with your objective data.",
            signals,
        )

    gap = round(self_score - objective, 1)
    if gap >= PERCEPTION_GAP_ALERT:
        status: Status = "alert"
    elif gap >= PERCEPTION_GAP_WATCH:
        status = "watch"
    else:
        status = "ok"

    rated = f"You rate yourself {mood}/5 ({self_score:.0f}/100)"
    data = f"your objective data score {objective:.0f}/100"
    causes = f" ({', '.join(signals)})" if signals else ""
    if status != "ok":
        explanation = f"{rated}, but {data} only{causes}."
    elif abs(gap) <= PERCEPTION_GAP_WATCH / 2:
        explanation = f"{rated} and {data}: they agree."
    elif gap > 0:
        explanation = f"{rated}; {data}, a little lower than how you feel{causes}."
    elif gap > -PERCEPTION_GAP_WATCH:
        explanation = f"{rated}; {data}, a little better than how you feel."
    else:
        explanation = f"{rated}, while {data}: your data look better than you feel."
    return self_score, objective, gap, status, explanation, signals
