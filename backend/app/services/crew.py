import math
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..clock import clock
from ..datafiles import BodyFunction, DataBundle
from ..db import repos
from ..db.models.alerts import Alert as AlertRow
from ..db.models.measurements import Checkin as CheckinRow
from ..db.models.measurements import ExerciseSession, KeystrokeSession, Measurement
from ..db.models.measurements import PvtResult as PvtRow
from ..db.models.users import Crew
from ..deps import ApiError
from ..engine.baseline import compute
from ..engine.derived import MIN_SPREAD
from ..engine.pillars import behavioral, immune
from ..engine.types import Point
from ..schemas import (
    CrewMember,
    CrewSummary,
    Dashboard,
    DataSource,
    MetricSeries,
    MetricValue,
    Pillar,
    PillarDetail,
    PillarSummary,
    PlanStep,
    Reminder,
    SeriesPoint,
    Status,
    Streak,
    Timeline,
    TimelineDay,
)
from . import alerts as alerts_service
from . import behavioral as behavioral_service
from . import checkins as checkins_service
from . import pipeline

ORDER = (Pillar.behavioral, Pillar.cardio, Pillar.immune, Pillar.musculoskeletal)
RANK = {"unknown": 0, "ok": 1, "watch": 2, "alert": 3}
CHART_DAYS = 10

# pillars without engine rules yet (T27, T28): fixed placeholder values, shown as simulated
PLACEHOLDER = {
    Pillar.cardio: (88.0, "Within your in-flight range"),
    Pillar.musculoskeletal: (82.0, "Exercise plan on track"),
}

METRICS = {
    Pillar.behavioral: {
        "keys_per_min": ("Typing speed", "keys/min"),
        "hold_ms_mean": ("Key hold time", "ms"),
        "pvt_mean_speed": ("Reaction speed (PVT-B)", "1/s"),
    },
    Pillar.cardio: {
        "resting_pulse_bpm": ("Resting pulse", "bpm"),
        "hrv_lnrmssd": ("Heart rate variability", "ln(ms)"),
        "systolic_mmhg": ("Blood pressure (systolic)", "mmHg"),
        "diastolic_mmhg": ("Blood pressure (diastolic)", "mmHg"),
    },
    Pillar.immune: {
        "night_pulse_bpm": ("Night pulse", "bpm"),
        "temperature_c": ("Temperature", "°C"),
        "sleep_hours": ("Sleep", "h"),
    },
    Pillar.musculoskeletal: {"exercise_sessions": ("Exercise sessions", "sessions/day")},
}
CHART_METRIC = {
    Pillar.behavioral: "keys_per_min",
    Pillar.cardio: "resting_pulse_bpm",
    Pillar.immune: "night_pulse_bpm",
    Pillar.musculoskeletal: "exercise_sessions",
}
TOPIC_LABEL = {
    "behavioral": "Typing",
    "cardio": "Heart",
    "immune": "Sentinel",
    "musculoskeletal": "Loading",
    "radiation": "Radiation",
    "cross_signal": "Cross-signal",
}
SCENARIO_EVENT_LABELS = {"solar_storm": "Solar storm"}


def worst(statuses) -> Status:
    statuses = list(statuses)
    return Status(max(statuses, key=lambda s: RANK[s])) if statuses else Status.unknown


def current_day() -> int:
    return clock.mission_day()


def check_as_of(as_of_day: int | None) -> int:
    today = current_day()
    if as_of_day is not None and as_of_day > today:
        raise ApiError(
            422,
            "validation_error",
            f"Day {as_of_day} has not happened yet (current day: {today}).",
            {"fields": [{"field": "as_of_day", "problem": "in the future"}]},
        )
    return as_of_day or today


def _as_of(day: int) -> datetime:
    return clock.now() if day == current_day() else clock.day_start(day + 1) - timedelta(seconds=1)


def _body(data: DataBundle, pillar: Pillar) -> BodyFunction:
    return next(b for b in data.body.pillars if b.pillar == pillar)


async def _member(session: AsyncSession, crew_id: str) -> CrewMember:
    c = await session.get(Crew, crew_id)
    if c is None:
        raise ApiError(404, "not_found", f"Crew member {crew_id} does not exist.")
    return CrewMember(
        id=c.id, display_name=c.display_name, initials=c.initials, role_title=c.role_title, is_cmo=c.is_cmo
    )


