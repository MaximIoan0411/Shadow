"""Semnale încrucișate și cauza de mediu. TASK T29."""
from .types import Finding


def environmental_cause(findings_today: list[Finding], crew_count: int) -> set[str]:
    """Subiectele la care cel puțin ENVIRONMENTAL_MIN_CREW membri au aceeași constatare → cauză de mediu."""
    raise NotImplementedError("T29")


def detect(findings_window: list[Finding]) -> list[dict]:
    """Trei abateri mici din piloni diferiți la același om, în CROSS_SIGNAL_WINDOW_DAYS → un CrossSignal
    (forma din contract: id, title, pillars, signals, confidence, explanation)."""
    raise NotImplementedError("T29")
