import re
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..clock import clock
from ..datafiles import DataBundle
from ..db import repos
from ..db.models.alerts import Alert, AlertHistory, PlanStep
from ..db.models.measurements import KeystrokeSession
from ..db.models.users import Crew
from ..engine import triage
from ..engine.derived import MIN_SPREAD
from ..engine.pillars import behavioral, immune
from ..engine.types import Finding, PillarScore, Point, TriageDecision
from ..ids import next_id
from ..schemas import AlertBrief
from .events import Event

SHADOW_ACTOR = "SHADOW"

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
        cause="unknown",
        cause_explanation="",
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
    # TODO T23: level 3 → link.queue.enqueue (packet to Earth)


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

    open_levels = {key: (a.id, a.level) for key, a in open_alerts.items()}
    for decision in triage.decide(findings, open_levels):
        if decision.action == "create":
            alert = await create_alert(session, decision.finding, data, at)
            result.alerts_created.append(alert.id)
            result.events.append(Event("alert.created", brief(alert), crew_id))
        elif decision.action in ("update", "escalate"):
            alert = open_alerts[(decision.finding.crew_id, decision.finding.topic)]
            await _update(session, alert, decision, data, at)
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
    crew_ids = (await session.scalars(select(Crew.id).order_by(Crew.id))).all()
    for crew_id in crew_ids:
        series = await _load_immune_series(session, crew_id, until_day)
        typing_base = await typing_baseline(session, crew_id, data)
        typing_by_day: dict[int, list[KeystrokeSession]] = {}
        for row in await repos.keystroke_sessions(session, crew_id, 1, until_day):
            typing_by_day.setdefault(row.mission_day, []).append(row)
        for day in range(1, until_day + 1):
            await process(
                session,
                crew_id,
                set(IMMUNE_METRICS),
                day=day,
                data=data,
                at=review_time(data, day),
                _series={m: _up_to(points, day) for m, points in series.items()},
            )
            for row in typing_by_day.get(day, []):
                if row.is_baseline or not typing_base["ready"]:
                    continue
                row.fatigue_index, _z = behavioral.fatigue_index(behavioral.features_of(row), typing_base)
                row.status = behavioral.status_for(row.fatigue_index)
                if row.status in ("watch", "alert"):
                    await process(
                        session,
                        crew_id,
                        {"keys_per_min"},
                        day=day,
                        data=data,
                        at=row.updated_at,
                        _typing=(row, typing_base),
                    )
