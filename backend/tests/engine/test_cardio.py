from datetime import UTC, datetime, timedelta

import pytest

from app.datafiles import load_all
from app.engine.pillars.cardio import landing_readiness
from app.engine.types import Point
from app.services.pipeline import cardio_day, cardio_params
from app.simulator.scenario import generate
from tests.conftest import auth

T0 = datetime(2027, 1, 10, 7, tzinfo=UTC)
DAYS = 60


@pytest.fixture(scope="module")
def data():
    return load_all()


def flat(value: float, *, changes: dict[int, float] | None = None, wobble: float = 0.0) -> list[Point]:
    changes = changes or {}
    return [
        Point(d, T0 + timedelta(days=d - 1), value + changes.get(d, 0.0) + (wobble if d % 2 else -wobble))
        for d in range(1, DAYS + 1)
    ]


def series(hr=None, hrv=None, sbp=None) -> dict:
    return {
        "resting_pulse_bpm": hr or flat(57.0, wobble=0.5),
        "hrv_lnrmssd": hrv or flat(4.1, wobble=0.03),
        "systolic_mmhg": sbp or flat(110.0, wobble=1.0),
    }


def rise(days: range, by: float) -> dict[int, float]:
    return {d: by for d in days}


def test_steady_values_are_ok_and_near_100(data):
    score, finding = cardio_day("cm-x", DAYS, series(), data, None)
    assert finding is None and score.status == "ok" and score.score >= 98


def test_resting_pulse_rise_for_three_days_is_watch(data):
    hr = flat(57.0, wobble=0.5, changes=rise(range(DAYS - 9, DAYS + 1), 6.0))
    score, finding = cardio_day("cm-x", DAYS, series(hr=hr), data, None)
    assert finding.level == 1 and finding.status == "watch" and finding.recommendation_id == "cardio-1-1"
    assert finding.title.startswith(("Resting pulse +5 bpm", "Resting pulse +6 bpm")) and score.score < 90


def test_short_rise_is_not_enough(data):
    hr = flat(57.0, wobble=0.5, changes=rise(range(DAYS - 1, DAYS + 1), 6.0))
    _score, finding = cardio_day("cm-x", DAYS, series(hr=hr), data, None)
    assert finding is None


def test_hrv_drop_alone_is_watch(data):
    hrv = flat(4.1, wobble=0.03, changes=rise(range(DAYS - 9, DAYS + 1), -0.4))
    _score, finding = cardio_day("cm-x", DAYS, series(hrv=hrv), data, None)
    assert finding.level == 1 and finding.title.startswith("Heart rate variability below")


def test_both_together_is_level_2(data):
    hr = flat(57.0, wobble=0.5, changes=rise(range(DAYS - 9, DAYS + 1), 6.0))
    hrv = flat(4.1, wobble=0.03, changes=rise(range(DAYS - 9, DAYS + 1), -0.4))
    score, finding = cardio_day("cm-x", DAYS, series(hr=hr, hrv=hrv), data, None)
    assert finding.level == 2 and finding.status == "alert" and finding.recommendation_id == "cardio-2-1"
    assert score.score < 75 and [e.metric_key for e in finding.evidence] == ["resting_pulse_bpm", "hrv_lnrmssd"]


def test_systolic_drop_beyond_threshold_costs_points(data):
    sbp = flat(110.0, wobble=1.0, changes=rise(range(DAYS - 9, DAYS + 1), -25.0))
    low, _ = cardio_day("cm-x", DAYS, series(sbp=sbp), data, None)
    normal, _ = cardio_day("cm-x", DAYS, series(), data, None)
    assert normal.score - low.score == pytest.approx(10, abs=0.5)


def test_not_ready_in_the_first_weeks(data):
    score, finding = landing_readiness([], [], [], {}, cardio_params(data))
    assert score.status == "unknown" and finding is None
    score, _ = cardio_day("cm-x", 20, series(), data, None)
    assert score.status == "unknown"


def test_scenario_cm2_is_ready_on_day_96_and_dips_after_110(data):
    days = generate(data.scenario, from_day=1, to_day=125)
    pts = {m: [] for m in ("resting_pulse_bpm", "hrv_lnrmssd", "systolic_mmhg")}
    for d in days:
        if d.crew_id == "cm-2":
            for k, v, _u, at in d.measurements:
                if k in pts:
                    pts[k].append(Point(d.day, at, v))
    on_96, f96 = cardio_day("cm-2", 96, pts, data, None)
    assert on_96.score >= 80 and f96 is None
    on_117, f117 = cardio_day("cm-2", 117, pts, data, None)
    assert on_117.score < on_96.score and f117 is not None and f117.level == 2


async def test_heart_pillar_on_the_dashboard(client):
    d = (await client.get("/api/v1/crew/cm-2/dashboard", headers=auth("specialist2"))).json()
    heart = next(p for p in d["pillars"] if p["pillar"] == "cardio")
    assert heart["status"] == "ok" and heart["score"] >= 80
    panel = (await client.get("/api/v1/crew/cm-2/pillars/cardio", headers=auth("specialist2"))).json()
    assert panel["chart"]["metric_key"] == "landing_readiness" and len(panel["chart"]["points"]) == 10
    assert panel["metrics"][0]["key"] == "landing_readiness" and panel["metrics"][0]["value"] >= 80
