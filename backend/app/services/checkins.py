from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..clock import clock
from ..datafiles import DataBundle
from ..db import repos
from ..db.models.alerts import Alert as AlertRow
from ..db.models.measurements import Checkin as CheckinRow
from ..engine import perception_gap
from ..engine.derived import CHECKIN_FROZEN_DAYS, MIN_SPREAD, SLEEP_SCORE_PENALTY_PER_HOUR
from ..engine.pillars import immune
from ..ids import next_id
from ..schemas import (
    Checkin,
    CheckinCreate,
    CheckinResult,
    CheckinSchema,
    FieldRejection,
    PerceptionGap,
    RejectionKind,
    Streak,
)
from ..security import validation
from . import alerts as alerts_service
from . import behavioral as behavioral_service
from . import pipeline
from .events import Event

VALUE_FIELDS = (
    "mood",
    "systolic_mmhg",
    "diastolic_mmhg",
    "pulse_bpm",
    "glucose_mg_dl",
    "temperature_c",
    "sleep_hours",
    "meals_eaten",
    "note",
)
METRIC_OF_FIELD = {"pulse_bpm": "resting_pulse_bpm"}
STREAK_LABEL = "Daily check-in"


def schema(data: DataBundle) -> CheckinSchema:
    return CheckinSchema(indicators=data.checkin.indicators)


def _limits(data: DataBundle) -> dict[str, tuple[float, float]]:
    return {
        i.key: (i.min, i.max)
        for i in data.checkin.indicators
        if i.input == "number" and i.min is not None and i.max is not None
    }


def to_schema(row: CheckinRow) -> Checkin:
    return Checkin(
        id=row.id,
        crew_id=row.crew_id,
        mission_day=row.mission_day,
        created_at=row.created_at,
        values=CheckinCreate(**{f: getattr(row, f) for f in VALUE_FIELDS}),
    )


async def _previous_values(session: AsyncSession, crew_id: str, day: int, field: str) -> list[float | None]:
    days = CHECKIN_FROZEN_DAYS - 1
    stmt = (
        select(CheckinRow.mission_day, getattr(CheckinRow, field))
        .where(
            CheckinRow.crew_id == crew_id,
            CheckinRow.mission_day.between(day - days, day - 1),
            CheckinRow.source == "manual",  # generated history repeats 0.1-step values by chance
        )
        .order_by(CheckinRow.mission_day)
    )
    found = dict((await session.execute(stmt)).all())
    return [found.get(d) for d in range(day - days, day)]


async def _validate(
    session: AsyncSession, data: DataBundle, crew_id: str, day: int, body: CheckinCreate
) -> tuple[CheckinCreate, list[FieldRejection]]:
    values = body.model_copy()
    rejected: list[FieldRejection] = []
    limits = _limits(data)
    for field, (lo, hi) in limits.items():
        value = getattr(body, field, None)
        if value is None:
            continue
        issue = validation.check(field, value, [], limits)
        if issue is not None:
            rejected.append(
                FieldRejection(
                    field=field,
                    value=value,
                    reason=RejectionKind.implausible,
                    message=f"{value:g} is outside the possible range ({lo:g}–{hi:g}). Measure again.",
                )
            )
        elif all(v == value for v in await _previous_values(session, crew_id, day, field)):
            rejected.append(
                FieldRejection(
                    field=field,
                    value=value,
                    reason=RejectionKind.frozen_sensor,
                    message=f"Exactly {value:g} for {CHECKIN_FROZEN_DAYS} days in a row: check the device and measure again.",
                )
            )
        else:
            continue
        setattr(values, field, None)
    return values, rejected


async def _save(
    session: AsyncSession, crew_id: str, day: int, values: CheckinCreate, rejected: list[FieldRejection]
) -> CheckinRow:
    row = await session.scalar(select(CheckinRow).where(CheckinRow.crew_id == crew_id, CheckinRow.mission_day == day))
    if row is None:
        row = CheckinRow(id=await next_id(session, "ck"), crew_id=crew_id, mission_day=day)
        session.add(row)
    row.created_at = clock.now()
    for f in VALUE_FIELDS:
        setattr(row, f, getattr(values, f))
    row.source = "manual"
    row.rejected = [r.model_dump(mode="json") for r in rejected]
    await session.flush()
    return row


