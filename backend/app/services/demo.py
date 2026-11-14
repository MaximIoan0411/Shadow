import time
from datetime import timedelta

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from ..clock import clock
from ..datafiles import DataBundle
from ..db import session as db
from ..db.seed import write_days
from ..link import queue
from ..schemas import MeasurementIngest, Packet, Rejection, User
from ..security import lockout, sealing, validation
from ..security.keys import Keys
from ..simulator.devices import signed_measurement
from . import access, pipeline, security_log
from . import exercise as exercise_service
from . import mission as mission_service
from .events import Event
from .link import to_packet

FROZEN_DEVICE = ("wearable-cm-4", "cm-4", "temperature_c", 36.6, "°C")
SPOOF_SENDER = "Unknown sender"


async def reset(app: FastAPI) -> tuple[float, list[Event]]:
    """Everything back to the start: background tasks stopped, tables emptied, the same scenario loaded again
    (same seed → same data), clock on day 96 at 07:00, account lockouts cleared, tasks started again."""
    started = time.perf_counter()
    await app.state.stop_tasks(app)
    await app.state.wipe(app)
    await app.state.bootstrap(app)
    app.state.start_tasks(app)
    lockout.reset_all()
    return round(time.perf_counter() - started, 2), [
        Event("mission.tick", mission_service.tick_data()),
        Event("dashboard.changed", {"reason": "reset"}),
    ]


async def log_reset(user: User) -> None:
    """The access log survives a reset; the reset itself is written to it, with who asked for it."""
    async with db.SessionLocal() as s:
        await access.record(s, user, action="reset", resource="sim/reset", crew_id=None, outcome="allowed")
        await s.commit()


async def jump_to_day(session: AsyncSession, data: DataBundle, day: int) -> None:
    """Forward only: the simulated data between now and day `day` at 07:00 are generated and written, the engine
    runs over those days (the same day-by-day replay as at startup), then the clock jumps."""
    current, now = clock.mission_day(), clock.now()
    target = clock.day_start(day) + timedelta(
        hours=int(data.scenario.start_time[:2]), minutes=int(data.scenario.start_time[3:])
    )
    await write_days(session, data, current, day, after=now, not_after=target)
    await exercise_service.score_days(session, current, day - 1)
    await pipeline.replay_days(session, data, current, day)
    clock.jump_to_day(day, data.scenario.start_time)


async def inject_spoof(session: AsyncSession) -> Packet:
    """A ship → Earth packet sealed with the wrong key. The scheduler rejects it on arrival (`bad_signature`)."""
    payload = {"crew_id": "cm-2", "week": 14, "summary": "Forged content: all values normal, no alerts."}
    packet = await queue.enqueue(
        session,
        direction="down",
        kind="weekly_summary",
        title="Weekly summary · week 14",
        sender=SPOOF_SENDER,
        payload=payload,
    )
    packet.sealed = sealing.seal(payload, packet.header, sender="attacker")
    packet.size_bytes = len(packet.sealed)
    await session.commit()
    return to_packet(packet)


async def frozen_sensor(session: AsyncSession, data: DataBundle, keys: Keys) -> tuple[Rejection, list[Event]]:
    """A device sends the exact same value FROZEN_REPEATS times; the validation layer rejects the last one."""
    device_id, crew_id, metric, value, unit = FROZEN_DEVICE
    now = clock.now()
    events: list[Event] = []
    for i in range(validation.FROZEN_REPEATS):
        at = now - timedelta(minutes=validation.FROZEN_REPEATS - i)
        signed = signed_measurement(
            device_id, crew_id, metric, value, unit, at.isoformat(), keys.device_private[device_id]
        )
        result, step_events = await security_log.ingest(session, data, keys, MeasurementIngest(**signed), signed)
        events += step_events
        if result.rejection is not None:
            return result.rejection, events
    raise RuntimeError("the frozen sensor was not detected")  # validation.FROZEN_REPEATS guarantees it is
