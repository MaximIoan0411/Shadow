from datetime import timedelta

import pytest

from app.clock import clock
from app.db import session as db
from app.db.models.link import Packet
from app.link import scheduler
from app.services.events import publish_all
from tests.conftest import auth

A, C, E = auth("specialist2"), auth("medic"), auth("earth")


@pytest.fixture
def frozen(client):
    t0 = clock.now()
    clock.freeze(t0)
    return t0


async def run_step(client) -> list:
    async with db.SessionLocal() as s:
        events = await scheduler.step(s, client._transport.app.state.data)
        await s.commit()
    publish_all(events)
    return events


async def escalate(client) -> str:
    alerts = (await client.get("/api/v1/crew/cm-2/alerts", headers=A)).json()
    alert_id = next(a["id"] for a in alerts if a["topic"] == "immune")
    r = await client.post(f"/api/v1/alerts/{alert_id}/escalate", headers=C, json={"to_level": 3})
    return r.json()["packet_id"]


async def test_packet_arrives_after_exactly_the_delay(client, frozen):
    packet_id = await escalate(client)
    sent = await run_step(client)
    assert [(e.type, e.data["id"]) for e in sent] == [("packet.sent", packet_id)]
    p = (await client.get(f"/api/v1/link/packets/{packet_id}", headers=E)).json()
    assert p["status"] == "in_transit" and p["eta_real_s"] == 700
    assert p["arrives_at"] == (frozen + timedelta(seconds=700)).isoformat().replace("+00:00", "Z")

    clock.freeze(frozen + timedelta(seconds=699))
    assert await run_step(client) == []
    clock.freeze(frozen + timedelta(seconds=700))
    arrived = await run_step(client)
    assert [e.type for e in arrived] == ["packet.arrived"] and arrived[0].crew_id == "cm-2"

    detail = (await client.get(f"/api/v1/link/packets/{packet_id}", headers=E)).json()
    assert detail["status"] == "delivered" and detail["signature_valid"] is True and detail["progress"] == 1
    assert detail["payload"]["alert"]["id"] and detail["payload"]["alert"]["level"] == 3
    hidden = (await client.get(f"/api/v1/link/packets/{packet_id}", headers=C)).json()
    assert hidden["payload"] is not None  # the cmo sent it


async def test_tampered_header_is_rejected(client, frozen):
    packet_id = await escalate(client)
    async with db.SessionLocal() as s:
        p = await s.get(Packet, packet_id)
        p.header = {**p.header, "kind": "weekly_summary"}
        await s.commit()
    await run_step(client)
    clock.freeze(frozen + timedelta(seconds=700))
    events = await run_step(client)
    assert [e.type for e in events] == ["packet.rejected"]
    detail = (await client.get(f"/api/v1/link/packets/{packet_id}", headers=E)).json()
    assert detail["status"] == "rejected" and detail["signature_valid"] is False
    assert detail["reject_reason"] == "bad_signature" and detail["payload"] is None


async def test_earth_reply_reaches_the_astronaut_after_the_second_delay(client, frozen):
    packet_id = await escalate(client)
    await run_step(client)
    clock.freeze(frozen + timedelta(seconds=700))
    await run_step(client)

    alerts = (await client.get("/api/v1/crew/cm-2/alerts", headers=A)).json()
    alert_id = next(a["id"] for a in alerts if a["topic"] == "immune")
    r = await client.post(
        "/api/v1/earth/replies",
        headers=E,
        json={
            "in_reply_to": packet_id,
            "crew_id": "cm-2",
            "alert_id": alert_id,
            "body": "Rest and measure twice a day.",
        },
    )
    reply_id = r.json()["id"]
    await run_step(client)
    assert (await client.get("/api/v1/crew/cm-2/messages", headers=A)).json() == []

    clock.freeze(frozen + timedelta(seconds=1400))
    events = await run_step(client)
    assert [e.type for e in events] == ["packet.arrived", "alert.updated"]
    [msg] = (await client.get("/api/v1/crew/cm-2/messages", headers=A)).json()
    assert (
        msg["packet_id"] == reply_id and msg["body"] == "Rest and measure twice a day." and msg["kind"] == "earth_reply"
    )
    alert = (await client.get(f"/api/v1/alerts/{alert_id}", headers=A)).json()
    assert alert["earth_reply"] == "Rest and measure twice a day."
    assert alert["history"][-1]["action"] == "earth_replied" and alert["history"][-1]["role"] == "earth"
    assert (await client.get("/api/v1/crew/cm-1/messages", headers=auth("comandant"))).json() == []


async def test_environment_change_keeps_arrival_of_packets_in_transit(client, frozen):
    packet_id = await escalate(client)
    await run_step(client)
    await client.put("/api/v1/mission/environment", headers=C, json={"environment": "iss"})
    r = await client.post("/api/v1/link/outbox", headers=A, json={"kind": "weekly_summary", "crew_id": "cm-2"})
    await run_step(client)
    old = (await client.get(f"/api/v1/link/packets/{packet_id}", headers=E)).json()
    new = (await client.get(f"/api/v1/link/packets/{r.json()['id']}", headers=E)).json()
    assert old["eta_real_s"] == 700 and new["eta_real_s"] == 1


async def test_scheduler_loop_survives_an_error(client, monkeypatch):
    calls = {"n": 0}

    async def broken(session, data):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("boom")
        raise SystemExit  # stops the loop on the second step

    monkeypatch.setattr(scheduler, "step", broken)
    monkeypatch.setattr(scheduler, "STEP_S", 0)
    with pytest.raises(SystemExit):
        await scheduler.link_scheduler(client._transport.app.state.data)
    assert calls["n"] == 2
