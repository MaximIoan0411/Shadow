import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..clock import clock
from ..datafiles import DataBundle
from ..db.models.alerts import Alert as AlertRow
from ..db.models.alerts import AlertHistory
from ..db.models.link import Packet as PacketRow
from ..db.models.users import Crew
from ..deps import ApiError
from ..link import queue
from ..schemas import (
    CrewMessage,
    EarthReplyCreate,
    OutboxCreate,
    Packet,
    PacketCrypto,
    PacketDetail,
    PacketDirection,
    PacketStatus,
    Role,
    User,
)

TOPIC_LABEL = {
    "behavioral": "Typing",
    "cardio": "Heart",
    "immune": "Sentinel",
    "musculoskeletal": "Loading",
    "radiation": "Radiation",
    "cross_signal": "Cross-signal",
}
WEEKLY_SUMMARY_DEFAULT = "Weekly summary approved by the astronaut."


# --------------------------------------------------------------------------- schema


def to_packet(p: PacketRow) -> Packet:
    progress, eta = 0.0, None
    if p.status == PacketStatus.in_transit.value and p.sent_at and p.arrives_at:
        total = (p.arrives_at - p.sent_at).total_seconds()
        left = max((p.arrives_at - clock.now()).total_seconds(), 0.0)
        progress = 1.0 if total <= 0 else min(max(1 - left / total, 0.0), 1.0)
        eta = round(clock.real_seconds(left), 1)
    elif p.status in (PacketStatus.delivered.value, PacketStatus.rejected.value):
        progress = 1.0
    return Packet(
        id=p.id,
        seq=p.seq,
        direction=p.direction,
        kind=p.kind,
        status=p.status,
        title=p.title,
        sender=p.sender,
        level=p.level,
        alert_status=p.alert_status,
        crew_id=p.crew_id,
        alert_id=p.alert_id,
        in_reply_to=p.in_reply_to,
        created_at=p.created_at,
        sent_at=p.sent_at,
        arrives_at=p.arrives_at,
        delivered_at=p.delivered_at,
        progress=round(progress, 3),
        eta_real_s=eta,
        signature_valid=p.signature_valid,
        reject_reason=p.reject_reason,
        size_bytes=p.size_bytes,
    )


def _crypto(p: PacketRow) -> PacketCrypto:
    try:
        box = json.loads(p.sealed)
    except ValueError:
        box = {}
    box = box if isinstance(box, dict) else {}
    return PacketCrypto(
        key_id=p.header.get("key_id", ""),
        nonce_b64=str(box.get("nonce_b64", "")),
        signature_b64=str(box.get("signature_b64", "")),
    )


def _may_read(p: PacketRow, user: User) -> bool:
    if p.status != PacketStatus.delivered.value:
        return False
    if user.role == Role.earth:
        return p.direction == PacketDirection.down.value
    if user.role == Role.cmo:
        return p.direction == PacketDirection.up.value or p.sender == user.display_name
    return False


def to_detail(p: PacketRow, user: User) -> PacketDetail:
    return PacketDetail(
        **to_packet(p).model_dump(), payload=p.payload if _may_read(p, user) else None, crypto=_crypto(p)
    )


# --------------------------------------------------------------------------- creating packets


async def send_alert_to_earth(
    session: AsyncSession, data: DataBundle, alert: AlertRow, *, sender: str, note: str | None
) -> PacketRow:
    """Level 3: the alert goes to Earth as a sealed `alert_l3` packet. `alert` must have steps and history loaded."""
    from . import alerts as alerts_service

    payload = {"alert": alerts_service.to_schema(alert, data).model_dump(mode="json"), "note": note}
    packet = await queue.enqueue(
        session,
        direction=PacketDirection.down.value,
        kind="alert_l3",
        title=f"{TOPIC_LABEL.get(alert.topic, alert.topic)} · {alert.title}",
        sender=sender,
        payload=payload,
        crew_id=alert.crew_id,
        alert_id=alert.id,
        level=alert.level,
        alert_status=alert.status,
    )
    alert.packet_id = packet.id
    alert.history.append(
        AlertHistory(at=clock.now(), actor=sender, role=None, action="packet_sent", note=f"Packet {packet.id} queued.")
    )
    return packet


async def _alert(session: AsyncSession, alert_id: str) -> AlertRow:
    stmt = (
        select(AlertRow)
        .where(AlertRow.id == alert_id)
        .options(selectinload(AlertRow.steps), selectinload(AlertRow.history))
    )
    a = await session.scalar(stmt)
    if a is None:
        raise ApiError(404, "not_found", f"Alert {alert_id} does not exist.")
    return a


