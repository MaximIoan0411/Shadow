"""Interogări refolosite (citiri). TASK T13. Toate primesc sesiunea și întorc tipuri din engine/types.py,
ca motorul să nu știe de SQLAlchemy."""
from sqlalchemy.ext.asyncio import AsyncSession

from ..engine.types import Point


async def series(session: AsyncSession, crew_id: str, metric_key: str, from_day: int, to_day: int) -> list[Point]:
    """O metrică pe zile, crescător. O valoare pe zi (dacă sunt mai multe în aceeași zi: ultima)."""
    raise NotImplementedError("T13")


async def series_all_crew(session: AsyncSession, metric_key: str, from_day: int, to_day: int) -> dict[str, list[Point]]:
    """Aceeași metrică pentru tot echipajul (cauza de mediu, T29)."""
    raise NotImplementedError("T13")


async def latest(session: AsyncSession, crew_id: str, metric_key: str, up_to_day: int) -> Point | None:
    raise NotImplementedError("T13")


async def recent_device_values(session: AsyncSession, device_id: str, metric_key: str, n: int) -> list[float]:
    """Ultimele n valori ale unui dispozitiv (senzor înghețat, T32)."""
    raise NotImplementedError("T13")
