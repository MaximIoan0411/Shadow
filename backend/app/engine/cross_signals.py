from .derived import (
    CROSS_SIGNAL_BASE_CONFIDENCE,
    CROSS_SIGNAL_CONFIDENCE_PER_SIGNAL,
    CROSS_SIGNAL_MAX_CONFIDENCE,
    ENVIRONMENTAL_MIN_CREW,
    WEAK_SIGNALS,
)
from .types import EvidenceItem, Finding

PILLAR_OF_SIGNAL = {
    "night_pulse_bpm": "immune",
    "temperature_c": "immune",
    "sleep_hours": "immune",
    "keys_per_min": "behavioral",
}
LABEL = {
    "night_pulse_bpm": ("Night pulse", "bpm"),
    "temperature_c": ("Temperature", "°C"),
    "sleep_hours": ("Sleep", "h"),
    "keys_per_min": ("Typing speed", "%"),
}
ENVIRONMENTAL_TOPIC = {
    "night_pulse_bpm": "immune",
    "temperature_c": "immune",
    "sleep_hours": "behavioral",
    "keys_per_min": "behavioral",
}
ENVIRONMENTAL_RECOMMENDATION = {
    "night_pulse_bpm": "immune-1-1",
    "temperature_c": "immune-1-1",
    "sleep_hours": "behavioral-1-5",
    "keys_per_min": "behavioral-1-5",
}


def _signal_key(f: Finding) -> str:
    return f.extra.get("signal", f.topic)


def weak_signals(crew_id: str, day: int, observations: dict[str, tuple[float, float]]) -> list[Finding]:
    """Small deviations (derived.WEAK_SIGNALS) of one person on one day. `observations` = metric → (value, personal
    median). They are not alerts by themselves."""
    out = []
    for metric, (direction, threshold) in WEAK_SIGNALS.items():
        if metric not in observations:
            continue
        value, median = observations[metric]
        if direction == "down_pct":
            delta = (value - median) / median * 100 if median else 0.0
            hit = delta <= -threshold
            text = f"Typing: {delta:+.0f}% speed"
        else:
            delta = value - median
            hit = delta >= threshold if direction == "up" else delta <= -threshold
            label, unit = LABEL[metric]
            text = f"{label}: {delta:+.1f} {unit}"
        if not hit:
            continue
        label, unit = LABEL[metric]
        out.append(
            Finding(
                crew_id=crew_id,
                topic=PILLAR_OF_SIGNAL[metric],
                level=1,
                status="watch",
                title=text,
                explanation="",
                evidence=(
                    EvidenceItem(
                        metric_key=metric,
                        label=label,
                        value=round(value, 2),
                        unit="keys/min" if metric == "keys_per_min" else unit,
                        baseline=round(median, 2),
                        deviation_text=text,
                    ),
                ),
                recommendation_id=ENVIRONMENTAL_RECOMMENDATION[metric],
                day=day,
                extra={"signal": metric, "delta": round(delta, 2)},
            )
        )
    return out


def environmental_cause(findings_today: list[Finding], crew_count: int) -> set[str]:
    """The signals (or topics) that at least ENVIRONMENTAL_MIN_CREW members share on the same day → an environmental
    cause (the cabin), not an individual one."""
    crew_by_key: dict[str, set[str]] = {}
    for f in findings_today:
        crew_by_key.setdefault(_signal_key(f), set()).add(f.crew_id)
    needed = min(ENVIRONMENTAL_MIN_CREW, crew_count)
    return {key for key, crew in crew_by_key.items() if len(crew) >= needed}


def environmental_finding(signal: Finding, affected: int, crew_count: int) -> Finding:
    metric = _signal_key(signal)
    label = LABEL[metric][0]
    return Finding(
        crew_id=signal.crew_id,
        topic=ENVIRONMENTAL_TOPIC[metric],
        level=1,
        status="watch",
        title=f"{label} changed for the whole crew ({affected} of {crew_count})",
        explanation=f"{signal.title} for you, and the same change for {affected} of {crew_count} crew members today.",
        evidence=signal.evidence,
        recommendation_id=ENVIRONMENTAL_RECOMMENDATION[metric],
        day=signal.day,
        extra={
            "signal": metric,
            "cause": "environmental",
            "cause_explanation": (
                f"The same deviation in {affected} of {crew_count} crew members: the problem is probably in the cabin "
                "(light, noise, temperature, schedule), not in you."
            ),
        },
    )


def detect(findings_window: list[Finding]) -> list[dict]:
    """Weak signals of one person over the last CROSS_SIGNAL_WINDOW_DAYS days, from at least 2 different pillars →
    one cross signal (contract shape: id, title, pillars, signals, confidence, explanation). Signals with an
    environmental cause are left out by the caller."""
    by_crew: dict[str, list[Finding]] = {}
    for f in findings_window:
        by_crew.setdefault(f.crew_id, []).append(f)
    out = []
    for crew_id, found in sorted(by_crew.items()):
        pillars = sorted({f.topic for f in found})
        if len(pillars) < 2:
            continue
        latest: dict[str, Finding] = {}
        for f in sorted(found, key=lambda f: f.day):
            latest[_signal_key(f)] = f
        signals = [f.title for f in latest.values()]
        confidence = min(
            CROSS_SIGNAL_MAX_CONFIDENCE,
            CROSS_SIGNAL_BASE_CONFIDENCE + CROSS_SIGNAL_CONFIDENCE_PER_SIGNAL * len(signals),
        )
        immune = "immune" in pillars
        out.append(
            {
                "id": f"xs-{crew_id}-{max(f.day for f in found)}",
                "title": "Possible onset of an illness" if immune else "Several small changes at once",
                "pillars": pillars,
                "signals": signals,
                "confidence": round(confidence, 2),
                "explanation": (
                    f"{len(signals)} weak, independent signals from {len(pillars)} pillars point the same way. "
                    "Each one alone is not an alert; together they weigh more."
                ),
            }
        )
    return out
