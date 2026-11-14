import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db import session as db
from app.db.models.link import Packet
from tests.conftest import auth

A, C, E = auth("specialist2"), auth("medic"), auth("earth")


async def immune_id(client) -> str:
    alerts = (await client.get("/api/v1/crew/cm-2/alerts", headers=A)).json()
    return next(a["id"] for a in alerts if a["topic"] == "immune")


async def test_escalation_to_level_3_creates_a_sealed_packet(client):
    alert_id = await immune_id(client)
    r = await client.post(f"/api/v1/alerts/{alert_id}/escalate", headers=C, json={"to_level": 3, "note": "Night 3."})
    alert = r.json()
    assert alert["level"] == 3 and alert["packet_id"]
    assert [h["action"] for h in alert["history"]][-2:] == ["escalated", "packet_sent"]

    async with db.SessionLocal() as s:
        p = await s.get(Packet, alert["packet_id"])
    assert p.status == "queued" and p.seq == 1 and p.direction == "down" and p.kind == "alert_l3"
    assert p.payload is None and p.size_bytes == len(p.sealed)
    assert p.header["id"] == p.id and p.header["seq"] == 1 and p.header["key_id"] == "ship-2026-01"
    assert p.level == 3 and p.crew_id == "cm-2" and p.alert_id == alert_id
    assert p.title.startswith("Sentinel · Night pulse")


async def test_second_packet_has_seq_2(client):
    await client.post(f"/api/v1/alerts/{await immune_id(client)}/escalate", headers=C, json={"to_level": 3})
    r = await client.post("/api/v1/link/outbox", headers=A, json={"kind": "weekly_summary", "crew_id": "cm-2"})
    assert r.status_code == 201
    body = r.json()
    assert body["seq"] == 2 and body["status"] == "queued" and body["kind"] == "weekly_summary"
    assert body["progress"] == 0 and body["eta_real_s"] is None and body["title"] == "Weekly summary · week 14"


async def test_up_direction_has_its_own_seq(client):
    r = await client.post("/api/v1/earth/replies", headers=E, json={"crew_id": "cm-2", "body": "Rest, please."})
    assert r.status_code == 201 and r.json()["seq"] == 1 and r.json()["direction"] == "up"
    async with db.SessionLocal() as s:
        p = await s.get(Packet, r.json()["id"])
    assert p.header["key_id"] == "earth-2026-01" and p.payload is None


async def test_payload_hidden_until_delivered(client):
    r = await client.post(f"/api/v1/alerts/{await immune_id(client)}/escalate", headers=C, json={"to_level": 3})
    packet_id = r.json()["packet_id"]
    detail = (await client.get(f"/api/v1/link/packets/{packet_id}", headers=E)).json()
    assert detail["payload"] is None and detail["status"] == "queued"
    assert detail["crypto"]["key_id"] == "ship-2026-01" and detail["crypto"]["cipher"] == "AES-256-GCM"


async def test_list_newest_first_and_filters(client):
    await client.post(f"/api/v1/alerts/{await immune_id(client)}/escalate", headers=C, json={"to_level": 3})
    await client.post("/api/v1/link/outbox", headers=A, json={"kind": "weekly_summary", "crew_id": "cm-2"})
    await client.post("/api/v1/earth/replies", headers=E, json={"crew_id": "cm-2", "body": "OK"})
    down = (await client.get("/api/v1/link/packets?direction=down", headers=E)).json()
    assert [p["kind"] for p in down] == ["weekly_summary", "alert_l3"]
    assert len((await client.get("/api/v1/link/packets", headers=C)).json()) == 3
    status = (await client.get("/api/v1/link/status", headers=E)).json()
    assert status["queued_down"] == 2 and status["queued_up"] == 1


async def test_outbox_rules(client):
    assert (
        await client.post("/api/v1/link/outbox", headers=A, json={"kind": "weekly_summary", "crew_id": "cm-1"})
    ).status_code == 403
    r = await client.post("/api/v1/link/outbox", headers=C, json={"kind": "alert_l3", "crew_id": "cm-2"})
    assert r.status_code == 422
    r = await client.post(
        "/api/v1/link/outbox", headers=C, json={"kind": "alert_l3", "crew_id": "cm-2", "alert_id": "al-9999"}
    )
    assert r.status_code == 404
    assert (await client.get("/api/v1/link/packets", headers=A)).status_code == 403


async def test_only_the_medical_officer_sends_an_alert_to_earth(client):
    alert_id = await immune_id(client)
    again = {"kind": "alert_l3", "crew_id": "cm-2", "alert_id": alert_id}

    # the astronaut cannot get around POST /alerts/{id}/escalate, not even for their own alert
    assert (await client.post(f"/api/v1/alerts/{alert_id}/escalate", headers=A, json={"to_level": 3})).status_code == 403
    r = await client.post("/api/v1/link/outbox", headers=A, json=again)
    assert r.status_code == 403 and "crew medical officer" in r.json()["error"]["message"]

    # the outbox only sends an alert again: before the escalation there is nothing to send again
    r = await client.post("/api/v1/link/outbox", headers=C, json=again)
    assert r.status_code == 409 and r.json()["error"]["code"] == "invalid_state"
    assert (await client.get("/api/v1/link/packets", headers=C)).json() == []

    await client.post(f"/api/v1/alerts/{alert_id}/escalate", headers=C, json={"to_level": 3})
    assert (await client.post("/api/v1/link/outbox", headers=A, json=again)).status_code == 403
    r = await client.post("/api/v1/link/outbox", headers=C, json=again)
    assert r.status_code == 201 and r.json()["kind"] == "alert_l3" and r.json()["seq"] == 2


async def test_a_copied_packet_cannot_enter_the_queue_again(client):
    """Replay: the same (direction, seq) a second time. The number is also inside the signed header, so a copy
    cannot be given a new one without breaking the seal."""
    await client.post("/api/v1/link/outbox", headers=A, json={"kind": "weekly_summary", "crew_id": "cm-2"})
    async with db.SessionLocal() as s:
        [original] = (await s.scalars(select(Packet))).all()
        copy = {c.name: getattr(original, c.name) for c in Packet.__table__.columns}
        s.add(Packet(**{**copy, "id": "pk-9999"}))
        with pytest.raises(IntegrityError):
            await s.commit()
    assert len((await client.get("/api/v1/link/packets", headers=C)).json()) == 1


async def test_nothing_stored_in_clear(client):
    await client.post("/api/v1/earth/replies", headers=E, json={"crew_id": "cm-2", "body": "secret words"})
    async with db.SessionLocal() as s:
        rows = (await s.scalars(select(Packet))).all()
    assert all(p.payload is None for p in rows)
