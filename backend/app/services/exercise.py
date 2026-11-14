from datetime import datetime, timedelta

from sqlalchemy import delete, func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..clock import clock
from ..datafiles import DataBundle
from ..db.models.measurements import ExerciseSession as SessionRow
from ..db.models.measurements import Measurement
from ..engine.derived import LOADING_ADHERENCE_DAYS, LOADING_TARGET
from ..engine.pillars import musculoskeletal as loading
from ..ids import next_id
from ..schemas import BoneProjection, ExerciseSession, ExerciseSessionCreate, ExerciseToday, Streak
from . import pipeline
from .events import Event

METRIC = "loading_score"
PLANNED_SESSIONS = 2
STREAK_LABEL = "Training in two sessions"


def to_schema(r: SessionRow) -> ExerciseSession:
    return ExerciseSession(
        id=r.id,
        crew_id=r.crew_id,
        mission_day=r.mission_day,
        kind=r.kind,
        started_at=r.started_at,
        duration_min=r.duration_min,
        sets=r.sets,
        loading_score=r.loading_score,
        source=r.source,
    )


def _hour(at: datetime, day: int) -> float:
    return (at - clock.day_start(day)).total_seconds() / 3600


def _daily(rows: list[SessionRow], day: int) -> float:
    return loading.daily_loading([(_hour(r.started_at, day), r.loading_score) for r in rows])


async def _rows(session: AsyncSession, crew_id: str, first: int, last: int) -> list[SessionRow]:
    stmt = (
        select(SessionRow)
        .where(SessionRow.crew_id == crew_id, SessionRow.mission_day.between(first, last))
        .order_by(SessionRow.started_at)
    )
    return list((await session.scalars(stmt)).all())


async def backfill(session: AsyncSession, until_day: int) -> None:
    """At startup: the loading score of the simulated sessions and the daily loading of every past day (for the chart
    and the timeline)."""
    if await session.scalar(select(Measurement.id).where(Measurement.metric_key == METRIC).limit(1)) is not None:
        return
    await score_days(session, 1, until_day - 1)


async def score_days(session: AsyncSession, first: int, last: int) -> None:
    """The loading score of the simulated sessions of days [first, last] and the daily loading of those days."""
    stmt = select(SessionRow).where(SessionRow.mission_day.between(first, last)).order_by(SessionRow.started_at)
    rows = list((await session.scalars(stmt)).all())
    by_crew_day: dict[tuple[str, int], list[SessionRow]] = {}
    for r in rows:
        if r.source != "manual":
            r.loading_score = loading.session_score(r.sets)
        by_crew_day.setdefault((r.crew_id, r.mission_day), []).append(r)
    crew_ids = set((await session.scalars(select(SessionRow.crew_id).distinct())).all())
    await session.execute(
        delete(Measurement).where(Measurement.metric_key == METRIC, Measurement.mission_day.between(first, last))
    )
    measurements = [
        {
            "crew_id": crew_id,
            "metric_key": METRIC,
            "value": _daily(by_crew_day.get((crew_id, day), []), day),
            "unit": "/80",
            "measured_at": clock.day_start(day) + timedelta(hours=23, minutes=59),
            "mission_day": day,
            "source": "simulated",
        }
        for crew_id in sorted(crew_ids)
        for day in range(first, last + 1)
    ]
    if measurements:
        await session.execute(insert(Measurement), measurements)
    await session.flush()


async def _save_daily(session: AsyncSession, crew_id: str, day: int) -> float:
    value = _daily(await _rows(session, crew_id, day, day), day)
    await session.execute(
        delete(Measurement).where(
            Measurement.crew_id == crew_id, Measurement.metric_key == METRIC, Measurement.mission_day == day
        )
    )
    session.add(
        Measurement(
            crew_id=crew_id,
            metric_key=METRIC,
            value=value,
            unit="/80",
            measured_at=clock.now(),
            mission_day=day,
            source="manual",
        )
    )
    return value


