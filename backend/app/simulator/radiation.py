"""Rata dozei de la dozimetru. Forma furtunii e SINTETICĂ; orele vin din fișierul DONKI. TASK T25."""
from datetime import datetime


def dose_rate(t: datetime, *, baseline_usv_h: float, storm_onset: datetime | None, peak_multiplier: float,
              sheltered: bool, shield_factor: float, rng_seed: int) -> float:
    """Fond + zgomot ±5%; după onset: urcă repede (~20 min) și scade lent (ore). Adăpostul înmulțește cu shield_factor."""
    raise NotImplementedError("T25")
