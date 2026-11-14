import asyncio
import logging

from ..datafiles import DataBundle
from ..db import session as db
from ..services import radiation
from ..services.events import publish_all

log = logging.getLogger(__name__)

STEP_S = 2.0


async def live_simulator(data: DataBundle) -> None:
    """Background task, one step every 2 real seconds, with its own session: while a solar storm runs, the dosimeter
    readings, the on-board alert and the DONKI warning from Earth (services/radiation.live_step). The day jump (T33)
    is added here later. An error is logged and the loop goes on."""
    while True:
        try:
            async with db.SessionLocal() as s:
                events = await radiation.live_step(s, data)
                await s.commit()
            publish_all(events)
        except Exception:
            log.exception("live simulator step failed; continuing")
        await asyncio.sleep(STEP_S)
