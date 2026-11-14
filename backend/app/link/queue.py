from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..clock import clock
from ..db.models import Packet
from ..ids import next_id, next_seq
from ..security import sealing
from ..security.keys import Keys

SENDER_OF_DIRECTION = {"down": "ship", "up": "earth"}
_keys: Keys | None = None


def configure(keys: Keys) -> None:
    """Called once at startup with app.state.keys, so the packet headers carry the right key ids."""
    global _keys
    _keys = keys


def _key_id(sender: str) -> str:
    if _keys is None:
        raise RuntimeError("link queue not configured: call queue.configure(keys) at startup")
    return _keys.ship_key_id if sender == "ship" else _keys.earth_key_id


async def enqueue(
    session: AsyncSession,
    *,
    direction: str,
    kind: str,
    title: str,
    sender: str,
    payload: dict[str, Any],
    crew_id: str | None = None,
    alert_id: str | None = None,
    level: int | None = None,
    alert_status: str | None = None,
    in_reply_to: str | None = None,
) -> Packet:
    """A new sealed packet in the queue (status `queued`). Only the sealed bytes are stored; `payload` is filled in
    at delivery (link/scheduler.py). Does not commit. `packet.sent` is published by the scheduler on departure."""
    signer = SENDER_OF_DIRECTION[direction]
    packet_id = await next_id(session, "pk")
    seq = await next_seq(session, direction)
    now = clock.now()
    header = {
        "id": packet_id,
        "seq": seq,
        "direction": direction,
        "kind": kind,
        "key_id": _key_id(signer),
        "created_at": now.isoformat(),
    }
    sealed = sealing.seal(payload, header, sender=signer)
    packet = Packet(
        id=packet_id,
        seq=seq,
        direction=direction,
        kind=kind,
        status="queued",
        title=title[:160],
        sender=sender,
        level=level,
        alert_status=alert_status,
        crew_id=crew_id,
        alert_id=alert_id,
        in_reply_to=in_reply_to,
        header=header,
        sealed=sealed,
        size_bytes=len(sealed),
        created_at=now,
        payload=None,
        read=False,
    )
    session.add(packet)
    await session.flush()
    return packet
