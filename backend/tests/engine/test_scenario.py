import pytest

from app.datafiles import load_all
from app.simulator.scenario import DayData, generate


@pytest.fixture(scope="module")
def scenario():
    return load_all().scenario


@pytest.fixture(scope="module")
def history(scenario):
    return generate(scenario, from_day=1, to_day=96)


def day_of(days: list[DayData], crew_id: str, day: int) -> DayData:
    return next(d for d in days if d.crew_id == crew_id and d.day == day)


def metric(d: DayData, key: str) -> float:
    return next(v for k, v, _unit, _at in d.measurements if k == key)


def test_two_runs_are_identical(scenario, history):
    assert generate(scenario, from_day=1, to_day=96) == history


def test_one_day_is_the_same_whatever_the_interval(scenario, history):
    alone = generate(scenario, from_day=94, to_day=94)
    assert len(alone) == 4
    for d in alone:
        assert d == day_of(history, d.crew_id, 94)


def test_all_crew_every_day(history):
    assert len(history) == 96 * 4
    assert {d.crew_id for d in history} == {"cm-1", "cm-2", "cm-3", "cm-4"}


def test_infection_night_pulse_of_cm2(scenario, history):
    base = scenario.crew_baselines["cm-2"]["night_pulse_bpm"]
    assert metric(day_of(history, "cm-2", 93), "night_pulse_bpm") < base + 3
    assert metric(day_of(history, "cm-2", 94), "night_pulse_bpm") >= base + 4
    assert metric(day_of(history, "cm-2", 95), "night_pulse_bpm") >= base + 4


def test_night_pulse_noise_stays_small(scenario, history):
    for d in history:
        if d.crew_id == "cm-2" and 93 <= d.day <= 100:
            continue
        base = scenario.crew_baselines[d.crew_id]["night_pulse_bpm"]
        assert abs(metric(d, "night_pulse_bpm") - base) < 0.8


def test_skipped_exercise_day_61_for_cm2(history):
    assert day_of(history, "cm-2", 61).exercise == []
    assert len(day_of(history, "cm-1", 61).exercise) == 2
    assert [s["started_at"].hour for s in day_of(history, "cm-2", 60).exercise] == [9, 16]


def test_poor_sleep_hits_everyone(scenario, history):
    for crew_id, base in scenario.crew_baselines.items():
        assert metric(day_of(history, crew_id, 40), "sleep_hours") <= base["sleep_hours"] - 1.2


def test_keystroke_slowdown_with_mood_4(scenario, history):
    base = scenario.crew_baselines["cm-2"]
    d = day_of(history, "cm-2", 96)
    assert d.keystroke["keys_per_min"] <= base["keys_per_min"] * 0.86
    assert d.keystroke["hold_ms_mean"] >= base["hold_ms_mean"] * 1.13
    assert d.checkin["mood"] == 4


def test_solar_storm_is_not_generated(history):
    for d in history:
        assert not any(k.startswith("dose") for k, *_ in d.measurements)


def test_times_and_units(scenario, history):
    d = day_of(history, "cm-1", 1)
    night = next(at for k, _v, _u, at in d.measurements if k == "night_pulse_bpm")
    assert night == scenario.start.replace(hour=3)
    assert d.checkin["created_at"] == scenario.start.replace(hour=7)
    assert d.keystroke["started_at"] == scenario.start.replace(hour=7, minute=15)
    assert {u for _k, _v, u, _at in d.measurements} >= {"bpm", "°C", "h", "mmHg", "mg/dL"}


def test_cardio_deconditioning_raises_resting_pulse(scenario):
    days = generate(scenario, from_day=100, to_day=125)
    pulse = {d.day: metric(d, "resting_pulse_bpm") for d in days if d.crew_id == "cm-2"}
    base = scenario.crew_baselines["cm-2"]["resting_pulse_bpm"]
    assert pulse[114] >= base + 3
    assert abs(pulse[125] - base) < 2


def test_range_is_clipped_to_mission(scenario):
    assert {d.day for d in generate(scenario, from_day=139, to_day=200)} == {139, 140}
