import re
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta

from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..clock import clock
from ..datafiles import DataBundle
from ..db import repos
from ..db.models.alerts import Alert, AlertHistory, PlanStep
from ..db.models.measurements import KeystrokeSession, Measurement
from ..db.models.users import Crew
from ..engine import cross_signals, triage
from ..engine.baseline import compute
from ..engine.derived import CARDIO_ADAPTATION_DAYS, CARDIO_WINDOW_DAYS, CROSS_SIGNAL_WINDOW_DAYS, MIN_SPREAD
from ..engine.pillars import behavioral, cardio, immune
from ..engine.types import Finding, PillarScore, Point, TriageDecision
from ..ids import next_id
from ..schemas import AlertBrief
from .events import Event

SHADOW_ACTOR = "SHADOW"
INDIVIDUAL_CAUSE = "Only you have this deviation; the rest of the crew is within their usual range."

IMMUNE_METRICS = ("night_pulse_bpm", "temperature_c", "sleep_hours")
TYPING_METRICS = {"keys_per_min", "hold_ms_mean", "flight_ms_mean"}
PILLAR_OF_METRIC = {
    **dict.fromkeys(IMMUNE_METRICS, "immune"),
    **dict.fromkeys(("keys_per_min", "hold_ms_mean", "flight_ms_mean", "pvt_mean_speed"), "behavioral"),
    **dict.fromkeys(("resting_pulse_bpm", "hrv_lnrmssd", "systolic_mmhg", "diastolic_mmhg"), "cardio"),
    **dict.fromkeys(("loading_score",), "musculoskeletal"),
}

REVIEW_TIME = time(7, 0)


@dataclass
class PipelineResult:
    alerts_created: list[str] = field(default_factory=list)
    alerts_updated: list[str] = field(default_factory=list)
    events: list[Event] = field(default_factory=list)


def review_time(data: DataBundle, day: int) -> datetime:
    start = data.scenario.start + timedelta(days=day - 1)
    return start + timedelta(hours=REVIEW_TIME.hour, minutes=REVIEW_TIME.minute)


async def _load_immune_series(session: AsyncSession, crew_id: str, to_day: int) -> dict[str, list[Point]]:
    return {m: await repos.series(session, crew_id, m, 1, to_day) for m in IMMUNE_METRICS}


def _up_to(points: list[Point], day: int) -> list[Point]:
    return [p for p in points if p.day <= day]


def _immune_finding(
    crew_id: str, day: int, series: dict[str, list[Point]], data: DataBundle, alert_since: int | None
) -> Finding | None:
    v = data.params.value
    min_n = v("nightsignal_min_nights_baseline")
    excluded = set(range(alert_since, day + 1)) if alert_since is not None else set()

    def base(metric: str):
        return immune.baseline_before(
            series[metric], day, min_n=min_n, min_spread=MIN_SPREAD.get(metric, 0.0), exclude_days=excluded
        )

    def today(metric: str) -> Point | None:
        return next((p for p in reversed(series[metric]) if p.day == day), None)

    return immune.night_signal(
        crew_id,
        series["night_pulse_bpm"],
        base("night_pulse_bpm"),
        yellow_delta=v("nightsignal_yellow_delta"),
        red_delta=v("nightsignal_red_delta_bpm"),
        red_nights=v("nightsignal_red_consecutive_nights"),
        day=day,
        temperature=today("temperature_c"),
        temperature_base=base("temperature_c"),
        sleep=today("sleep_hours"),
        sleep_base=base("sleep_hours"),
    )


@dataclass
class ImmuneSnapshot:
    score: PillarScore
    finding: Finding | None
    night_delta_bpm: float | None


async def immune_snapshot(session: AsyncSession, crew_id: str, day: int, data: DataBundle) -> ImmuneSnapshot:
    """The Sentinel pillar for one day, with the same rules as process() (used by the perception gap, T21)."""
    series = await _load_immune_series(session, crew_id, day)
    open_immune = (await _open_alerts(session, crew_id)).get((crew_id, "immune"))
    since = open_immune.mission_day if open_immune else None
    finding = _immune_finding(crew_id, day, series, data, since)
    nights = series["night_pulse_bpm"]
    excluded = set(range(since, day + 1)) if since is not None else set()
    base = immune.baseline_before(
        nights,
        day,
        min_n=data.params.value("nightsignal_min_nights_baseline"),
        min_spread=MIN_SPREAD["night_pulse_bpm"],
        exclude_days=excluded,
    )
    delta = nights[-1].value - base.median if nights and base.ready else None
    return ImmuneSnapshot(score=immune.score(nights, base, finding), finding=finding, night_delta_bpm=delta)