async def streak(session: AsyncSession, crew_id: str, day: int) -> Streak:
    days = set((await session.scalars(select(CheckinRow.mission_day).where(CheckinRow.crew_id == crew_id))).all())
    current = 0
    while day - current in days:
        current += 1
    best = run = 0
    for d in range(1, day + 1):
        run = run + 1 if d in days else 0
        best = max(best, run)
    return Streak(key="checkin", label=STREAK_LABEL, days=current, best=best)


async def _sleep_score(
    session: AsyncSession, data: DataBundle, crew_id: str, day: int, sleep_hours: float | None
) -> tuple[float | None, float | None]:
    nights = await repos.series(session, crew_id, "sleep_hours", 1, day)
    if sleep_hours is None:
        today = next((p for p in nights if p.day == day), None)
        sleep_hours = today.value if today else None
    base = immune.baseline_before(
        nights,
        day,
        min_n=data.params.value("nightsignal_min_nights_baseline"),
        min_spread=MIN_SPREAD["sleep_hours"],
    )
    if sleep_hours is None or not base.ready:
        return None, None
    delta = sleep_hours - base.median
    return max(0.0, min(100.0, 100.0 - SLEEP_SCORE_PENALTY_PER_HOUR * max(-delta, 0.0))), delta


async def gap_for(
    session: AsyncSession, data: DataBundle, crew_id: str, day: int, mood: int | None, sleep_hours: float | None
) -> PerceptionGap:
    snapshot = await pipeline.immune_snapshot(session, crew_id, day, data)
    sleep, sleep_delta = await _sleep_score(session, data, crew_id, day, sleep_hours)
    typing, typing_text = await behavioral_service.typing_snapshot(session, data, crew_id, day)
    scores = {"night_pulse": snapshot.score.score, "sleep": sleep, "keystrokes": typing}
    # TODO T20: add the "pvt" score
    details = {}
    if typing_text is not None:
        details["keystrokes"] = typing_text
    if snapshot.night_delta_bpm is not None:
        details["night_pulse"] = f"Night pulse: {snapshot.night_delta_bpm:+.1f} bpm"
    if sleep_delta is not None:
        details["sleep"] = f"Sleep: {sleep_delta:+.1f} h"
    self_score, objective, gap, status, explanation, signals = perception_gap.compute(mood, scores, details)
    return PerceptionGap(
        self_reported_mood=mood,
        self_score=self_score,
        objective_score=objective,
        gap=gap,
        status=status,
        explanation=explanation,
        contributing_signals=signals,
    )


def _changed_metrics(values: CheckinCreate) -> set[str]:
    return {
        METRIC_OF_FIELD.get(f, f)
        for f in ("systolic_mmhg", "diastolic_mmhg", "pulse_bpm", "glucose_mg_dl", "temperature_c", "sleep_hours")
        if getattr(values, f) is not None
    }


async def create(
    session: AsyncSession, data: DataBundle, crew_id: str, body: CheckinCreate
) -> tuple[CheckinResult, list[Event]]:
    day = clock.mission_day()
    values, rejected = await _validate(session, data, crew_id, day, body)
    row = await _save(session, crew_id, day, values, rejected)
    result = await pipeline.process(session, crew_id, _changed_metrics(values), day=day, data=data, reason="checkin")
    created = []
    if result.alerts_created:
        stmt = select(AlertRow).where(AlertRow.id.in_(result.alerts_created))
        created = [alerts_service.brief(a) for a in (await session.scalars(stmt)).all()]
    gap = await gap_for(session, data, crew_id, day, values.mood, values.sleep_hours)
    current = await streak(session, crew_id, day)
    await session.commit()
    noun = "day" if current.days == 1 else "days"
    return (
        CheckinResult(
            checkin=to_schema(row),
            rejected=rejected,
            perception_gap=gap,
            alerts_created=created,
            streak=current,
            message=f"Check-in saved. {current.days} {noun} in a row.",
        ),
        result.events,
    )


async def history(session: AsyncSession, crew_id: str, from_day: int, to_day: int) -> list[Checkin]:
    stmt = (
        select(CheckinRow)
        .where(CheckinRow.crew_id == crew_id, CheckinRow.mission_day.between(from_day, to_day))
        .order_by(CheckinRow.mission_day.desc())
    )
    return [to_schema(r) for r in (await session.scalars(stmt)).all()]


async def today(session: AsyncSession, crew_id: str) -> Checkin | None:
    stmt = select(CheckinRow).where(CheckinRow.crew_id == crew_id, CheckinRow.mission_day == clock.mission_day())
    row = await session.scalar(stmt)
    return to_schema(row) if row else None
