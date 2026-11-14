from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.clock import clock
from app.db import session as db
from app.db.models.alerts import Alert
from app.engine.radiation import event_dose_msv, is_alert, mean_24h
from app.services import radiation
from app.simulator.radiation import dose_rate
from tests.conftest import auth

A, C = auth("specialist2"), auth("medic")
T0 = datetime(2027, 4, 15, 7, tzinfo=UTC)


def rate(t, onset=T0, sheltered=False):
    return dose_rate(
        t,
        baseline_usv_h=65.8,
        storm_onset=onset,
        peak_multiplier=6.0,
        sheltered=sheltered,
        shield_factor=0.3,
        rng_seed=1,
    )


def test_sep_alert_at_2x_mean():
    assert not is_alert([140.0, 150.0], 66.0, 2.0, 3)
    assert not is_alert([140.0, 120.0, 150.0], 66.0, 2.0, 3)
    assert is_alert([60.0, 132.0, 140.0, 150.0], 66.0, 2.0, 3)
    assert not is_alert([200.0, 200.0, 200.0], 0.0, 2.0, 3)


def test_mean_and_event_dose():
    assert mean_24h([60.0, 70.0]) == 65 and mean_24h([]) == 0
    assert event_dose_msv([(0.0, 1000.0), (1.0, 1000.0)]) == pytest.approx(1.0)


def test_dose_rate_shape():
    quiet = rate(T0 - timedelta(hours=1))
    assert 65.8 * 0.95 <= quiet <= 65.8 * 1.05
    assert rate(T0 + timedelta(minutes=20)) == pytest.approx(65.8 * 6, rel=0.06)
    assert rate(T0 + timedelta(hours=3)) < rate(T0 + timedelta(minutes=30))
    assert rate(T0 + timedelta(minutes=20), sheltered=True) == pytest.approx(
        rate(T0 + timedelta(minutes=20)) * 0.3, rel=0.01
    )
    assert rate(T0 + timedelta(minutes=5)) == rate(T0 + timedelta(minutes=5))  # same minute, same noise


@pytest.fixture
def frozen(client):
    t0 = clock.now()
    clock.freeze(t0)
    return t0


async def step(client) -> list:
    async with db.SessionLocal() as s:
        events = await radiation.live_step(s, client._transport.app.state.data)
        await s.commit()
    return events


async def test_quiet_background_is_seeded(client):
    s = (await client.get("/api/v1/radiation/status", headers=A)).json()
    assert 60 < s["mean_24h_usv_h"] < 72 and s["alert_active"] is False and s["event"] is None
    assert 0.9 < s["ratio"] < 1.1 and s["profile_is_synthetic"] is True
    series = (await client.get("/api/v1/radiation/series?hours=24&step_min=60", headers=A)).json()
    assert 23 <= len(series["points"]) <= 25 and series["unit"] == "µSv/h"


async def test_two_readings_above_threshold_no_alert_third_alerts(client, frozen):
    await client.post("/api/v1/sim/sep/start", headers=C, json={"starts_in_min": 0})
    above = 0
    minute = 0
    while above < 2:
        clock.freeze(frozen + timedelta(minutes=minute))
        events = await step(client)
        status = (await client.get("/api/v1/radiation/status", headers=A)).json()
        if status["dose_rate_usv_h"] >= 2 * status["mean_24h_usv_h"]:
            above += 1
        assert "radiation.alert" not in [e.type for e in events]
        minute += 2
    clock.freeze(frozen + timedelta(minutes=minute))
    events = await step(client)
    types = [e.type for e in events]
    assert "radiation.alert" in types and types.count("alert.created") == 4

    s = (await client.get("/api/v1/radiation/status", headers=A)).json()
    assert s["alert_active"] is True and s["onboard_alert_at"] and s["alert_id"]
    assert s["event"]["donki_id"] == "2024-05-11T02:10:00-SEP-001" and s["event_dose_msv"] > 0
    async with db.SessionLocal() as session:
        alerts = (await session.scalars(select(Alert).where(Alert.topic == "radiation"))).all()
    assert len(alerts) == 4 and {a.level for a in alerts} == {1} and alerts[0].recommendation_id == "radiation-1-1"
    mine = next(a for a in alerts if a.crew_id == "cm-2")
    assert s["alert_id"] == mine.id
    d = (await client.get("/api/v1/crew/cm-2/dashboard", headers=A)).json()
    assert d["radiation_alert_active"] is True


async def test_shelter_lowers_the_rate(client, frozen):
    await client.post("/api/v1/sim/sep/start", headers=C, json={"starts_in_min": 0})
    clock.freeze(frozen + timedelta(minutes=20))
    outside = (await client.get("/api/v1/radiation/status", headers=A)).json()["dose_rate_usv_h"]
    r = await client.post("/api/v1/radiation/shelter-ack", headers=A, json={"sheltered": True})
    inside = r.json()
    assert inside["sheltered"] is True and inside["sheltered_since"]
    assert inside["dose_rate_usv_h"] == pytest.approx(outside * 68 / 214, rel=0.01)
    await step(client)
    out = (await client.post("/api/v1/radiation/shelter-ack", headers=A, json={"sheltered": False})).json()
    assert out["sheltered"] is False and out["dose_rate_usv_h"] == pytest.approx(outside, rel=0.01)


async def test_stop_clears_the_storm(client, frozen):
    await client.post("/api/v1/sim/sep/start", headers=C, json={"starts_in_min": 5})
    assert (await client.get("/api/v1/radiation/status", headers=A)).json()["event"]["sim_onset_at"]
    r = await client.post("/api/v1/sim/sep/stop", headers=C)
    assert r.status_code == 200 and r.json()["event"] is None and r.json()["alert_active"] is False
    assert await step(client) == []


async def test_unknown_event_and_earth_access(client):
    r = await client.post("/api/v1/sim/sep/start", headers=C, json={"event_id": "nope"})
    assert r.status_code == 404
    assert (await client.get("/api/v1/radiation/status", headers=auth("earth"))).status_code == 403
    events = (await client.get("/api/v1/radiation/events", headers=auth("earth"))).json()
    assert events[0]["donki_id"] == "2024-05-11T02:10:00-SEP-001"
