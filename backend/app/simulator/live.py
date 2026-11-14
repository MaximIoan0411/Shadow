"""Datele LIVE, cât ceasul merge. Task din fundal (pas 2 s reale). TASK T25 (radiații) și T33 (salt de zi).

La fiecare pas: dacă ceasul a trecut de 03:00 → pulsul de noapte al zilei; dacă e furtună → o citire de radiații;
dacă a început o zi nouă → datele zilei din scenariu. Totul prin services/pipeline.process.
"""


async def live_simulator() -> None:
    raise NotImplementedError("T25")
