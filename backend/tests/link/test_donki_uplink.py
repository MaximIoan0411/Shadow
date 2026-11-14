from datetime import datetime, timedelta

import pytest

from app.clock import clock
from app.db import session as db
from app.link import scheduler
from app.services import radiation
from tests.conftest import auth

A, C, E = auth("specialist2"), auth("medic"), auth("earth")


@pytest.fixture
def frozen(client):
    t0 = clock.now()
    clock.freeze(t0)
    return t0


async def both_steps(client) -> list:
    data = client._transport.app.state.data
    async with db.SessionLocal() as s:
        events = await radiation.live_step(s, data)
        events += await scheduler.step(s, data)
        await s.commit()
    return events


async def test_lead_minutes_is_delay_plus_nasa_lag(client, frozen):
    await client.post("/api/v1/sim/sep/start", headers=C, json={"starts_in_min": 0})
    lag = radiation.earth_warning_lag(client._transport.app.state.data)
    assert lag == timedelta(minutes=20)

    minute = 0
    while True:
        clock.freeze(frozen + timedelta(minutes=minute))
        await both_steps(client)
        s = (await client.get("/api/v1/radiation/status", headers=A)).json()
        if s["earth_warning_arrived_at"]:
            break
        assert minute < 60, "the DONKI warning never arrived"
        minute += 1

    onboard = datetime.fromisoformat(s["onboard_alert_at"])
    arrived = datetime.fromisoformat(s["earth_warning_arrived_at"])
    assert arrived == frozen + lag + timedelta(seconds=700) or arrived - (
        frozen + lag + timedelta(seconds=700)
    ) < timedelta(minutes=1)
    assert s["lead_minutes"] > 0
    assert s["lead_minutes"] == pytest.approx((arrived - onboard).total_seconds() / 60, abs=0.1)
    assert s["lead_minutes"] == pytest.approx(20 + 700 / 60 - (onboard - frozen).total_seconds() / 60, abs=1.1)

    packets = (await client.get("/api/v1/link/packets?direction=up", headers=E)).json()
    assert [p["kind"] for p in packets] == ["donki_alert"] and packets[0]["status"] == "delivered"
    [msg] = (await client.get("/api/v1/crew/cm-1/messages", headers=auth("comandant"))).json()
    assert msg["kind"] == "donki_alert" and msg["donki_event_id"] == "2024-05-11T02:10:00-SEP-001"


async def test_warning_leaves_at_the_nasa_alert_time(client, frozen):
    await client.post("/api/v1/sim/sep/start", headers=C, json={"starts_in_min": 0})
    clock.freeze(frozen + timedelta(minutes=19))
    await both_steps(client)
    assert (await client.get("/api/v1/link/packets?direction=up", headers=E)).json() == []
    clock.freeze(frozen + timedelta(minutes=20))
    await both_steps(client)
    [p] = (await client.get("/api/v1/link/packets?direction=up", headers=E)).json()
    assert p["kind"] == "donki_alert" and p["status"] == "in_transit"
