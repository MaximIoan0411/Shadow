import math
from datetime import UTC, datetime, timedelta

import pytest

from app.engine.baseline import compute, deviation
from app.engine.types import Baseline, Point

T0 = datetime(2027, 1, 10, 3, tzinfo=UTC)


def series(values: list[float], first_day: int = 1) -> list[Point]:
    return [Point(day=first_day + i, t=T0 + timedelta(days=i), value=v) for i, v in enumerate(values)]


def test_constant_values_use_min_spread():
    b = compute(series([54.0] * 10), min_n=7, min_spread=1.0)
    assert b.median == 54.0 and b.spread == 1.0 and b.n == 10 and b.ready


def test_robust_spread_is_scaled_mad():
    b = compute(series([1, 2, 3, 4, 5]), min_n=1)
    assert b.median == 3
    assert b.spread == pytest.approx(1.4826 * 1)


def test_isolated_spike_does_not_move_median():
    calm = [54.0, 54.2, 53.8, 54.1, 53.9, 54.0, 54.2]
    with_spike = compute(series([*calm, 75.0]), min_n=7)
    assert with_spike.median == pytest.approx(54.05)
    assert with_spike.spread < 1


def test_excluded_days_do_not_count():
    points = series([54.0] * 7 + [61.0, 62.0, 63.0])
    b = compute(points, min_n=7, exclude_days={8, 9, 10})
    assert b.median == 54.0 and b.n == 7


def test_window_keeps_only_last_days():
    points = series([50.0] * 10 + [60.0] * 5)
    b = compute(points, min_n=1, window_days=5)
    assert b.median == 60.0 and b.n == 5


def test_window_counts_from_last_day_even_when_it_is_excluded():
    points = series([50.0] * 10 + [70.0, 70.0])
    b = compute(points, min_n=1, window_days=4, exclude_days={11, 12})
    assert b.n == 2 and b.median == 50.0


def test_ready_from_min_n():
    assert not compute(series([54.0] * 6), min_n=7).ready
    assert compute(series([54.0] * 7), min_n=7).ready


def test_empty_series():
    b = compute([], min_n=7, min_spread=0.5)
    assert math.isnan(b.median) and b.spread == 0.5 and b.n == 0 and not b.ready


def test_deviation_in_personal_spreads():
    base = Baseline(median=54.0, spread=2.0, n=10, ready=True)
    assert deviation(61.0, base) == pytest.approx(3.5)
    assert deviation(50.0, base) == pytest.approx(-2.0)


def test_deviation_without_baseline_is_nan():
    assert math.isnan(deviation(60.0, compute([], min_n=7)))
    assert math.isnan(deviation(60.0, Baseline(median=54.0, spread=0.0, n=3, ready=False)))


def test_cm2_history_baseline_is_personal():
    from app.datafiles import load_all
    from app.simulator.scenario import generate

    s = load_all().scenario
    days = generate(s, from_day=1, to_day=92)
    by_crew: dict[str, list[Point]] = {}
    for d in days:
        for key, value, _unit, at in d.measurements:
            if key == "night_pulse_bpm":
                by_crew.setdefault(d.crew_id, []).append(Point(day=d.day, t=at, value=value))
    medians = {c: compute(p, min_n=7).median for c, p in by_crew.items()}
    for crew_id, m in medians.items():
        assert abs(m - s.crew_baselines[crew_id]["night_pulse_bpm"]) < 0.5
    assert len({round(m) for m in medians.values()}) == 4
