"""Inima: scorul de pregătire pentru revenire. Praguri DERIVATE (medicina sportivă). TASK T27."""
from ..types import Baseline, Finding, PillarScore, Point


def landing_readiness(resting_pulse: list[Point], hrv: list[Point], systolic: list[Point],
                      bases: dict[str, Baseline], params: dict) -> tuple[PillarScore, Finding | None]:
    raise NotImplementedError("T27")
