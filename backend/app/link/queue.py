"""Crearea pachetelor. TASK T23."""
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Packet


async def enqueue(session: AsyncSession, *, direction: str, kind: str, title: str, sender: str, payload: dict[str, Any],
                  crew_id: str | None = None, alert_id: str | None = None, level: int | None = None,
                  alert_status: str | None = None, in_reply_to: str | None = None) -> Packet:
    """next_id("pk") + next_seq(direction) → header (sealing.HEADER_FIELDS) → sealing.seal(payload, header, sender=…)
    → Packet(status="queued"). Nu face commit. Evenimentul packet.sent îl trimite planificatorul, la plecare."""
    raise NotImplementedError("T23")