async def _open_alerts(session: AsyncSession, crew_id: str, day: int) -> list[AlertRow]:
    """Alerts that were open at the end of `day` (created by then and not resolved by then)."""
    stmt = (
        select(AlertRow)
        .where(AlertRow.crew_id == crew_id, AlertRow.mission_day <= day)
        .options(selectinload(AlertRow.steps), selectinload(AlertRow.history))
    )
    out = []
    for a in (await session.scalars(stmt)).all():
        resolved = [h for h in a.history if h.action == "resolved"]
        if not resolved or clock.mission_day(resolved[-1].at) > day:
            out.append(a)
    return out


def _alert_for(alerts: list[AlertRow], pillar: Pillar) -> AlertRow | None:
    mine = [a for a in alerts if a.topic == pillar.value]
    return max(mine, key=lambda a: (a.level, a.created_at)) if mine else None


# --------------------------------------------------------------------------- pillar scores


async def _latest_typing(session: AsyncSession, crew_id: str, day: int) -> KeystrokeSession | None:
    return await repos.latest_keystroke_session(session, crew_id, day, from_day=day - 1, judged_only=True)


async def _pillar_summaries(
    session: AsyncSession, data: DataBundle, crew_id: str, day: int, alerts: list[AlertRow]
) -> list[PillarSummary]:
    out = []
    for pillar in ORDER:
        body = _body(data, pillar)
        alert = _alert_for(alerts, pillar)
        if pillar == Pillar.immune:
            snap = await pipeline.immune_snapshot(session, crew_id, day, data)
            score, status, headline = snap.score.score, snap.score.status, snap.score.headline
        elif pillar == Pillar.behavioral:
            typing = await _latest_typing(session, crew_id, day)
            _pvt, pvt_sd, _text = await behavioral_service.pvt_snapshot(session, crew_id, day)
            s = behavioral.score(typing.fatigue_index if typing else None, pvt_sd)
            score, status, headline = s.score, s.status, s.headline
        else:
            score, headline = PLACEHOLDER[pillar]
            status = "ok"
        if alert is not None:
            status = worst([status, alert.status])
            headline = alert.title
        out.append(
            PillarSummary(
                pillar=pillar,
                name=body.name,
                body_zone=body.body_zone,
                status=status,
                score=score,
                headline=headline,
                hazard=body.hazard,
                active_alert_id=alert.id if alert else None,
            )
        )
    return out


# --------------------------------------------------------------------------- streaks and reminders


def _run_until(days: set[int], day: int) -> tuple[int, int]:
    start = day if day in days else day - 1
    current = 0
    while start - current in days:
        current += 1
    best = run = 0
    for d in range(1, day + 1):
        run = run + 1 if d in days else 0
        best = max(best, run)
    return current, best


async def _streaks(session: AsyncSession, crew_id: str, day: int) -> list[Streak]:
    checkin = await checkins_service.streak(session, crew_id, day)
    counts = dict(
        (
            await session.execute(
                select(ExerciseSession.mission_day, func.count())
                .where(ExerciseSession.crew_id == crew_id, ExerciseSession.mission_day <= day)
                .group_by(ExerciseSession.mission_day)
            )
        ).all()
    )
    split_now, split_best = _run_until({d for d, n in counts.items() if n >= 2}, day)
    pvt_days = set(
        (
            await session.scalars(
                select(PvtRow.mission_day).where(PvtRow.crew_id == crew_id, PvtRow.mission_day <= day)
            )
        ).all()
    )
    pvt_now, pvt_best = _run_until(pvt_days, day)
    return [
        checkin,
        Streak(key="split_training", label="Training in two sessions", days=split_now, best=split_best),
        Streak(key="pvt", label="Reaction test", days=pvt_now, best=pvt_best),
    ]