async def split_streak(session: AsyncSession, crew_id: str, day: int) -> Streak:
    stmt = (
        select(SessionRow.mission_day, func.count())
        .where(SessionRow.crew_id == crew_id, SessionRow.mission_day <= day)
        .group_by(SessionRow.mission_day)
    )
    split_days = {d for d, n in (await session.execute(stmt)).all() if n >= PLANNED_SESSIONS}
    start = day if day in split_days else day - 1
    current = 0
    while start - current in split_days:
        current += 1
    best = run = 0
    for d in range(1, day + 1):
        run = run + 1 if d in split_days else 0
        best = max(best, run)
    return Streak(key="split_training", label=STREAK_LABEL, days=current, best=best)


async def _projection(session: AsyncSession, data: DataBundle, crew_id: str, day: int) -> BoneProjection:
    first = max(1, day - LOADING_ADHERENCE_DAYS)
    rows = await _rows(session, crew_id, first, day - 1)
    days = max(day - first, 1)
    adherence = len(rows) / (days * PLANNED_SESSIONS)
    per_day: dict[int, int] = {}
    for r in rows:
        per_day[r.mission_day] = per_day.get(r.mission_day, 0) + 1
    split = sum(1 for n in per_day.values() if n >= PLANNED_SESSIONS) >= days / 2
    current, with_split = loading.projection(adherence, split, data.params.value("projected_bmd_loss_model"))
    return BoneProjection(current_plan_pct_month=current, split_plan_pct_month=with_split, note=loading.PROJECTION_NOTE)


def _recommendation(completed: int) -> str:
    if completed == 0:
        return "Plan two sessions today, a few hours apart: it helps your bones more than one long session."
    if completed == 1:
        return "Do a second session today, at least 4 hours after the first one."
    return "Two sessions done today, well spread out. Well done."


async def today(session: AsyncSession, data: DataBundle, crew_id: str) -> ExerciseToday:
    day = clock.mission_day()
    rows = await _rows(session, crew_id, day, day)
    return ExerciseToday(
        mission_day=day,
        planned_sessions=PLANNED_SESSIONS,
        completed_sessions=len(rows),
        loading_score=_daily(rows, day),
        loading_target=LOADING_TARGET,
        split_recommended=loading.split_recommended(len(rows)),
        recommendation_text=_recommendation(len(rows)),
        streak=await split_streak(session, crew_id, day),
        sessions=[to_schema(r) for r in rows],
        projection=await _projection(session, data, crew_id, day),
    )


async def create(
    session: AsyncSession, data: DataBundle, crew_id: str, body: ExerciseSessionCreate
) -> tuple[ExerciseSession, list[Event]]:
    day = min(max(clock.mission_day(body.started_at), 1), clock.mission_day())
    row = SessionRow(
        id=await next_id(session, "ex"),
        crew_id=crew_id,
        mission_day=day,
        kind=body.kind,
        started_at=body.started_at,
        duration_min=body.duration_min,
        sets=[s.model_dump() for s in body.sets],
        loading_score=loading.session_score([s.model_dump() for s in body.sets]),
        source="manual",
    )
    session.add(row)
    await session.flush()
    await _save_daily(session, crew_id, day)
    result = await pipeline.process(session, crew_id, {METRIC}, day=day, data=data, reason="exercise")
    await session.commit()
    return to_schema(row), result.events


async def history(session: AsyncSession, crew_id: str, from_day: int, to_day: int) -> list[ExerciseSession]:
    return [to_schema(r) for r in reversed(await _rows(session, crew_id, from_day, to_day))]


async def yesterday_score(session: AsyncSession, crew_id: str, day: int):
    """The pillar score from the last full day (today is still in progress)."""
    rows = await _rows(session, crew_id, day - 1, day - 1)
    return loading.score(_daily(rows, day - 1), LOADING_TARGET) if day > 1 else loading.score(0, LOADING_TARGET)
