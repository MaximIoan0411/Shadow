"""Validarea măsurătorilor: valori imposibile și senzori „înghețați”.

Limitele fizic posibile vin din data/texts/checkin_indicators.json (`min`, `max`) și din `EXTRA_LIMITS` de mai
jos, pentru metricile care nu apar la check-in. Backend-ul încarcă ultimele valori și le dă funcției.
"""
from dataclasses import dataclass
from typing import Literal

PROVIZORIU: tuple[str, ...] = ()
"""Funcțiile al căror corp e încă provizoriu. Echipa de securitate scoate numele pe măsură ce le termină."""

FROZEN_REPEATS = 20
"""Aceeași valoare exactă de atâtea ori la rând (de la același dispozitiv) = senzor înghețat."""

EXTRA_LIMITS: dict[str, tuple[float, float]] = {
    "night_pulse_bpm": (25, 200),
    "resting_pulse_bpm": (25, 220),
    "hrv_lnrmssd": (0.5, 6.5),
    "dose_rate_usv_h": (0, 100_000),
}


@dataclass(frozen=True)
class Issue:
    kind: Literal["implausible", "frozen_sensor"]
    message: str           # în română, gata de afișat în /security/rejections


def check(metric_key: str, value: float, recent_values: list[float],
          limits: dict[str, tuple[float, float]]) -> Issue | None:
    """None = valoarea e acceptată. `recent_values` = ultimele valori ale aceluiași dispozitiv, cea mai nouă ultima.
    `limits` = limitele din checkin_indicators.json, completate de backend cu EXTRA_LIMITS."""
    lo_hi = limits.get(metric_key) or EXTRA_LIMITS.get(metric_key)
    if lo_hi and not (lo_hi[0] <= value <= lo_hi[1]):
        return Issue("implausible", f"Valoare imposibilă: {value} (interval posibil {lo_hi[0]}–{lo_hi[1]}).")
    tail = recent_values[-(FROZEN_REPEATS - 1):]
    if len(tail) == FROZEN_REPEATS - 1 and all(v == value for v in tail):
        return Issue("frozen_sensor", f"Aceeași valoare ({value}) de {FROZEN_REPEATS} ori la rând: senzor înghețat.")
    return None