async def _reminders(session: AsyncSession, crew_id: str, day: int, checkin_done: bool) -> list[Reminder]:
    start = clock.day_start(day)
    now = _as_of(day)
    pvt_done = (
        await session.scalar(
            select(func.count()).select_from(PvtRow).where(PvtRow.crew_id == crew_id, PvtRow.mission_day == day)
        )
        or 0
    ) > 0
    sessions = (
        await session.scalar(
            select(func.count())
            .select_from(ExerciseSession)
            .where(ExerciseSession.crew_id == crew_id, ExerciseSession.mission_day == day)
        )
        or 0
    )
    items = [
        ("rm-1", "checkin", "Morning check-in", 7, checkin_done),
        ("rm-2", "pvt", "Reaction test (3 minutes)", 9, pvt_done),
        ("rm-3", "exercise", "Second exercise session", 16, sessions >= 2),
    ]
    return [
        Reminder(
            id=rid,
            kind=kind,
            label=label,
            due_at=start + timedelta(hours=hour),
            done=done,
            overdue=not done and start + timedelta(hours=hour) < now,
        )
        for rid, kind, label, hour, done in items
    ]


# --------------------------------------------------------------------------- dashboard


async def dashboard(session: AsyncSession, data: DataBundle, crew_id: str, as_of_day: int | None) -> Dashboard:
    day = check_as_of(as_of_day)
    member = await _member(session, crew_id)
    alerts = await _open_alerts(session, crew_id, day)
    pillars = await _pillar_summaries(session, data, crew_id, day, alerts)

    checkin = await session.scalar(
        select(CheckinRow).where(CheckinRow.crew_id == crew_id, CheckinRow.mission_day == day)
    )
    gap = await checkins_service.gap_for(
        session, data, crew_id, day, checkin.mood if checkin else None, checkin.sleep_hours if checkin else None
    )
    top = max(alerts, key=lambda a: (a.level, RANK[a.status], a.created_at)) if alerts else None
    return Dashboard(
        crew=member,
        as_of=_as_of(day),
        mission_day=day,
        overall_status=worst([p.status for p in pillars] + [a.status for a in alerts]),
        pillars=pillars,
        perception_gap=gap,
        cross_signals=[],  # TODO T29
        alerts_active_count=len(alerts),
        top_alert=alerts_service.brief(top) if top else None,
        streaks=await _streaks(session, crew_id, day),
        reminders=await _reminders(session, crew_id, day, checkin is not None),
        radiation_alert_active=False,  # TODO T25
        checkin_done_today=checkin is not None,
    )


# --------------------------------------------------------------------------- series


async def _daily_points(session: AsyncSession, crew_id: str, metric: str, from_day: int, to_day: int) -> list[Point]:
    if metric in ("keys_per_min", "hold_ms_mean"):
        rows = await repos.keystroke_sessions(session, crew_id, from_day, to_day)
        by_day = {r.mission_day: Point(r.mission_day, r.updated_at, getattr(r, metric)) for r in rows if r.n_keys}
        return [by_day[d] for d in sorted(by_day)]
    if metric == "pvt_mean_speed":
        stmt = (
            select(PvtRow)
            .where(PvtRow.crew_id == crew_id, PvtRow.mission_day.between(from_day, to_day))
            .order_by(PvtRow.at)
        )
        by_day = {r.mission_day: Point(r.mission_day, r.at, r.mean_speed) for r in (await session.scalars(stmt)).all()}
        return [by_day[d] for d in sorted(by_day)]
    if metric == "exercise_sessions":
        stmt = (
            select(ExerciseSession.mission_day, func.count(), func.max(ExerciseSession.started_at))
            .where(ExerciseSession.crew_id == crew_id, ExerciseSession.mission_day.between(from_day, to_day))
            .group_by(ExerciseSession.mission_day)
        )
        found = {d: Point(d, at, float(n)) for d, n, at in (await session.execute(stmt)).all()}
        return [found.get(d) or Point(d, clock.day_start(d), 0.0) for d in range(from_day, to_day + 1)]
    return await repos.series(session, crew_id, metric, from_day, to_day)


def _band(points: list[Point], metric: str, *, min_n: int) -> tuple[float | None, float | None, float | None]:
    base = compute(points, min_n=min_n, min_spread=MIN_SPREAD.get(metric, 0.0))
    if not base.ready or math.isnan(base.median):
        return None, None, None
    return round(base.median, 2), round(base.median - base.spread, 2), round(base.median + base.spread, 2)


