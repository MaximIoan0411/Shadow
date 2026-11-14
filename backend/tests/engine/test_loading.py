import pytest

from app.datafiles import load_all
from app.engine.derived import LOADING_TARGET
from app.engine.pillars import musculoskeletal as m
from app.simulator.scenario import generate
from tests.conftest import auth

NORMAL = [{"exercise": "ARED squat", "reps": 10, "load_kg": 80.0}] * 3
A = auth("specialist2")


def test_session_score_has_diminishing_returns():
    assert m.session_score(NORMAL) == pytest.approx(33.3, abs=0.1)
    five = m.session_score([{"exercise": "x", "reps": 5, "load_kg": 80.0}])
    ten = m.session_score([{"exercise": "x", "reps": 10, "load_kg": 80.0}])
    assert ten == pytest.approx(five * 1.5, abs=0.1)
    assert m.session_score([]) == 0


def test_second_session_7_hours_later_gets_the_bonus():
    one = m.session_score(NORMAL)
    assert m.daily_loading([(9, one)]) == pytest.approx(one, abs=0.1)
    assert m.daily_loading([(9, one), (16, one)]) == pytest.approx(2 * one * 1.2, abs=0.1)
    assert m.daily_loading([(9, one), (11, one)]) == pytest.approx(2 * one, abs=0.1)
    assert m.daily_loading([(9, one), (16, one)]) == pytest.approx(LOADING_TARGET, abs=0.2)


def test_split_recommended_on_the_skipped_day_61():
    days = generate(load_all().scenario, from_day=61, to_day=61)
    cm2 = next(d for d in days if d.crew_id == "cm-2")
    assert cm2.exercise == [] and m.split_recommended(len(cm2.exercise))
    assert not m.split_recommended(2)


def test_projection_is_an_estimate_between_ared_and_pre_ared():
    params = load_all().params.value("projected_bmd_loss_model")
    full, full_split = m.projection(1.0, False, params)
    none, _ = m.projection(0.0, False, params)
    assert full == params["rata_cu_ARED_sold_total"] and none == params["rata_pre_ARED_trohanter_max"]
    assert full_split > full  # the split plan loses less (a smaller negative number)
    assert m.projection(1.0, True, params)[0] == full_split
    assert "animals" in m.PROJECTION_NOTE


def test_score():
    assert m.score(80, 80).status == "ok" and m.score(80, 80).score == 100
    assert m.score(30, 80).status == "watch"


async def test_today_and_logging_a_session(client):
    today = (await client.get("/api/v1/crew/cm-2/exercise/today", headers=A)).json()
    assert today["completed_sessions"] == 0 and today["split_recommended"] is True
    assert today["loading_target"] == 80 and today["streak"]["key"] == "split_training"
    assert today["projection"]["current_plan_pct_month"] < 0 and "animals" in today["projection"]["note"]

    body = {"kind": "resistance", "started_at": "2027-04-15T09:00:00Z", "duration_min": 40, "sets": NORMAL}
    r = await client.post("/api/v1/crew/cm-2/exercise/sessions", headers=A, json=body)
    assert (
        r.status_code == 201
        and r.json()["source"] == "manual"
        and r.json()["loading_score"] == pytest.approx(33.3, abs=0.1)
    )
    second = {**body, "started_at": "2027-04-15T16:00:00Z"}
    await client.post("/api/v1/crew/cm-2/exercise/sessions", headers=A, json=second)
    today = (await client.get("/api/v1/crew/cm-2/exercise/today", headers=A)).json()
    assert today["completed_sessions"] == 2 and today["split_recommended"] is False
    assert today["loading_score"] == pytest.approx(80, abs=0.2)
    history = (await client.get("/api/v1/crew/cm-2/exercise/sessions?from_day=95", headers=A)).json()
    assert history[0]["started_at"].startswith("2027-04-15T16") and len(history) == 4


async def test_history_has_loading_scores_and_the_dashboard_uses_them(client):
    sessions = (await client.get("/api/v1/crew/cm-2/exercise/sessions?from_day=60&to_day=62", headers=A)).json()
    assert {s["mission_day"] for s in sessions} == {60} and all(s["loading_score"] > 30 for s in sessions)
    d = (await client.get("/api/v1/crew/cm-2/dashboard", headers=A)).json()
    bones = next(p for p in d["pillars"] if p["pillar"] == "musculoskeletal")
    assert bones["status"] == "ok" and bones["score"] >= 90  # yesterday: 2 sessions, 7 h apart
    panel = (await client.get("/api/v1/crew/cm-2/pillars/musculoskeletal", headers=A)).json()
    assert panel["chart"]["metric_key"] == "loading_score"
    d61 = (await client.get("/api/v1/crew/cm-2/dashboard?as_of_day=62", headers=A)).json()
    assert next(p for p in d61["pillars"] if p["pillar"] == "musculoskeletal")["status"] == "watch"
