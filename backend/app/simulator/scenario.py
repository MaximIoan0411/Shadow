"""Generatorul celor 140 de zile, din data/scenario/scenario.json. TASK T10.

PUR: fără bază de date. Întoarce listele de rânduri pe care seed_history (T11) le scrie în bază.
"""
from dataclasses import dataclass, field
from datetime import datetime

from ..datafiles import ScenarioFile


@dataclass
class DayData:
    """Tot ce se întâmplă într-o zi pentru un membru. Valorile sunt marcate source="simulated"."""
    crew_id: str
    day: int
    measurements: list[tuple[str, float, str, datetime]] = field(default_factory=list)   # (metric_key, value, unit, at)
    checkin: dict | None = None             # câmpurile CheckinCreate + created_at
    exercise: list[dict] = field(default_factory=list)                                   # câmpurile ExerciseSessionCreate
    keystroke: dict | None = None           # trăsăturile unei sesiuni de dimineață (pentru baseline-ul tastării)


def generate(scenario: ScenarioFile, *, from_day: int, to_day: int) -> list[DayData]:
    """Zilele [from_day, to_day] pentru toți membrii. random.Random(scenario.seed + day) pe fiecare zi, ca o zi să
    iasă la fel indiferent de interval (important pentru jump_to_day, T33). Evenimentele din scenario.events
    modifică valorile (params din fiecare eveniment)."""
    raise NotImplementedError("T10")
