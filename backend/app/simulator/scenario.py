import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from ..datafiles import ScenarioEvent, ScenarioFile

UNITS = {
    "night_pulse_bpm": "bpm",
    "resting_pulse_bpm": "bpm",
    "hrv_lnrmssd": "ln(ms)",
    "temperature_c": "°C",
    "sleep_hours": "h",
    "systolic_mmhg": "mmHg",
    "diastolic_mmhg": "mmHg",
    "glucose_mg_dl": "mg/dL",
}

NOISE = {
    "night_pulse_bpm": 0.6,
    "resting_pulse_bpm": 1.5,
    "hrv_lnrmssd": 0.08,
    "temperature_c": 0.1,
    "sleep_hours": 0.3,
    "systolic_mmhg": 3.0,
    "diastolic_mmhg": 2.0,
    "glucose_mg_dl": 3.0,
}
KEYSTROKE_NOISE_PCT = 3.0
NIGHT_HOUR = 3
MORNING_HOUR = 7
KEYSTROKE_TIME = (7, 15)
EXERCISE_HOURS = (9, 16)
EXERCISE_MINUTES = 40
EXERCISE_LOAD_KG = 80.0
EXERCISES = ("ARED squat", "ARED deadlift", "ARED heel raise")
MOOD_CHOICES = (3, 4, 5)
MOOD_WEIGHTS = (1, 6, 2)

DECONDITIONING_PULSE_DELTA = 6.0
DECONDITIONING_HRV_DELTA = -0.3

LIVE_ONLY_EVENTS = {"solar_storm"}


@dataclass
class DayData:
    crew_id: str
    day: int
    measurements: list[tuple[str, float, str, datetime]] = field(default_factory=list)
    checkin: dict | None = None
    exercise: list[dict] = field(default_factory=list)
    keystroke: dict | None = None


def _applies(event: ScenarioEvent, crew_id: str, day: int) -> bool:
    first, last = event.days
    if not first <= day <= last or event.kind in LIVE_ONLY_EVENTS:
        return False
    if event.crew == "all":
        return True
    if isinstance(event.crew, str):
        return event.crew == crew_id
    return crew_id in event.crew


def _triangle(event: ScenarioEvent, day: int) -> float:
    first, last = event.days
    if last == first:
        return 1.0
    middle = (first + last) / 2
    return max(0.0, 1.0 - abs(day - middle) / (middle - first + 1))


def _at(day_start: datetime, hour: int, minute: int = 0) -> datetime:
    return day_start + timedelta(hours=hour, minutes=minute)


def _one_day(scenario: ScenarioFile, crew_id: str, crew_nr: int, day: int) -> DayData:
    rng = random.Random(scenario.seed * 1000 + day * 10 + crew_nr)
    base = scenario.crew_baselines[crew_id]
    day_start = scenario.start + timedelta(days=day - 1)

    values = {k: base[k] + rng.uniform(-NOISE[k], NOISE[k]) for k in UNITS}
    kpm = base["keys_per_min"] * (1 + rng.uniform(-KEYSTROKE_NOISE_PCT, KEYSTROKE_NOISE_PCT) / 100)
    hold = base["hold_ms_mean"] * (1 + rng.uniform(-KEYSTROKE_NOISE_PCT, KEYSTROKE_NOISE_PCT) / 100)
    mood = rng.choices(MOOD_CHOICES, weights=MOOD_WEIGHTS)[0]
    backspace_rate = 0.05 + rng.uniform(-0.01, 0.01)
    n_keys = rng.randint(300, 420)
    loads = [EXERCISE_LOAD_KG + rng.uniform(-5, 5) for _ in EXERCISES]
    sessions = len(EXERCISE_HOURS)

    for event in scenario.events:
        if not _applies(event, crew_id, day):
            continue
        p = event.params
        kind = event.kind
        if kind == "poor_sleep":
            values["sleep_hours"] += p.get("sleep_hours_delta", 0)
            kpm *= 1 + p.get("keys_per_min_pct", 0) / 100
        elif kind == "skipped_exercise":
            sessions = int(p.get("sessions", 0))
        elif kind == "infection_onset":
            values["night_pulse_bpm"] += p.get("night_pulse_bpm_delta_by_day", {}).get(str(day), 0)
            values["temperature_c"] += p.get("temperature_c_delta", 0)
            values["sleep_hours"] += p.get("sleep_hours_delta", 0)
        elif kind == "keystroke_slowdown":
            kpm *= 1 + p.get("keys_per_min_pct", 0) / 100
            hold *= 1 + p.get("hold_ms_pct", 0) / 100
            mood = int(p.get("reported_mood", mood))
        elif kind == "cardio_deconditioning":
            weight = _triangle(event, day)
            values["resting_pulse_bpm"] += p.get("resting_pulse_bpm_delta", DECONDITIONING_PULSE_DELTA) * weight
            values["hrv_lnrmssd"] += p.get("hrv_lnrmssd_delta", DECONDITIONING_HRV_DELTA) * weight

    values = {k: round(v, 2 if k == "hrv_lnrmssd" else 1) for k, v in values.items()}
    morning = _at(day_start, MORNING_HOUR)
    measurements = [
        (k, v, UNITS[k], _at(day_start, NIGHT_HOUR) if k == "night_pulse_bpm" else morning) for k, v in values.items()
    ]

    checkin = {
        "mood": mood,
        "systolic_mmhg": values["systolic_mmhg"],
        "diastolic_mmhg": values["diastolic_mmhg"],
        "pulse_bpm": values["resting_pulse_bpm"],
        "glucose_mg_dl": values["glucose_mg_dl"],
        "temperature_c": values["temperature_c"],
        "sleep_hours": values["sleep_hours"],
        "meals_eaten": "all",
        "note": None,
        "created_at": morning,
    }

    exercise = [
        {
            "kind": "resistance",
            "started_at": _at(day_start, hour),
            "duration_min": EXERCISE_MINUTES,
            "sets": [
                {"exercise": name, "reps": 10, "load_kg": round(load, 1)}
                for name, load in zip(EXERCISES, loads, strict=True)
            ],
        }
        for hour in EXERCISE_HOURS[:sessions]
    ]

    flight = 60000 / kpm
    keystroke = {
        "started_at": _at(day_start, *KEYSTROKE_TIME),
        "context": "free_typing",
        "hold_ms_mean": round(hold, 1),
        "hold_ms_sd": round(hold * 0.2, 1),
        "flight_ms_mean": round(flight, 1),
        "flight_ms_sd": round(flight * 0.35, 1),
        "backspace_rate": round(backspace_rate, 3),
        "keys_per_min": round(kpm, 1),
        "n_keys": n_keys,
    }

    return DayData(
        crew_id=crew_id, day=day, measurements=measurements, checkin=checkin, exercise=exercise, keystroke=keystroke
    )


def generate(scenario: ScenarioFile, *, from_day: int, to_day: int) -> list[DayData]:
    first, last = max(1, from_day), min(scenario.total_days, to_day)
    crew = sorted(scenario.crew_baselines)
    return [
        _one_day(scenario, crew_id, nr, day) for day in range(first, last + 1) for nr, crew_id in enumerate(crew, 1)
    ]
