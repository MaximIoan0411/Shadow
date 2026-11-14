import asyncio
import logging
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..clock import clock
from ..datafiles import DataBundle
from ..db import session as db
from ..db.models.alerts import Alert, AlertHistory
from ..db.models.link import Packet
from ..security import sealing
from ..security.errors import SealError
from ..services import alerts as alerts_service
from ..services import mission as mission_service
from ..services import radiation as radiation_service
from ..services import security_log
from ..services.events import Event, publish_all
from ..services.link import to_packet
from . import windows

log = logging.getLogger(__name__)

STEP_S = 1.0


def _event(kind: str, p: Packet) -> Event:
    return Event(kind, to_packet(p).model_dump(mode="json"), p.crew_id)


async def _deliver_reply(session: AsyncSession, p: Packet, events: list[Event]) -> None:
    alert_id = (p.payload or {}).get("alert_id") or p.alert_id
    if not alert_id:
        return
    stmt = select(Alert).where(Alert.id == alert_id).options(selectinload(Alert.history))
    alert = await session.scalar(stmt)
    if alert is None:
        return
    alert.earth_reply = p.payload.get("body")
    alert.updated_at = clock.now()
    alert.history.append(
        AlertHistory(at=clock.now(), actor=p.sender, role="earth", action="earth_replied", note=alert.earth_reply)
    )
    events.append(Event("alert.updated", alerts_service.brief(alert).model_dump(mode="json"), alert.crew_id))


async def step(session: AsyncSession, data: DataBundle) -> list[Event]:
    """One scheduler step: queued packets leave when the window is open; packets in transit whose arrival time has
    come are opened and delivered or rejected. Packets already in transit keep their arrival time. Does not commit;
    the events are published by the caller after commit."""
    now = clock.now()
    events: list[Event] = []
    env_id = await mission_service.current_environment_id(session, data)
    delays = {e.id.value: e.one_way_delay_s for e in data.environments.environments}

    if windows.window_open(now, env_id):
        delay = timedelta(seconds=windows.one_way_delay_s(env_id, delays))
        queued = (
            await session.scalars(select(Packet).where(Packet.status == "queued").order_by(Packet.created_at))
        ).all()
        for p in queued:
            p.status, p.sent_at, p.arrives_at = "in_transit", now, now + delay
            events.append(_event("packet.sent", p))

    due = (
        await session.scalars(
            select(Packet).where(Packet.status == "in_transit", Packet.arrives_at <= now).order_by(Packet.arrives_at)
        )
    ).all()
    for p in due:
        try:
            payload = sealing.open(p.sealed, p.header)
        except SealError as e:
            p.status, p.signature_valid, p.reject_reason, p.delivered_at = "rejected", False, e.reason, now
            await security_log.record_rejection(
                session,
                kind=e.reason,
                source=p.id,
                crew_id=p.crew_id,
                message=f"Packet {p.id} ({p.kind}) rejected on arrival: the seal does not verify ({e.reason}).",
            )
            events.append(_event("packet.rejected", p))
            continue
        p.status, p.signature_valid, p.payload, p.delivered_at = "delivered", True, payload, now
        events.append(_event("packet.arrived", p))
        if p.kind == "earth_reply":
            await _deliver_reply(session, p, events)
        elif p.kind == "donki_alert":
            await radiation_service.donki_arrived(session, p.id)
    await session.flush()
    return events


async def link_scheduler(data: DataBundle) -> None:
    """Background task, one step per real second, with its own session. An error is logged and the loop goes on."""
    while True:
        try:
            async with db.SessionLocal() as s:
                events = await step(s, data)
                await s.commit()
            publish_all(events)
        except Exception:
            log.exception("link scheduler step failed; continuing")
        await asyncio.sleep(STEP_S)