CARDIO_METRICS = ("resting_pulse_bpm", "hrv_lnrmssd", "systolic_mmhg")
LANDING_READINESS = "landing_readiness"


def cardio_params(data: DataBundle) -> dict:
    v = data.params.value
    hr, hrv = v("prag_hr_repaus_crestere"), v("prag_hrv_lnrmssd")
    return {
        "hr_cv_default_pct": hr["CV_implicit_daca_lipseste_pct"],
        "hr_min_days": hr["minim_zile_consecutive"],
        "hrv_cv_default_pct": hrv["CV_implicit_daca_lipseste_pct"],
        "sbp_drop_mmhg": v("prag_tas_scadere_in_zbor"),
    }


def cardio_day(
    crew_id: str, day: int, series: dict[str, list[Point]], data: DataBundle, alert_since: int | None
) -> tuple[PillarScore, Finding | None]:
    """The Heart pillar for one day. The in-flight baseline uses the days after the adaptation period and before
    the last 7-day window (minus the days of an open heart alert)."""
    excluded = set(range(alert_since, day + 1)) if alert_since is not None else set()
    upto = {m: [p for p in series[m] if p.day <= day] for m in CARDIO_METRICS}
    bases = {
        m: compute(
            [p for p in upto[m] if CARDIO_ADAPTATION_DAYS < p.day <= day - CARDIO_WINDOW_DAYS],
            min_n=CARDIO_WINDOW_DAYS,
            exclude_days=excluded,
        )
        for m in CARDIO_METRICS
    }
    return cardio.landing_readiness(
        upto["resting_pulse_bpm"],
        upto["hrv_lnrmssd"],
        upto["systolic_mmhg"],
        bases,
        cardio_params(data),
        crew_id=crew_id,
        day=day,
    )


async def _load_cardio_series(session: AsyncSession, crew_id: str, to_day: int) -> dict[str, list[Point]]:
    return {m: await repos.series(session, crew_id, m, 1, to_day) for m in CARDIO_METRICS}


async def _save_readiness(
    session: AsyncSession, crew_id: str, day: int, score: float, at: datetime, source: str
) -> None:
    await session.execute(
        delete(Measurement).where(
            Measurement.crew_id == crew_id, Measurement.metric_key == LANDING_READINESS, Measurement.mission_day == day
        )
    )
    session.add(
        Measurement(
            crew_id=crew_id,
            metric_key=LANDING_READINESS,
            value=score,
            unit="/100",
            measured_at=at,
            mission_day=day,
            source=source,
        )
    )


async def typing_baseline(session: AsyncSession, crew_id: str, data: DataBundle) -> dict:
    rows = await repos.keystroke_baseline_sessions(session, crew_id)
    return behavioral.typing_baseline(
        [behavioral.features_of(r) for r in rows], min_sessions=int(data.params.value("keystroke_baseline_duration"))
    )


async def _typing_finding(
    session: AsyncSession, crew_id: str, day: int, data: DataBundle, preloaded: tuple[KeystrokeSession, dict] | None
) -> Finding | None:
    if preloaded is not None:
        row, base = preloaded
    else:
        row = await repos.latest_keystroke_session(session, crew_id, day, from_day=day)
        base = await typing_baseline(session, crew_id, data)
    if row is None or not base["ready"]:
        return None
    return behavioral.typing_finding(crew_id, behavioral.features_of(row), base, row.fatigue_index, day=day)


async def _open_alerts(session: AsyncSession, crew_id: str) -> dict[tuple[str, str], Alert]:
    stmt = (
        select(Alert)
        .where(Alert.crew_id == crew_id, Alert.state != "resolved")
        .options(selectinload(Alert.steps), selectinload(Alert.history))
    )
    return {(a.crew_id, a.topic): a for a in (await session.scalars(stmt)).all()}


