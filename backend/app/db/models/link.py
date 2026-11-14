"""Coada navă ↔ Pământ.

Conținutul stă SIGILAT în `sealed` (security.sealing.seal). La livrare, backend-ul îl deschide (sealing.open) și
pune rezultatul în `payload` (necesar pentru /link/packets/{id} și /crew/{id}/messages).
Retrimiterea (replay) e blocată de UNIQUE(direction, seq).
"""
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, ForeignKey, Index, Integer, LargeBinary, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base, UTCDateTime


class Packet(Base):
    __tablename__ = "packets"
    __table_args__ = (
        UniqueConstraint("direction", "seq", name="uq_packet_direction_seq"),
        Index("ix_packet_status", "status"),
    )
    id: Mapped[str] = mapped_column(String(16), primary_key=True)        # "pk-0007"
    seq: Mapped[int] = mapped_column(Integer)
    direction: Mapped[str] = mapped_column(String(4))                    # down | up
    kind: Mapped[str] = mapped_column(String(16))                        # alert_l3 | weekly_summary | earth_reply | donki_alert
    status: Mapped[str] = mapped_column(String(12))                      # queued | in_transit | delivered | rejected
    title: Mapped[str] = mapped_column(String(160))
    sender: Mapped[str] = mapped_column(String(80))
    level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    alert_status: Mapped[str | None] = mapped_column(String(8), nullable=True)
    crew_id: Mapped[str | None] = mapped_column(ForeignKey("crew.id"), nullable=True)
    alert_id: Mapped[str | None] = mapped_column(ForeignKey("alerts.id"), nullable=True)
    in_reply_to: Mapped[str | None] = mapped_column(String(16), nullable=True)
    header: Mapped[dict[str, Any]] = mapped_column(JSON)                 # sealing.HEADER_FIELDS
    sealed: Mapped[bytes] = mapped_column(LargeBinary)
    size_bytes: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
    sent_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    arrives_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    signature_valid: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    reject_reason: Mapped[str | None] = mapped_column(String(16), nullable=True)   # bad_signature | replay
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)    # completat la livrare
    read: Mapped[bool] = mapped_column(Boolean, default=False)          # mesaj citit la bord
