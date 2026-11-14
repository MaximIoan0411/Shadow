import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..datafiles import DataBundle
from ..ids import next_ids
from ..security import passwords
from ..simulator import scenario
from .models.measurements import Checkin, ExerciseSession, KeystrokeSession, Measurement
from .models.users import Crew, User

SIMULATED = "simulated"

ROLE_TITLES = {
    "cm-1": "Commander",
    "cm-2": "Mission Specialist",
    "cm-3": "Crew Medical Officer",
    "cm-4": "Flight Engineer",
}


def _read_users(path: str) -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))["users"]


async def seed_crew_and_users(session: AsyncSession, users_json_path: str) -> None:
    if await session.scalar(select(func.count()).select_from(User)):
        return
    accounts = await asyncio.to_thread(_read_users, users_json_path)

    for u in accounts:
        if u["crew_id"] is None:
            continue
        session.add(
            Crew(
                id=u["crew_id"],
                display_name=u["display_name"],
                initials=u["initials"],
                role_title=ROLE_TITLES.get(u["crew_id"], u["display_name"]),
                is_cmo=u["role"] == "cmo",
            )
        )
    await session.flush()

    hashes = await asyncio.gather(*(asyncio.to_thread(passwords.hash, u["test_password"]) for u in accounts))
    for u, password_hash in zip(accounts, hashes, strict=True):
        session.add(
            User(
                id=u["id"],
                username=u["username"],
                password_hash=password_hash,
                display_name=u["display_name"],
                initials=u["initials"],
                role=u["role"],
                crew_id=u["crew_id"],
            )
        )
    await session.flush()


def _keystroke_row(crew_id: str, day: int, k: dict, *, is_baseline: bool) -> KeystrokeSession:
    n = k["n_keys"]
    flights = n - 1
    active_ms = n / k["keys_per_min"] * 60000
    return KeystrokeSession(
        session_id=f"sim-{crew_id}-d{day:03d}",
        crew_id=crew_id,
        context=k["context"],
        started_at=k["started_at"],
        updated_at=k["started_at"] + timedelta(milliseconds=active_ms),
        mission_day=day,
        n_keys=n,
        hold_sum=k["hold_ms_mean"] * n,
        hold_sumsq=(k["hold_ms_sd"] ** 2 + k["hold_ms_mean"] ** 2) * n,
        flight_n=flights,
        flight_sum=k["flight_ms_mean"] * flights,
        flight_sumsq=(k["flight_ms_sd"] ** 2 + k["flight_ms_mean"] ** 2) * flights,
        backspaces=round(k["backspace_rate"] * n),
        active_ms=active_ms,
        hold_ms_mean=k["hold_ms_mean"],
        hold_ms_sd=k["hold_ms_sd"],
        flight_ms_mean=k["flight_ms_mean"],
        flight_ms_sd=k["flight_ms_sd"],
        backspace_rate=k["backspace_rate"],
        keys_per_min=k["keys_per_min"],
        status="unknown",
        is_baseline=is_baseline,
    )


async def seed_history(
    session: AsyncSession, data: DataBundle, until_day: int, *, not_after: datetime | None = None
) -> None:
    if await session.scalar(select(func.count()).select_from(Checkin)):
        return
    days = await asyncio.to_thread(scenario.generate, data.scenario, from_day=1, to_day=until_day)
    baseline_days = int(data.params.value("keystroke_baseline_duration"))

    def due(at: datetime) -> bool:
        return not_after is None or at <= not_after

    # the check-in of the start day is done live by the astronaut, so the history stops the day before
    checkins = [d for d in days if d.checkin and d.day < until_day and due(d.checkin["created_at"])]
    sessions = [(d, s) for d in days for s in d.exercise if due(s["started_at"])]
    ck_ids = await next_ids(session, "ck", len(checkins))
    ex_ids = await next_ids(session, "ex", len(sessions))

    measurements = [
        {
            "crew_id": d.crew_id,
            "metric_key": key,
            "value": value,
            "unit": unit,
            "measured_at": at,
            "mission_day": d.day,
            "source": SIMULATED,
        }
        for d in days
        for key, value, unit, at in d.measurements
        if due(at)
    ]
    if measurements:
        await session.execute(insert(Measurement), measurements)

    rows: list = []
    for d in days:
        if d.keystroke and due(d.keystroke["started_at"]):
            rows.append(_keystroke_row(d.crew_id, d.day, d.keystroke, is_baseline=d.day <= baseline_days))
    for ck_id, d in zip(ck_ids, checkins, strict=True):
        c = d.checkin
        rows.append(
            Checkin(
                id=ck_id,
                crew_id=d.crew_id,
                mission_day=d.day,
                created_at=c["created_at"],
                mood=c["mood"],
                systolic_mmhg=c["systolic_mmhg"],
                diastolic_mmhg=c["diastolic_mmhg"],
                pulse_bpm=c["pulse_bpm"],
                glucose_mg_dl=c["glucose_mg_dl"],
                temperature_c=c["temperature_c"],
                sleep_hours=c["sleep_hours"],
                meals_eaten=c["meals_eaten"],
                note=c["note"],
                source=SIMULATED,
                rejected=[],
            )
        )
    for ex_id, (d, s) in zip(ex_ids, sessions, strict=True):
        rows.append(
            ExerciseSession(
                id=ex_id,
                crew_id=d.crew_id,
                mission_day=d.day,
                kind=s["kind"],
                started_at=s["started_at"],
                duration_min=s["duration_min"],
                sets=s["sets"],
                loading_score=0.0,
                source=SIMULATED,
            )
        )
    session.add_all(rows)
    await session.flush()
