import math
import random
from datetime import datetime

# The SHAPE of the storm is synthetic (no measured dose is published for the 2024 event); only its time is real.
NOISE = 0.05
RISE_MIN = 20.0
DECAY_H = 3.0


def storm_multiplier(t: datetime, storm_onset: datetime | None, peak_multiplier: float) -> float:
    if storm_onset is None or t < storm_onset:
        return 1.0
    minutes = (t - storm_onset).total_seconds() / 60
    if minutes <= RISE_MIN:
        return 1.0 + (peak_multiplier - 1.0) * minutes / RISE_MIN
    return 1.0 + (peak_multiplier - 1.0) * math.exp(-(minutes - RISE_MIN) / (DECAY_H * 60))


def dose_rate(
    t: datetime,
    *,
    baseline_usv_h: float,
    storm_onset: datetime | None,
    peak_multiplier: float,
    sheltered: bool,
    shield_factor: float,
    rng_seed: int,
) -> float:
    """Background ± 5% noise; after the onset it rises in ~20 min to `peak_multiplier` × background and decays over
    hours. In the shelter the rate is multiplied by `shield_factor`. The same minute always gives the same noise."""
    rng = random.Random(rng_seed * 1_000_003 + int(t.timestamp() // 60))
    rate = baseline_usv_h * storm_multiplier(t, storm_onset, peak_multiplier) * (1 + rng.uniform(-NOISE, NOISE))
    return round(rate * (shield_factor if sheltered else 1.0), 2)