def _steps_text(data: DataBundle, recommendation_id: str) -> list[str]:
    entry = data.catalog.by_id()[recommendation_id]
    if entry.steps:
        return list(entry.steps)
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", entry.action) if s.strip()]


def _evidence(finding: Finding) -> list[dict]:
    return [
        {
            "metric_key": e.metric_key,
            "label": e.label,
            "value": e.value,
            "unit": e.unit,
            "baseline": e.baseline,
            "deviation_text": e.deviation_text,
        }
        for e in finding.evidence
    ]


def brief(alert: Alert) -> dict:
    return AlertBrief(
        id=alert.id,
        crew_id=alert.crew_id,
        topic=alert.topic,
        level=alert.level,
        status=alert.status,
        state=alert.state,
        title=alert.title,
        created_at=alert.created_at,
    ).model_dump(mode="json")


async def create_alert(session: AsyncSession, finding: Finding, data: DataBundle, at: datetime) -> Alert:
    entry = data.catalog.by_id()[finding.recommendation_id]
    alert = Alert(
        id=await next_id(session, "al"),
        crew_id=finding.crew_id,
        topic=finding.topic,
        level=finding.level,
        status=finding.status,
        state="active",
        title=finding.title,
        explanation=finding.explanation,
        cause=finding.extra.get("cause", "individual"),
        cause_explanation=finding.extra.get("cause_explanation", INDIVIDUAL_CAUSE),
        evidence=_evidence(finding),
        recommendation_id=finding.recommendation_id,
        recheck_at=at + timedelta(days=entry.recheck_days),
        created_at=at,
        updated_at=at,
        mission_day=finding.day,
    )
    alert.steps = _plan(data, finding.recommendation_id)
    alert.history = [AlertHistory(at=at, actor=SHADOW_ACTOR, role=None, action="created")]
    session.add(alert)
    await session.flush()
    return alert


def _plan(data: DataBundle, recommendation_id: str) -> list[PlanStep]:
    return [
        PlanStep(step_id=f"st-{i}", position=i, text=text, done=False)
        for i, text in enumerate(_steps_text(data, recommendation_id), 1)
    ]


async def _update(
    session: AsyncSession, alert: Alert, decision: TriageDecision, data: DataBundle, at: datetime
) -> None:
    f = decision.finding
    alert.title = f.title
    alert.explanation = f.explanation
    alert.evidence = _evidence(f)
    alert.updated_at = at
    if "cause" in f.extra:
        alert.cause, alert.cause_explanation = f.extra["cause"], f.extra.get("cause_explanation", "")
    if f.status == "alert":
        alert.status = "alert"
    if decision.action == "escalate":
        alert.level = decision.new_level
        alert.status = f.status
        alert.state = "escalated"
        if alert.recommendation_id != f.recommendation_id:
            alert.recommendation_id = f.recommendation_id
            alert.steps.clear()
            await session.flush()
            alert.steps.extend(_plan(data, f.recommendation_id))
            alert.recheck_at = at + timedelta(days=data.catalog.by_id()[f.recommendation_id].recheck_days)
        alert.history.append(
            AlertHistory(
                at=at,
                actor=SHADOW_ACTOR,
                role=None,
                action="escalated",
                note=f"Escalated automatically to level {decision.new_level}.",
            )
        )


async def _send_level3(session: AsyncSession, alert: Alert, data: DataBundle) -> None:
    if alert.level >= 3 and alert.packet_id is None:
        from . import link as link_service

        await link_service.send_alert_to_earth(
            session, data, alert, sender=SHADOW_ACTOR, note="Escalated automatically by the triage engine."
        )


