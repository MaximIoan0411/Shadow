"""Jurnalul de acces (doar INSERT) și respingerile. Scrise de codul echipei de securitate."""
from datetime import datetime

from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base, UTCDateTime


class AccessLog(Base):
    """hash = SHA-256(prev_hash + JSON canonic al intrării), primele 16 caractere (security.access_log.entry_hash).
    NU există UPDATE sau DELETE pe acest tabel."""

    __tablename__ = "access_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    at: Mapped[datetime] = mapped_column(UTCDateTime)
    actor: Mapped[str] = mapped_column(String(80))
    actor_role: Mapped[str] = mapped_column(String(12))
    action: Mapped[str] = mapped_column(String(24))
    resource: Mapped[str] = mapped_column(String(120))
    crew_id: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    outcome: Mapped[str] = mapped_column(String(8))                      # allowed | denied
    prev_hash: Mapped[str] = mapped_column(String(16))
    hash: Mapped[str] = mapped_column(String(16))


class Rejection(Base):
    """O valoare sau un pachet respins: semnătură invalidă, valoare imposibilă, senzor înghețat, replay."""

    __tablename__ = "rejections"
    id: Mapped[str] = mapped_column(String(16), primary_key=True)        # "rj-0003"
    at: Mapped[datetime] = mapped_column(UTCDateTime)
    kind: Mapped[str] = mapped_column(String(16))                        # RejectionKind
    source: Mapped[str] = mapped_column(String(60))                      # device_id sau packet id
    crew_id: Mapped[str | None] = mapped_column(String(16), nullable=True)
    metric_key: Mapped[str | None] = mapped_column(String(40), nullable=True)
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    message: Mapped[str] = mapped_column(Text)
