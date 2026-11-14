from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..engine.types import Point
from .models.measurements import Checkin, Measurement

CHECKIN_METRICS = {
    "mood": Checkin.mood,
    "systolic_mmhg": Checkin.systolic_mmhg,
    "diastolic_mmhg": Checkin.diastolic_mmhg,
    "resting_pulse_bpm": Checkin.pulse_bpm,
    "glucose_mg_dl": Checkin.glucose_mg_dl,
    "temperature_c": Checkin.temperature_c,
    "sleep_hours": Checkin.sleep_hours,
}


async def _by_crew_and_day(
    session: AsyncSession, crew_id: str | None, metric_key: str, from_day: int, to_day: int
) -> dict[str, dict[int, Point]]:
    out: dict[str, dict[int, Point]] = {}

    stmt = (
        select(Measurement.crew_id, Measurement.mission_day, Measurement.measured_at, Measurement.value)
        .where(Measurement.metric_key == metric_key, Measurement.mission_day.between(from_day, to_day))
        .order_by(Measurement.mission_day, Measurement.measured_at, Measurement.id)
    )
    if crew_id is not None:
        stmt = stmt.where(Measurement.crew_id == crew_id)
    for crew, day, at, value in (await session.execute(stmt)).all():
        out.setdefault(crew, {})[day] = Point(day=day, t=at, value=float(value))

    column = CHECKIN_METRICS.get(metric_key)
    if column is not None:
        stmt = select(Checkin.crew_id, Checkin.mission_day, Checkin.created_at, column).where(
            Checkin.mission_day.between(from_day, to_day), column.is_not(None)
        )
        if crew_id is not None:
            stmt = stmt.where(Checkin.crew_id == crew_id)
        for crew, day, at, value in (await session.execute(stmt)).all():
            out.setdefault(crew, {}).setdefault(day, Point(day=day, t=at, value=float(value)))

    return out


def _sorted(points_by_day: dict[int, Point]) -> list[Point]:
    return [points_by_day[d] for d in sorted(points_by_day)]


async def series(session: AsyncSession, crew_id: str, metric_key: str, from_day: int, to_day: int) -> list[Point]:
    found = await _by_crew_and_day(session, crew_id, metric_key, from_day, to_day)
    return _sorted(found.get(crew_id, {}))


async def series_all_crew(session: AsyncSession, metric_key: str, from_day: int, to_day: int) -> dict[str, list[Point]]:
    found = await _by_crew_and_day(session, None, metric_key, from_day, to_day)
    return {crew: _sorted(days) for crew, days in sorted(found.items())}


async def latest(session: AsyncSession, crew_id: str, metric_key: str, up_to_day: int) -> Point | None:
    points = await series(session, crew_id, metric_key, 1, up_to_day)
    return points[-1] if points else None


async def recent_device_values(session: AsyncSession, device_id: str, metric_key: str, n: int) -> list[float]:
    stmt = (
        select(Measurement.value)
        .where(Measurement.device_id == device_id, Measurement.metric_key == metric_key)
        .order_by(Measurement.measured_at.desc(), Measurement.id.desc())
        .limit(n)
    )
    values = (await session.scalars(stmt)).all()
    return [float(v) for v in reversed(values)]
