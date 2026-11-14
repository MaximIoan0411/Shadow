from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..clock import clock
from ..datafiles import DataBundle
from ..db import repos
from ..db.models.measurements import KeystrokeSession
from ..db.models.measurements import PvtResult as PvtRow
from ..deps import ApiError
from ..engine.derived import KEYSTROKE_MIN_KEYS
from ..engine.pillars import behavioral
from ..ids import next_id
from ..schemas import (
    KeystrokeBatch,
    KeystrokeFeatures,
    KeystrokeResult,
    KeystrokeSessionPoint,
    KeystrokeSummary,
    PvtResult,
    PvtSubmit,
)
from . import pipeline
from .events import Event

SESSION_ID_MAX = 64
NOTIFY = ("watch", "alert")


def _features(values: dict, n_keys: int) -> KeystrokeFeatures:
    return KeystrokeFeatures(
        hold_ms_mean=round(values["hold_ms_mean"], 1),
        hold_ms_sd=round(values["hold_ms_sd"], 1),
        flight_ms_mean=round(values["flight_ms_mean"], 1),
        flight_ms_sd=round(values["flight_ms_sd"], 1),
        backspace_rate=round(values["backspace_rate"], 3),
        keys_per_min=round(values["keys_per_min"], 1),
        n_keys=n_keys,
    )


def _baseline_features(base: dict) -> KeystrokeFeatures | None:
    return _features(base["mean"], base["n_keys"]) if base["ready"] else None


async def _session_row(session: AsyncSession, crew_id: str, body: KeystrokeBatch, base: dict) -> KeystrokeSession:
    if len(body.session_id) > SESSION_ID_MAX:
        raise ApiError(
            422,
            "validation_error",
            "The submitted data does not match the contract.",
            {"fields": [{"field": "session_id", "problem": f"at most {SESSION_ID_MAX} characters"}]},
        )
    row = await session.get(KeystrokeSession, body.session_id)
    if row is None:
        now = clock.now()
        row = KeystrokeSession(
            session_id=body.session_id,
            crew_id=crew_id,
            context=body.context,
            started_at=now,
            updated_at=now,
            mission_day=clock.mission_day(),
            status="unknown",
            is_baseline=not base["ready"],
        )
        session.add(row)
    elif row.crew_id != crew_id:
        raise ApiError(403, "forbidden", "This typing session belongs to another account.")
    return row


async def add_batch(
    session: AsyncSession, data: DataBundle, crew_id: str, body: KeystrokeBatch
) -> tuple[KeystrokeResult, list[Event]]:
    base = await pipeline.typing_baseline(session, crew_id, data)
    row = await _session_row(session, crew_id, body, base)

    acc = {k: getattr(row, k) for k in (*behavioral.ACCUMULATORS, "last_down_ms")}
    events_in = [behavioral.KeyEventIn(e.t_down_ms, e.t_up_ms, e.key_class) for e in body.events]
    for key, value in behavioral.accumulate(acc, events_in).items():
        setattr(row, key, value)
    row.updated_at = clock.now()

    features = behavioral.features_of(row)
    fatigue, deviation_z = None, {}
    if base["ready"] and not row.is_baseline:
        index, deviation_z = behavioral.fatigue_index(features, base)
        if row.n_keys >= KEYSTROKE_MIN_KEYS:
            fatigue = index
    previous_status = row.status
    row.fatigue_index = fatigue
    row.status = behavioral.status_for(fatigue)
    await session.flush()

    events: list[Event] = []
    if row.status in NOTIFY and row.status != previous_status:
        result = await pipeline.process(
            session, crew_id, {"keys_per_min"}, day=row.mission_day, data=data, reason="keystrokes"
        )
        events = result.events
    await session.commit()

    return (
        KeystrokeResult(
            session_id=row.session_id,
            features=_features(features, row.n_keys),
            baseline=_baseline_features(base),
            deviation_z=deviation_z,
            fatigue_index=fatigue,
            status=row.status,
            baseline_ready=base["ready"],
            baseline_sessions=base["sessions"],
        ),
        events,
    )


async def summary(session: AsyncSession, data: DataBundle, crew_id: str, last: int) -> KeystrokeSummary:
    base = await pipeline.typing_baseline(session, crew_id, data)
    day = clock.mission_day()
    current = await repos.latest_keystroke_session(session, crew_id, day)
    recent = (await repos.keystroke_sessions(session, crew_id, 1, day))[-last:]
    return KeystrokeSummary(
        baseline=_baseline_features(base),
        current=_features(behavioral.features_of(current), current.n_keys) if current else None,
        fatigue_index=current.fatigue_index if current else None,
        status=current.status if current else "unknown",
        baseline_ready=base["ready"],
        sessions=[
            KeystrokeSessionPoint(
                session_id=r.session_id,
                at=r.started_at,
                keys_per_min=round(r.keys_per_min, 1),
                hold_ms_mean=round(r.hold_ms_mean, 1),
                fatigue_index=r.fatigue_index,
                status=r.status,
            )
            for r in recent
        ],
    )


