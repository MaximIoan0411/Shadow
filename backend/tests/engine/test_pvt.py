import pytest

from app.engine.derived import PVT_MIN_SPEED_SD
from app.engine.pillars.behavioral import pvt_baseline, pvt_finding, pvt_summary
from tests.conftest import auth

URL = "/api/v1/crew/cm-2/pvt"


def trials(rts: list[float | None], false_starts: int = 0) -> list[dict]:
    out = [{"stimulus_at_ms": 1000 * i, "rt_ms": rt, "false_start": False} for i, rt in enumerate(rts)]
    return out + [{"stimulus_at_ms": 99000 + i, "rt_ms": None, "false_start": True} for i in range(false_starts)]


def test_lapse_at_exactly_355_ms():
    s = pvt_summary(trials([354.9, 355.0, 400.0]), lapse_ms=355)
    assert s["lapses"] == 2 and s["n_trials"] == 3


def test_no_answer_is_a_lapse_and_false_starts_are_not_reaction_times():
    s = pvt_summary(trials([250.0, None, 500.0], false_starts=2), lapse_ms=355)
    assert s["lapses"] == 2 and s["false_starts"] == 2 and s["n_trials"] == 5
    assert s["mean_rt_ms"] == 375.0
    assert s["mean_speed"] == pytest.approx((4 + 2) / 2)


def test_baseline_needs_two_tests_and_has_a_minimum_spread():
    assert pvt_baseline([4.0]) is None
    speed, sd = pvt_baseline([4.0, 4.0])
    assert speed == 4.0 and sd == PVT_MIN_SPEED_SD


def test_finding_only_past_reliable_change():
    assert pvt_finding("cm-2", 3.9, 4.0, 0.15, reliable_change_sd=1.24, day=96) is None
    f = pvt_finding("cm-2", 3.6, 4.0, 0.2, reliable_change_sd=1.24, day=96)
    assert f.level == 1 and f.status == "watch" and f.topic == "behavioral"
    assert f.recommendation_id == "behavioral-1-1" and f.extra["deviation_sd"] == -2.0
    assert f.title == "Reaction speed 10% below your baseline"


async def post(client, rts):
    body = {"started_at": "2027-04-15T09:00:00Z", "duration_s": 180, "trials": trials(rts)}
    r = await client.post(URL, headers=auth("specialist2"), json=body)
    assert r.status_code == 201
    return r.json()


async def test_practice_then_baseline_then_slow_test_is_watch(client):
    normal = [250.0, 260.0, 255.0, 245.0]
    results = [await post(client, normal) for _ in range(5)]
    # 3 practice tests, then 2 tests that build the baseline: none of the 5 is judged
    assert [r["status"] for r in results] == ["unknown"] * 5
    assert all(r["baseline_speed"] is None for r in results)
    again = await post(client, normal)
    assert again["status"] == "ok" and again["baseline_speed"] is not None

    slow = await post(client, [330.0, 340.0, 360.0, 380.0])
    assert slow["status"] == "watch" and slow["deviation_sd"] <= -1.24 and slow["lapses"] == 2

    history = (await client.get(URL, headers=auth("specialist2"))).json()
    assert [h["id"] for h in history][0] == slow["id"] and len(history) == 7

    alerts = (await client.get("/api/v1/crew/cm-2/alerts?topic=behavioral", headers=auth("specialist2"))).json()
    assert len(alerts) == 1 and alerts[0]["title"].startswith("Reaction speed")