async def series(
    session: AsyncSession,
    data: DataBundle,
    crew_id: str,
    pillar: Pillar,
    metric: str,
    from_day: int,
    to_day: int | None,
    *,
    alerts: list[AlertRow] | None = None,
) -> MetricSeries:
    if metric not in METRICS[pillar]:
        raise ApiError(404, "not_found", f"Metric {metric} does not exist in the {pillar.value} pillar.")
    label, unit = METRICS[pillar][metric]
    last = min(to_day or current_day(), current_day())
    first = min(from_day, last)
    history = await _daily_points(session, crew_id, metric, 1, last)
    exclude = set()
    for a in alerts if alerts is not None else await _open_alerts(session, crew_id, last):
        if a.topic == pillar.value:
            exclude |= set(range(a.mission_day, last + 1))
    min_n = int(data.params.value("nightsignal_min_nights_baseline"))
    base, low, high = _band([p for p in history if p.day not in exclude], metric, min_n=min_n)

    threshold, threshold_label = None, None
    if metric == "night_pulse_bpm" and base is not None:
        red = data.params.value("nightsignal_red_delta_bpm")
        nights = data.params.value("nightsignal_red_consecutive_nights")
        threshold, threshold_label = round(base + red, 2), f"+{red:g} bpm, {nights} nights (NightSignal)"

    def status(v: float | None) -> Status | None:
        if v is None or base is None:
            return None
        if threshold is not None:
            return Status.alert if v >= threshold else Status.ok
        return Status.ok if low <= v <= high else Status.watch

    points = [
        SeriesPoint(day=p.day, t=p.t, value=round(p.value, 2), status=status(p.value))
        for p in history
        if p.day >= first
    ]
    return MetricSeries(
        metric_key=metric,
        label=label,
        unit=unit,
        baseline=base,
        band_low=low,
        band_high=high,
        threshold=threshold,
        threshold_label=threshold_label,
        points=points,
    )


# --------------------------------------------------------------------------- pillar panel


def _metric_value(key: str, label: str, unit: str, chart: MetricSeries, source: DataSource) -> MetricValue:
    last = chart.points[-1] if chart.points else None
    value = last.value if last else None
    base = chart.baseline
    dev = round(value - base, 2) if value is not None and base is not None else None
    pct = round(dev / base * 100, 1) if dev is not None and base else None
    return MetricValue(
        key=key,
        label=label,
        value=value,
        unit=unit,
        baseline=base,
        deviation_abs=dev,
        deviation_pct=pct,
        status=last.status if last and last.status else Status.unknown,
        source=source,
        measured_at=last.t if last else None,
    )


async def _source(session: AsyncSession, crew_id: str, pillar: Pillar, day: int) -> DataSource:
    if pillar == Pillar.behavioral:
        row = await repos.latest_keystroke_session(session, crew_id, day)
        return DataSource.simulated if row is None or row.session_id.startswith("sim-") else DataSource.device
    metric = CHART_METRIC[pillar]
    if metric == "exercise_sessions":
        src = await session.scalar(
            select(ExerciseSession.source)
            .where(ExerciseSession.crew_id == crew_id, ExerciseSession.mission_day <= day)
            .order_by(ExerciseSession.started_at.desc())
            .limit(1)
        )
    else:
        src = await session.scalar(
            select(Measurement.source)
            .where(Measurement.crew_id == crew_id, Measurement.metric_key == metric, Measurement.mission_day <= day)
            .order_by(Measurement.measured_at.desc())
            .limit(1)
        )
    return DataSource(src) if src in {s.value for s in DataSource} else DataSource.simulated