async def process(
    session: AsyncSession,
    crew_id: str,
    changed: set[str],
    *,
    day: int,
    data: DataBundle,
    at: datetime | None = None,
    reason: str | None = None,
    _series: dict[str, list[Point]] | None = None,
    _typing: tuple[KeystrokeSession, dict] | None = None,
    extra_findings: list[Finding] | None = None,
) -> PipelineResult:
    """Runs only the rules of the pillars touched by `changed`, then triage, then writes the alerts.
    Returns the events to publish AFTER commit. Does not commit."""
    at = at or clock.now()
    result = PipelineResult()
    pillars = {PILLAR_OF_METRIC[m] for m in changed if m in PILLAR_OF_METRIC}
    open_alerts = await _open_alerts(session, crew_id)

    findings: list[Finding] = list(extra_findings or [])
    if "immune" in pillars:
        series = _series or await _load_immune_series(session, crew_id, day)
        open_immune = open_alerts.get((crew_id, "immune"))
        finding = _immune_finding(crew_id, day, series, data, open_immune.mission_day if open_immune else None)
        if finding:
            findings.append(finding)
    if changed & TYPING_METRICS:
        finding = await _typing_finding(session, crew_id, day, data, _typing)
        if finding:
            findings.append(finding)
    if "cardio" in pillars:
        open_cardio = open_alerts.get((crew_id, "cardio"))
        score, finding = cardio_day(
            crew_id,
            day,
            await _load_cardio_series(session, crew_id, day),
            data,
            open_cardio.mission_day if open_cardio else None,
        )
        if score.score is not None:
            await _save_readiness(session, crew_id, day, score.score, at, "manual")
        if finding:
            findings.append(finding)

    open_levels = {key: (a.id, a.level) for key, a in open_alerts.items()}
    for decision in triage.decide(findings, open_levels):
        if decision.action == "create":
            alert = await create_alert(session, decision.finding, data, at)
            await _send_level3(session, alert, data)
            result.alerts_created.append(alert.id)
            result.events.append(Event("alert.created", brief(alert), crew_id))
        elif decision.action in ("update", "escalate"):
            alert = open_alerts[(decision.finding.crew_id, decision.finding.topic)]
            await _update(session, alert, decision, data, at)
            await _send_level3(session, alert, data)
            result.alerts_updated.append(alert.id)
            result.events.append(Event("alert.updated", brief(alert), crew_id))
    await session.flush()

    if reason is not None:
        result.events.append(Event("dashboard.changed", {"reason": reason}, crew_id))
    return result


async def replay_history(session: AsyncSession, *, until_day: int, data: DataBundle) -> None:
    """At startup: process() day by day for 1..until_day, so the alerts in the history are produced by the engine.
    "Now" is the replayed day (given as `at`), the clock is not moved. No events are published."""
    if await session.scalar(select(Alert.id).limit(1)) is not None:
        return
    await replay_days(session, data, 1, until_day)


async def replay_days(session: AsyncSession, data: DataBundle, first: int, last: int) -> None:
    """The engine over days [first, last] for the whole crew, day by day: each member's rules, then the crew-wide
    (environmental) check, then the rechecks. Used at startup (1..96) and by the day jump (T33)."""
    crew_ids = (await session.scalars(select(Crew.id).order_by(Crew.id))).all()
    pre = {crew_id: await _crew_history(session, crew_id, last, data) for crew_id in crew_ids}
    readiness = []
    cardio_since: dict[str, int | None] = {}
    for crew_id in crew_ids:
        open_cardio = (await _open_alerts(session, crew_id)).get((crew_id, "cardio"))
        cardio_since[crew_id] = open_cardio.mission_day if open_cardio else None
    await session.execute(
        delete(Measurement).where(
            Measurement.metric_key == LANDING_READINESS, Measurement.mission_day.between(first, last)
        )
    )
    for day in range(first, last + 1):
        at = review_time(data, day)
        signals_today: dict[str, list[Finding]] = {}
        for crew_id in crew_ids:
            h = pre[crew_id]
            score, cardio_finding = cardio_day(crew_id, day, h.cardio, data, cardio_since[crew_id])
            if cardio_finding and cardio_since[crew_id] is None:
                cardio_since[crew_id] = day
            if score.score is not None:
                readiness.append(
                    {
                        "crew_id": crew_id,
                        "metric_key": LANDING_READINESS,
                        "value": score.score,
                        "unit": "/100",
                        "measured_at": at,
                        "mission_day": day,
                        "source": "simulated",
                    }
                )
            await process(
                session,
                crew_id,
                set(IMMUNE_METRICS),
                day=day,
                data=data,
                at=at,
                _series={m: _up_to(points, day) for m, points in h.immune.items()},
                extra_findings=[cardio_finding] if cardio_finding else None,
            )
            for row in h.typing_by_day.get(day, []):
                if row.is_baseline or not h.typing_base["ready"] or row.fatigue_index is not None:
                    continue
                row.fatigue_index, _z = behavioral.fatigue_index(behavioral.features_of(row), h.typing_base)
                row.status = behavioral.status_for(row.fatigue_index)
                if row.status in ("watch", "alert"):
                    await process(
                        session,
                        crew_id,
                        {"keys_per_min"},
                        day=day,
                        data=data,
                        at=row.updated_at,
                        _typing=(row, h.typing_base),
                    )
            signals_today[crew_id] = cross_signals.weak_signals(crew_id, day, observations_for_day(h, day, data))
        await environmental_pass(session, data, day, signals_today, at)
        await recheck_due(session, data, at)
    if readiness:
        await session.execute(insert(Measurement), readiness)


