"""Drumul oricărei date noi: salvare → motor → triaj → alerte → (nivel 3) pachet → evenimente. TASK T16.

Vezi backend/handoff/tasks/T16-*.md pentru pași, fișiere și criteriile de acceptare.
"""
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from .events import Event


@dataclass
class PipelineResult:
    alerts_created: list[str] = field(default_factory=list)
    alerts_updated: list[str] = field(default_factory=list)
    events: list[Event] = field(default_factory=list)      # de publicat DUPĂ commit


async def process(session: AsyncSession, crew_id: str, changed: set[str], *, day: int) -> PipelineResult:
    """`changed` = cheile de metrici atinse (ex. {"night_pulse_bpm"}). Rulează doar regulile pilonilor afectați,
    apoi engine.triage.decide, apoi scrie alertele (cu pașii din catalog și istoricul). Nivel 3 → link.queue.enqueue.
    Nu face commit."""
    raise NotImplementedError("T16")


async def replay_history(session: AsyncSession, *, until_day: int) -> None:
    """La pornire: rulează process() zi cu zi pentru 1..until_day, ca alertele din istoric să le producă motorul
    (alerta lui cm-2 apare în ziua 95 pentru că NightSignal o declanșează, nu pentru că e scrisă de mână)."""
    raise NotImplementedError("T16")
