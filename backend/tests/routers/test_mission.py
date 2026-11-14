from datetime import datetime, timedelta

import pytest

from app import deps
from app.clock import clock
from tests.conftest import auth

C = auth("medic")


async def mission(client) -> dict:
    r = await client.get("/api/v1/mission", headers=auth("specialist2"))
    assert r.status_code == 200
    return r.json()


async def test_mission_starts_on_day_96_in_default_environment(client):
    m = await mission(client)
    assert m["mission_day"] == 96 and m["total_days"] == 140 and m["name"] == "SHADOW-1"
    assert m["sim_now"].startswith("2027-04-15T07:0")
    assert m["environment"]["id"] == "mars_transit"
    assert m["link"]["environment"] == "mars_transit"
    assert m["link"]["one_way_delay_s"] == 700
    assert m["link"]["queued_down"] == 0 and m["link"]["queued_up"] == 0


async def test_environments_come_from_data(client):
    envs = (await client.get("/api/v1/environments", headers=C)).json()
    assert {e["id"] for e in envs} == {"iss", "moon_base", "mars_transit", "mars_base"}
    assert "sources" not in envs[0] and "delay_range_s" not in envs[0]


async def test_switch_to_iss_changes_delay_and_publishes(client):
    q = deps.subscribe()
    try:
        r = await client.put("/api/v1/mission/environment", json={"environment": "iss"}, headers=C)
        assert r.status_code == 200
        assert r.json()["link"]["one_way_delay_s"] == 1
        assert r.json()["environment"]["id"] == "iss"
        event = q.get_nowait()
        assert event["type"] == "environment.changed" and event["data"]["environment"]["id"] == "iss"
    finally:
        deps.unsubscribe(q)
    assert (await mission(client))["link"]["one_way_delay_s"] == 1


async def test_environment_change_forbidden_for_earth(client):
    r = await client.put("/api/v1/mission/environment", json={"environment": "iss"}, headers=auth("earth"))
    assert r.status_code == 403


async def test_time_scale_changes_without_jumping(client):
    before = datetime.fromisoformat((await mission(client))["sim_now"])
    r = await client.put("/api/v1/sim/clock", json={"time_scale": 600}, headers=C)
    assert r.status_code == 200
    body = r.json()
    assert body["time_scale"] == 600
    assert body["link"]["one_way_delay_real_s"] == pytest.approx(700 / 600, abs=0.01)
    after = datetime.fromisoformat(body["sim_now"])
    assert timedelta(0) <= after - before < timedelta(minutes=5)
    assert clock.scale == 600


async def test_clock_cannot_go_back(client):
    r = await client.put("/api/v1/sim/clock", json={"mission_day": 50}, headers=C)
    assert r.status_code == 409 and r.json()["error"]["code"] == "invalid_state"
    assert (await mission(client))["mission_day"] == 96


async def test_clock_cannot_pass_end_of_mission(client):
    r = await client.put("/api/v1/sim/clock", json={"mission_day": 141}, headers=C)
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"


async def test_clock_jumps_forward(client):
    r = await client.put("/api/v1/sim/clock", json={"mission_day": 100}, headers=C)
    assert r.status_code == 200
    assert r.json()["mission_day"] == 100
    assert r.json()["sim_now"].startswith("2027-04-19T07:0")