# --------------------------------------------------------------------------- weak signals, cause, cross signals


@dataclass
class CrewHistory:
    immune: dict[str, list[Point]]
    cardio: dict[str, list[Point]]
    typing_base: dict
    typing_by_day: dict[int, list[KeystrokeSession]]


async def _crew_history(session: AsyncSession, crew_id: str, to_day: int, data: DataBundle) -> CrewHistory:
    typing_by_day: dict[int, list[KeystrokeSession]] = {}
    for row in await repos.keystroke_sessions(session, crew_id, 1, to_day):
        typing_by_day.setdefault(row.mission_day, []).append(row)
    return CrewHistory(
        immune=await _load_immune_series(session, crew_id, to_day),
        cardio=await _load_cardio_series(session, crew_id, to_day),
        typing_base=await typing_baseline(session, crew_id, data),
        typing_by_day=typing_by_day,
    )


def observations_for_day(h: CrewHistory, day: int, data: DataBundle) -> dict[str, tuple[float, float]]:
    """metric → (the day's value, the personal median from the days before), for the weak signals."""
    min_n = data.params.value("nightsignal_min_nights_baseline")
    out = {}
    for metric in IMMUNE_METRICS:
        today = next((p for p in reversed(h.immune[metric]) if p.day == day), None)
        if today is None:
            continue
        base = immune.baseline_before(h.immune[metric], day, min_n=min_n)
        if base.ready:
            out[metric] = (today.value, base.median)
    rows = [r for r in h.typing_by_day.get(day, []) if r.n_keys and not r.is_baseline]
    if rows and h.typing_base["ready"]:
        out["keys_per_min"] = (rows[-1].keys_per_min, h.typing_base["mean"]["keys_per_min"])
    return out


async def environmental_pass(
    session: AsyncSession, data: DataBundle, day: int, signals_today: dict[str, list[Finding]], at: datetime
) -> list[Event]:
    """The same weak signal at ≥ ENVIRONMENTAL_MIN_CREW members on the same day → a level 1 alert for each of them,
    with cause = environmental."""
    every = [f for signals in signals_today.values() for f in signals]
    shared = cross_signals.environmental_cause(every, len(signals_today))
    events: list[Event] = []
    for key in sorted(shared):
        matching = [f for f in every if f.extra.get("signal") == key]
        for signal in matching:
            env = cross_signals.environmental_finding(signal, len(matching), len(signals_today))
            result = await process(session, signal.crew_id, set(), day=day, data=data, at=at, extra_findings=[env])
            events += result.events
    return events


async def cross_signals_for(session: AsyncSession, crew_id: str, day: int, data: DataBundle) -> list[dict]:
    """The cross signals of one person for the dashboard: weak signals of the last CROSS_SIGNAL_WINDOW_DAYS days,
    without the ones the whole crew shares (environmental)."""
    first = max(1, day - CROSS_SIGNAL_WINDOW_DAYS + 1)
    crew_ids = (await session.scalars(select(Crew.id).order_by(Crew.id))).all()
    histories = {c: await _crew_history(session, c, day, data) for c in crew_ids}
    mine: list[Finding] = []
    for d in range(first, day + 1):
        today = {c: cross_signals.weak_signals(c, d, observations_for_day(h, d, data)) for c, h in histories.items()}
        shared = cross_signals.environmental_cause([f for fs in today.values() for f in fs], len(crew_ids))
        mine += [f for f in today.get(crew_id, []) if f.extra.get("signal") not in shared]
    return cross_signals.detect(mine)