async def outbox(session: AsyncSession, data: DataBundle, body: OutboxCreate, user: User) -> Packet:
    if user.role == Role.astronaut and body.crew_id != user.crew_id:
        raise ApiError(403, "forbidden", "You can only send data about yourself.")
    if await session.get(Crew, body.crew_id) is None:
        raise ApiError(404, "not_found", f"Crew member {body.crew_id} does not exist.")
    if body.kind == "alert_l3":
        if not body.alert_id:
            raise ApiError(
                422,
                "validation_error",
                "alert_l3 needs an alert_id.",
                {"fields": [{"field": "alert_id", "problem": "required for alert_l3"}]},
            )
        alert = await _alert(session, body.alert_id)
        if alert.crew_id != body.crew_id:
            raise ApiError(422, "validation_error", "The alert belongs to another crew member.")
        packet = await send_alert_to_earth(session, data, alert, sender=user.display_name, note=body.body)
    else:
        week = (clock.mission_day() - 1) // 7 + 1
        packet = await queue.enqueue(
            session,
            direction=PacketDirection.down.value,
            kind="weekly_summary",
            title=f"Weekly summary · week {week}",
            sender=user.display_name,
            payload={"crew_id": body.crew_id, "week": week, "summary": body.body or WEEKLY_SUMMARY_DEFAULT},
            crew_id=body.crew_id,
        )
    await session.commit()
    return to_packet(packet)


async def earth_reply(session: AsyncSession, body: EarthReplyCreate, user: User) -> Packet:
    if await session.get(Crew, body.crew_id) is None:
        raise ApiError(404, "not_found", f"Crew member {body.crew_id} does not exist.")
    if body.alert_id is not None:
        alert = await session.get(AlertRow, body.alert_id)
        if alert is None:
            raise ApiError(404, "not_found", f"Alert {body.alert_id} does not exist.")
        if alert.crew_id != body.crew_id:
            raise ApiError(422, "validation_error", "The alert belongs to another crew member.")
    packet = await queue.enqueue(
        session,
        direction=PacketDirection.up.value,
        kind="earth_reply",
        title=f"Reply: {body.body[:60]}",
        sender=user.display_name,
        payload={"body": body.body, "alert_id": body.alert_id},
        crew_id=body.crew_id,
        alert_id=body.alert_id,
        in_reply_to=body.in_reply_to,
    )
    await session.commit()
    return to_packet(packet)


# --------------------------------------------------------------------------- reading


async def packets(
    session: AsyncSession, direction: PacketDirection | None, status: PacketStatus | None, limit: int
) -> list[Packet]:
    stmt = select(PacketRow)
    if direction is not None:
        stmt = stmt.where(PacketRow.direction == direction.value)
    if status is not None:
        stmt = stmt.where(PacketRow.status == status.value)
    stmt = stmt.order_by(PacketRow.created_at.desc(), PacketRow.id.desc()).limit(limit)
    return [to_packet(p) for p in (await session.scalars(stmt)).all()]


async def packet(session: AsyncSession, packet_id: str, user: User) -> PacketDetail:
    p = await session.get(PacketRow, packet_id)
    if p is None:
        raise ApiError(404, "not_found", f"Packet {packet_id} does not exist.")
    return to_detail(p, user)


def _message_body(p: PacketRow) -> str:
    payload = p.payload or {}
    if p.kind == "earth_reply":
        return str(payload.get("body", ""))
    event = payload.get("event") or {}
    return str(payload.get("text") or f"Solar particle event warning ({event.get('donki_id', 'NASA DONKI')}).")


async def messages(session: AsyncSession, crew_id: str) -> list[CrewMessage]:
    stmt = (
        select(PacketRow)
        .where(
            PacketRow.direction == PacketDirection.up.value,
            PacketRow.status == PacketStatus.delivered.value,
            (PacketRow.crew_id == crew_id) | (PacketRow.kind == "donki_alert"),
        )
        .order_by(PacketRow.delivered_at.desc())
    )
    out = []
    for p in (await session.scalars(stmt)).all():
        event = (p.payload or {}).get("event") or {}
        out.append(
            CrewMessage(
                packet_id=p.id,
                kind=p.kind,
                sender=p.sender,
                body=_message_body(p),
                sent_at=p.sent_at,
                delivered_at=p.delivered_at,
                alert_id=p.alert_id,
                donki_event_id=event.get("donki_id"),
                read=p.read,
            )
        )
    return out