async def pillar_detail(
    session: AsyncSession, data: DataBundle, crew_id: str, pillar: Pillar, as_of_day: int | None
) -> PillarDetail:
    day = check_as_of(as_of_day)
    await _member(session, crew_id)
    body = _body(data, pillar)
    alerts = await _open_alerts(session, crew_id, day)
    summary = next(p for p in await _pillar_summaries(session, data, crew_id, day, alerts) if p.pillar == pillar)
    alert = _alert_for(alerts, pillar)
    source = await _source(session, crew_id, pillar, day)

    metrics = []
    chart = None
    for key, (label, unit) in METRICS[pillar].items():
        s = await series(session, data, crew_id, pillar, key, max(1, day - CHART_DAYS + 1), day, alerts=alerts)
        metrics.append(_metric_value(key, label, unit, s, source))
        if key == CHART_METRIC[pillar]:
            chart = s

    if pillar == Pillar.immune:
        typing = await _latest_typing(session, crew_id, day)
        stress = immune.stress_index(typing.fatigue_index if typing else None, day, None)
        metrics.append(
            MetricValue(
                key="stress_index",
                label="Stress index",
                value=stress,
                unit="/100",
                status=Status.ok if stress < 50 else Status.watch,
                source=DataSource.simulated,
            )
        )

    if alert is not None:
        explanation = alert.explanation
    elif pillar in PLACEHOLDER:
        explanation = (
            "Your values are shown against your personal in-flight baseline. The rules of this pillar are added later."
        )
    elif summary.status == Status.unknown:
        explanation = "Not enough data yet to know your personal normal."
    else:
        explanation = "Your values are within your personal in-flight range."

    return PillarDetail(
        pillar=pillar,
        name=body.name,
        body_zone=body.body_zone,
        function_text=body.function_text,
        hazard=body.hazard,
        hazard_text=body.hazard_text,
        status=summary.status,
        score=summary.score,
        explanation=explanation,
        metrics=metrics,
        chart=chart,
        plan_steps=[PlanStep(id=s.step_id, text=s.text, done=s.done, done_at=s.done_at) for s in alert.steps]
        if alert
        else [],
        active_alert_id=alert.id if alert else None,
        recheck_at=alert.recheck_at if alert else None,
        sources=body.sources,
        limits_text=body.limits_text,
        data_is_simulated=source == DataSource.simulated or pillar in PLACEHOLDER,
    )


# --------------------------------------------------------------------------- timeline


def _alert_days(a: AlertRow, last: int) -> dict[int, Status]:
    """The colour of one alert on each day it was open, from its history."""
    escalations = [clock.mission_day(h.at) for h in a.history if h.action == "escalated"]
    resolved = [clock.mission_day(h.at) for h in a.history if h.action == "resolved"]
    end = min(resolved[-1] if resolved else last, last)
    first_status = Status.watch if escalations else Status(a.status)
    out = {}
    for d in range(a.mission_day, end + 1):
        out[d] = Status.alert if any(e <= d for e in escalations) else first_status
    return out


async def timeline(
    session: AsyncSession, data: DataBundle, crew_id: str, from_day: int, to_day: int | None
) -> Timeline:
    await _member(session, crew_id)
    last = min(to_day or current_day(), current_day())
    first = min(from_day, last)
    stmt = select(AlertRow).where(AlertRow.crew_id == crew_id).options(selectinload(AlertRow.history))
    status = {d: {p: Status.ok for p in ORDER} for d in range(first, last + 1)}
    events: dict[int, list[str]] = {d: [] for d in status}
    for a in (await session.scalars(stmt)).all():
        try:
            pillar = Pillar(a.topic)
        except ValueError:
            pillar = None
        for d, s in _alert_days(a, last).items():
            if d in status and pillar is not None:
                status[d][pillar] = worst([status[d][pillar], s])
        if a.mission_day in events:
            events[a.mission_day].append(f"{TOPIC_LABEL.get(a.topic, a.topic)} alert")
        for h in a.history:
            d = clock.mission_day(h.at)
            if h.action == "escalated" and d in events and d != a.mission_day:
                events[d].append(f"{TOPIC_LABEL.get(a.topic, a.topic)} alert escalated")
    for e in data.scenario.events:
        label = SCENARIO_EVENT_LABELS.get(e.kind)
        if label:
            for d in range(e.days[0], e.days[1] + 1):
                if d in events:
                    events[d].append(label)
    days = [
        TimelineDay(
            day=d,
            date=clock.day_start(d),
            overall_status=worst(status[d].values()),
            pillars=status[d],
            events=events[d],
        )
        for d in range(first, last + 1)
    ]
    return Timeline(crew_id=crew_id, from_day=first, to_day=last, days=days)


# --------------------------------------------------------------------------- crew list (cmo)


async def crew_list(session: AsyncSession) -> list[CrewSummary]:
    crew = (await session.scalars(select(Crew).order_by(Crew.id))).all()
    alerts = (await session.scalars(select(AlertRow).where(AlertRow.state != "resolved"))).all()
    out = []
    for c in crew:
        mine = [a for a in alerts if a.crew_id == c.id]
        out.append(
            CrewSummary(
                member=CrewMember(
                    id=c.id, display_name=c.display_name, initials=c.initials, role_title=c.role_title, is_cmo=c.is_cmo
                ),
                overall_status=worst(a.status for a in mine) if mine else Status.ok,
                active_alerts=len(mine),
                highest_level=max(a.level for a in mine) if mine else None,
            )
        )
    return out
