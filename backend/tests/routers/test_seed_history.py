import time

from asgi_lifespan import LifespanManager
from sqlalchemy import func, select

from app.clock import clock
from app.db import session as db
from app.db.models.measurements import Checkin, ExerciseSession, KeystrokeSession, Measurement
from app.db.models.sim import SimState


async def scalar(stmt):
    async with db.SessionLocal() as s:
        return await s.scalar(stmt)


async def test_cm2_has_96_checkins_and_night_pulse_every_day(client):
    n = await scalar(select(func.count()).select_from(Checkin).where(Checkin.crew_id == "cm-2"))
    assert n == 96
    async with db.SessionLocal() as s:
        days = (
            await s.scalars(
                select(Measurement.mission_day).where(
                    Measurement.crew_id == "cm-2", Measurement.metric_key == "night_pulse_bpm"
                )
            )
        ).all()
    assert sorted(days) == list(range(1, 97))


async def test_everything_is_marked_simulated(client):
    async with db.SessionLocal() as s:
        sources = set((await s.scalars(select(Measurement.source).distinct())).all())
        sources |= set((await s.scalars(select(Checkin.source).distinct())).all())
        sources |= set((await s.scalars(select(ExerciseSession.source).distinct())).all())
    assert sources == {"simulated"}


async def test_ids_and_counters(client):
    async with db.SessionLocal() as s:
        first = await s.get(Checkin, "ck-0001")
        n_ck = await s.scalar(select(func.count()).select_from(Checkin))
        n_ex = await s.scalar(select(func.count()).select_from(ExerciseSession))
        assert (await s.get(SimState, "id:ck")).value == {"n": n_ck}
        assert (await s.get(SimState, "id:ex")).value == {"n": n_ex}
    assert first is not None and first.mission_day == 1
    assert n_ck == 96 * 4


async def test_nothing_after_mission_start(client):
    now = clock.now()
    assert await scalar(select(func.count()).select_from(Measurement).where(Measurement.measured_at > now)) == 0
    assert await scalar(select(func.count()).select_from(ExerciseSession).where(ExerciseSession.started_at > now)) == 0
    day96 = await scalar(select(func.count()).select_from(ExerciseSession).where(ExerciseSession.mission_day == 96))
    assert day96 == 0


async def test_skipped_exercise_and_keystroke_baseline(client):
    day61 = await scalar(
        select(func.count())
        .select_from(ExerciseSession)
        .where(ExerciseSession.crew_id == "cm-2", ExerciseSession.mission_day == 61)
    )
    assert day61 == 0
    async with db.SessionLocal() as s:
        rows = (await s.scalars(select(KeystrokeSession).where(KeystrokeSession.crew_id == "cm-2"))).all()
    assert {r.mission_day for r in rows if r.is_baseline} == set(range(1, 8))
    day1 = next(r for r in rows if r.mission_day == 1)
    assert abs(day1.hold_sum / day1.n_keys - day1.hold_ms_mean) < 1e-6


async def test_startup_is_fast(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 'speed.sqlite'}")
    from app.main import create_app

    started = time.perf_counter()
    async with LifespanManager(create_app(), startup_timeout=30):
        elapsed = time.perf_counter() - started
    assert elapsed < 10
