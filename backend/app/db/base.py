"""Baza declarativă și tipurile comune. Verificat (plan, secțiunea 5)."""
from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.types import TypeDecorator


class UTCDateTime(TypeDecorator):
    """Dată-oră mereu în UTC. SQLite nu păstrează fusul orar; acest tip îl impune:
    refuză la scriere o dată fără fus orar și pune UTC la citire."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("Dată-oră fără fus orar. Folosiți clock.now() sau datetime(..., tzinfo=UTC).")
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value, dialect):
        return value.replace(tzinfo=UTC) if value is not None else None


class Base(AsyncAttrs, DeclarativeBase):
    pass


def utcnow_placeholder() -> datetime:
    """NU folosiți ca valoare implicită: timpul vine din clock.now() (timpul misiunii), dat explicit la creare."""
    raise RuntimeError("Dați data explicit, din clock.now().")
