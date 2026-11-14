"""Încărcarea: stimulul osos, recomandarea de împărțire, proiecția. Efect demonstrat DOAR pe animale. TASK T28."""
from ..types import PillarScore


def session_score(sets: list[dict]) -> float:
    """repetări × greutate, cu randament descrescător după primele repetări."""
    raise NotImplementedError("T28")


def daily_loading(session_scores: list[tuple[float, float]]) -> float:
    """(ora_în_zi, scor) pentru sesiunile zilei; bonus pentru sesiuni la câteva ore distanță."""
    raise NotImplementedError("T28")


def projection(adherence: float, split: bool, params: dict) -> tuple[float, float]:
    """(pierdere %/lună cu planul actual, cu antrenamentul împărțit). Estimare, nu măsurătoare."""
    raise NotImplementedError("T28")


def score(loading_today: float, target: float) -> PillarScore:
    raise NotImplementedError("T28")