# --------------------------------------------------------------------------- recheck (T30)


async def _recheck_verdict(session: AsyncSession, alert: Alert, day: int, data: DataBundle) -> str:
    """ "resolved" (values back to normal), "worse" (still above the threshold) or "nodata" (nothing new to judge)."""
    if alert.topic == "radiation":
        from . import radiation as radiation_service

        status = await radiation_service.status(session, data)
        return "resolved" if status.event is None or status.ratio < status.threshold_ratio else "nodata"

    if alert.cause == "environmental":
        h = await _crew_history(session, alert.crew_id, day, data)
        metric = alert.evidence[0]["metric_key"] if alert.evidence else None
        observations = observations_for_day(h, day, data)
        if metric not in observations:
            return "nodata"
        signals = cross_signals.weak_signals(alert.crew_id, day, observations)
        return "worse" if any(s.extra["signal"] == metric for s in signals) else "resolved"

    if alert.topic == "immune":
        series = await _load_immune_series(session, alert.crew_id, day)
        if not any(p.day == day for p in series["night_pulse_bpm"]):
            return "nodata"
        return "worse" if _immune_finding(alert.crew_id, day, series, data, alert.mission_day) else "resolved"

    if alert.topic == "behavioral":
        row = await repos.latest_keystroke_session(session, alert.crew_id, day, from_day=day, judged_only=True)
        if row is None or row.updated_at <= alert.updated_at:
            return "nodata"
        base = await typing_baseline(session, alert.crew_id, data)
        finding = behavioral.typing_finding(
            alert.crew_id, behavioral.features_of(row), base, row.fatigue_index, day=day
        )
        return "worse" if finding else "resolved"

    if alert.topic == "cardio":
        series = await _load_cardio_series(session, alert.crew_id, day)
        if not any(p.day == day for p in series["resting_pulse_bpm"]):
            return "nodata"
        _score, finding = cardio_day(alert.crew_id, day, series, data, alert.mission_day)
        return "worse" if finding else "resolved"
    return "nodata"


async def recheck_due(session: AsyncSession, data: DataBundle, now: datetime | None = None) -> list[Event]:
    """Open alerts whose `recheck_at` has come: values back to normal → resolved by SHADOW; still above the
    threshold → one level up (max 3) and a new recheck date; no new data → wait. Does not commit."""
    now = now or clock.now()
    day = clock.mission_day(now)
    stmt = (
        select(Alert)
        .where(Alert.state != "resolved", Alert.recheck_at.is_not(None), Alert.recheck_at <= now)
        .options(selectinload(Alert.steps), selectinload(Alert.history))
    )
    events: list[Event] = []
    for alert in (await session.scalars(stmt)).all():
        verdict = await _recheck_verdict(session, alert, day, data)
        if verdict == "nodata":
            continue
        alert.updated_at = now
        if verdict == "resolved":
            note = "Values back to normal."
            alert.state = "resolved"
            alert.history.append(AlertHistory(at=now, actor=SHADOW_ACTOR, role=None, action="rechecked", note=note))
            alert.history.append(AlertHistory(at=now, actor=SHADOW_ACTOR, role=None, action="resolved", note=note))
        else:
            alert.level = min(alert.level + 1, 3)
            alert.status, alert.state = "alert", "escalated"
            days = data.catalog.by_id()[alert.recommendation_id].recheck_days
            alert.recheck_at = now + timedelta(days=days)
            alert.history.append(
                AlertHistory(
                    at=now,
                    actor=SHADOW_ACTOR,
                    role=None,
                    action="rechecked",
                    note=f"Still above the threshold: moved to level {alert.level}.",
                )
            )
            await _send_level3(session, alert, data)
        events.append(Event("alert.updated", brief(alert), alert.crew_id))
    await session.flush()
    return events
