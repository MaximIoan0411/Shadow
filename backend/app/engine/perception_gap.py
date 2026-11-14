"""Decalajul de percepție — ideea centrală. TASK T18."""
from .types import Status


def compute(mood: int | None, objective_scores: dict[str, float]) -> tuple[float | None, float | None, float | None, Status, str, list[str]]:
    """Întoarce (self_score, objective_score, gap, status, explanation, contributing_signals).
    self = mood × 20; objective = media ponderată a scorurilor (tastare, pvt, puls de noapte, somn);
    gap = self − objective; praguri în derived.py. Textul în română, cu cifrele care au contat."""
    raise NotImplementedError("T18")
