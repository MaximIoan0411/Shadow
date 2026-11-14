from datetime import UTC, datetime, timedelta

import pytest

from app.datafiles import load_all
from app.engine.derived import MIN_SPREAD
from app.engine.pillars.immune import baseline_before, night_signal, score, stress_index
from app.engine.types import Point
from app.simulator.scenario import generate

T0 = datetime(2027, 1, 10, 3, tzinfo=UTC)
MEDIAN = 54.0


@pytest.fixture(scope="module")
def data():
    return load_all()


@pytest.fixture(scope="module")
def rules(data):
    v = data.params.value
    return {
        "yellow_delta": v("nightsignal_yellow_delta"),
        "red_delta": v("nightsignal_red_delta_bpm"),
        "red_nights": v("nightsignal_red_consecutive_nights"),
    }


@pytest.fixture(scope="module")
def min_n(data):
    return data.params.value("nightsignal_min_nights_baseline")


def nights(*deltas: float, calm: int = 10) -> list[Point]:
    values = [MEDIAN] * calm + [MEDIAN + d for d in deltas]
    return [Point(day=i + 1, t=T0 + timedelta(days=i), value=v) for i, v in enumerate(values)]


def check(points, rules, min_n):
    day = points[-1].day
    base = baseline_before(points, day, min_n=min_n, min_spread=MIN_SPREAD["night_pulse_bpm"])
    return night_signal("cm-x", points, base, day=day, **rules), base


def test_calm_night_gives_nothing(rules, min_n):
    finding, _ = check(nights(1.0), rules, min_n)
    assert finding is None


def test_one_night_plus_4_is_yellow(rules, min_n):
    finding, _ = check(nights(4.0), rules, min_n)
    assert finding.level == 1 and finding.status == "watch"
    assert finding.recommendation_id == "immune-1-1"
    assert finding.title == "Night pulse +4 bpm, 1 night"


def test_one_night_plus_3_is_yellow(rules, min_n):
    finding, _ = check(nights(3.0), rules, min_n)
    assert finding.level == 1


def test_nightsignal_red_after_two_nights(rules, min_n):
    finding, _ = check(nights(4.0, 4.0), rules, min_n)
    assert finding.level == 2 and finding.status == "alert"
    assert finding.recommendation_id == "immune-2-1"
    assert finding.title == "Night pulse +4 bpm, 2 nights in a row"
    assert [e.metric_key for e in finding.evidence] == ["night_pulse_bpm", "temperature_c", "sleep_hours"]


def test_3_9_then_4_is_not_red(rules, min_n):
    finding, _ = check(nights(3.9, 4.0), rules, min_n)
    assert finding.level == 1


def test_red_needs_consecutive_nights(rules, min_n):
    points = nights(4.0, 0.0, 4.0)
    finding, _ = check(points, rules, min_n)
    assert finding.level == 1


def test_three_nights_in_a_row_title(rules, min_n):
    finding, _ = check(nights(5.0, 6.5, 7.0), rules, min_n)
    assert finding.level == 2
    assert finding.title == "Night pulse +7 bpm, 3 nights in a row"
    assert finding.extra["nights"] == 3


def test_baseline_not_ready_gives_none(rules, min_n):
    finding, base = check(nights(8.0, 8.0, calm=5), rules, min_n)
    assert not base.ready and finding is None


def test_missing_tonight_gives_none(rules, min_n):
    points = nights(5.0, 5.0)
    base = baseline_before(points, 13, min_n=min_n)
    assert night_signal("cm-x", points, base, day=13, **rules) is None


def test_scenario_cm2_yellow_on_94_red_on_95(data, rules, min_n):
    days = generate(data.scenario, from_day=1, to_day=96)
    pts = [
        Point(d.day, at, v)
        for d in days
        if d.crew_id == "cm-2"
        for k, v, _u, at in d.measurements
        if k == "night_pulse_bpm"
    ]
    temps = {
        d.day: Point(d.day, at, v)
        for d in days
        if d.crew_id == "cm-2"
        for k, v, _u, at in d.measurements
        if k == "temperature_c"
    }
    results = {}
    for day in (93, 94, 95, 96):
        upto = [p for p in pts if p.day <= day]
        base = baseline_before(
            upto, day, min_n=min_n, min_spread=MIN_SPREAD["night_pulse_bpm"], exclude_days={94, 95, 96}
        )
        results[day] = night_signal("cm-2", upto, base, day=day, temperature=temps[day], **rules)
    assert results[93] is None
    assert results[94].level == 1
    assert results[95].level == 2
    assert results[96].level == 2 and results[96].extra["nights"] == 3
    temp_ev = results[96].evidence[1]
    assert temp_ev.value == temps[96].value and temp_ev.baseline is None


def test_stress_index_bounds_and_missing_parts():
    assert stress_index(None, 0, None) == 0
    assert stress_index(100, 140, 6.0) == 100
    assert stress_index(None, 70, None) == pytest.approx(50)
    assert 0 < stress_index(68, 96, 1.2) < 100
    assert stress_index(100, 0, None) == pytest.approx(100 * 0.5 / 0.7, abs=0.1)


def test_score(rules, min_n):
    calm = nights(0.0)
    finding, base = check(calm, rules, min_n)
    s = score(calm, base, finding)
    assert s.score == 100 and s.status == "ok"

    sick = nights(4.0, 7.0)
    finding, base = check(sick, rules, min_n)
    s = score(sick, base, finding)
    assert s.status == "alert" and s.score == pytest.approx(58) and s.headline == finding.title

    early = nights(calm=3)
    finding, base = check(early, rules, min_n)
    assert score(early, base, finding).status == "unknown"