async def typing_snapshot(
    session: AsyncSession, data: DataBundle, crew_id: str, day: int
) -> tuple[float | None, str | None]:
    """(typing score 0..100, short text) from the latest judged session of today or yesterday, for the perception gap."""
    row = await repos.latest_keystroke_session(session, crew_id, day, from_day=day - 1, judged_only=True)
    if row is None:
        return None, None
    base = await pipeline.typing_baseline(session, crew_id, data)
    usual = base["mean"]["keys_per_min"]
    speed_pct = (row.keys_per_min - usual) / usual * 100 if usual else 0.0
    return behavioral.score(row.fatigue_index, None).score, f"Typing: {speed_pct:+.0f}% speed"


def pvt_to_schema(row: PvtRow) -> PvtResult:
    return PvtResult(
        id=row.id,
        crew_id=row.crew_id,
        at=row.at,
        n_trials=row.n_trials,
        mean_rt_ms=row.mean_rt_ms,
        mean_speed=row.mean_speed,
        lapses=row.lapses,
        false_starts=row.false_starts,
        baseline_speed=row.baseline_speed,
        deviation_sd=row.deviation_sd,
        status=row.status,
    )


async def _pvt_rows(session: AsyncSession, crew_id: str) -> list[PvtRow]:
    stmt = select(PvtRow).where(PvtRow.crew_id == crew_id).order_by(PvtRow.at, PvtRow.id)
    return list((await session.scalars(stmt)).all())


async def add_pvt(
    session: AsyncSession, data: DataBundle, crew_id: str, body: PvtSubmit
) -> tuple[PvtResult, list[Event]]:
    v = data.params.value
    practice_runs = int(v("pvt_practice_runs")[-1])
    summary = behavioral.pvt_summary([t.model_dump() for t in body.trials], lapse_ms=v("pvtb_lapse_threshold"))
    previous = await _pvt_rows(session, crew_id)
    is_practice = len(previous) < practice_runs
    base = behavioral.pvt_baseline([r.mean_speed for r in previous if not r.is_practice and r.mean_speed > 0])

    day = clock.mission_day()
    deviation, status, finding = None, "unknown", None
    if not is_practice and base is not None and summary["mean_speed"] > 0:
        base_speed, base_sd = base
        deviation = round((summary["mean_speed"] - base_speed) / base_sd, 2)
        finding = behavioral.pvt_finding(
            crew_id,
            summary["mean_speed"],
            base_speed,
            base_sd,
            reliable_change_sd=v("pvt_reliable_change_derived"),
            day=day,
        )
        status = finding.status if finding else "ok"

    row = PvtRow(
        id=await next_id(session, "pvt"),
        crew_id=crew_id,
        at=clock.now(),
        mission_day=day,
        is_practice=is_practice,
        baseline_speed=round(base[0], 3) if base and not is_practice else None,
        deviation_sd=deviation,
        status=status,
        **summary,
    )
    session.add(row)
    await session.flush()

    result = await pipeline.process(
        session,
        crew_id,
        {"pvt_mean_speed"},
        day=day,
        data=data,
        reason="pvt",
        extra_findings=[finding] if finding else None,
    )
    await session.commit()
    return pvt_to_schema(row), result.events


async def pvt_history(session: AsyncSession, crew_id: str, limit: int) -> list[PvtResult]:
    rows = await _pvt_rows(session, crew_id)
    return [pvt_to_schema(r) for r in reversed(rows[-limit:])]


async def pvt_snapshot(session: AsyncSession, crew_id: str, day: int) -> tuple[float | None, float | None, str | None]:
    """(score 0..100, deviation in SD, short text) from the latest judged test of today or yesterday."""
    stmt = (
        select(PvtRow)
        .where(PvtRow.crew_id == crew_id, PvtRow.mission_day.between(day - 1, day), PvtRow.deviation_sd.is_not(None))
        .order_by(PvtRow.at.desc())
        .limit(1)
    )
    row = await session.scalar(stmt)
    if row is None:
        return None, None, None
    pct = (row.mean_speed - row.baseline_speed) / row.baseline_speed * 100 if row.baseline_speed else 0.0
    return behavioral.score(None, row.deviation_sd).score, row.deviation_sd, f"Reaction speed: {pct:+.0f}%"


async def pvt_count(session: AsyncSession, crew_id: str) -> int:
    return await session.scalar(select(func.count()).select_from(PvtRow).where(PvtRow.crew_id == crew_id)) or 0
