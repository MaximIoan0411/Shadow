"""Evenimentele de publicat după commit. Gata, nu e un task (folosit de toate serviciile)."""
from dataclasses import dataclass
from typing import Any

from ..deps import publish


@dataclass(frozen=True)
class Event:
    type: str                 # unul din schemas.SseEvent.type
    data: Any                 # model Pydantic sau dict
    crew_id: str | None = None


def publish_all(events: list[Event]) -> None:
    """Se apelează DOAR după `await session.commit()`."""
    for e in events:
        publish(e.type, e.data, e.crew_id)
