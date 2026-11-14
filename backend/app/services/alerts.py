"""Alertele: listă, detaliu, confirmare, pași, escaladare, închidere; recheck_loop (T30). TASK T17.

Vezi backend/handoff/tasks/T17-*.md pentru pași, fișiere și criteriile de acceptare.
"""


async def recheck_loop() -> None:
    """Task din fundal (pas 5 s). Alertele cu recheck_at depășit: valorile au revenit → resolved; nu → +1 nivel. T30."""
    raise NotImplementedError("T30")
