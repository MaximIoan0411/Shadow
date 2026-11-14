import pytest
from sqlalchemy import select

from app import deps
from app.db import session as db
from app.db.models.alerts import Alert as AlertRow
from tests.conftest import auth

A = auth("specialist2")
C = auth("medic")


async def immune_id(client) -> str:
    alerts = (await client.get("/api/v1/crew/cm-2/alerts", headers=A)).json()
    return next(a["id"] for a in alerts if a["topic"] == "immune")


async def typing_alert_id(client) -> str:
    """cm-2's level 1 typing alert, produced by the engine at startup (day 95 of the scenario)."""
    alerts = (await client.get("/api/v1/crew/cm-2/alerts", headers=A)).json()
    return next(a["id"] for a in alerts if a["topic"] == "behavioral")


@pytest.fixture
def events():
    q = deps.subscribe()
    yield lambda: [q.get_nowait() for _ in range(q.qsize())]
    deps.unsubscribe(q)


async def test_list_and_detail_come_from_database(client):
    alerts = (await client.get("/api/v1/crew/cm-2/alerts", headers=A)).json()
    assert [(a["topic"], a["level"]) for a in alerts] == [("immune", 2), ("behavioral", 1)]
    alert_id = alerts[0]["id"]
    detail = (await client.get(f"/api/v1/alerts/{alert_id}", headers=A)).json()
    assert detail["level"] == 2 and detail["state"] == "escalated"
    assert detail["recommendation"]["id"] == "immune-2-1"
    assert detail["plan_steps"][0]["id"] == "st-1"
    assert [h["action"] for h in detail["history"]] == ["created", "escalated"]
    assert detail["evidence"][0]["metric_key"] == "night_pulse_bpm"


async def test_cmo_queue_and_level_filter(client):
    low = await typing_alert_id(client)
    queue = (await client.get("/api/v1/cmo/queue", headers=C)).json()
    assert [a["topic"] for a in queue] == ["immune"]
    mine = (await client.get("/api/v1/crew/cm-2/alerts", headers=A)).json()
    assert [a["level"] for a in mine] == [2, 1]
    cmo_view = (await client.get("/api/v1/crew/cm-2/alerts", headers=C)).json()
    assert low not in [a["id"] for a in cmo_view]
    assert (await client.get(f"/api/v1/alerts/{low}", headers=C)).status_code == 403
    filtered = (await client.get("/api/v1/crew/cm-2/alerts?topic=behavioral", headers=A)).json()
    assert [a["id"] for a in filtered] == [low]


async def test_full_flow_ack_step_escalate_resolve(client, events):
    alert_id = await typing_alert_id(client)

    r = await client.post(f"/api/v1/alerts/{alert_id}/ack", headers=A)
    assert r.status_code == 200 and r.json()["state"] == "acknowledged"
    assert (await client.post(f"/api/v1/alerts/{alert_id}/ack", headers=A)).status_code == 409

    r = await client.put(f"/api/v1/alerts/{alert_id}/plan/steps/st-1", headers=A, json={"done": True})
    assert r.status_code == 200 and r.json()["plan_steps"][0]["done"] is True
    assert r.json()["plan_steps"][0]["done_at"] is not None

    r = await client.post(f"/api/v1/alerts/{alert_id}/escalate", headers=A, json={"to_level": 2, "note": "Worse."})
    assert r.status_code == 200 and r.json()["level"] == 2 and r.json()["state"] == "escalated"

    assert (
        await client.post(f"/api/v1/alerts/{alert_id}/escalate", headers=A, json={"to_level": 3})
    ).status_code == 403
    r = await client.post(f"/api/v1/alerts/{alert_id}/escalate", headers=C, json={"to_level": 3})
    assert r.status_code == 200 and r.json()["level"] == 3

    assert (
        await client.post(f"/api/v1/alerts/{alert_id}/resolve", headers=A, json={"outcome": "resolved"})
    ).status_code == 403
    r = await client.post(f"/api/v1/alerts/{alert_id}/resolve", headers=C, json={"outcome": "resolved", "note": "OK"})
    assert r.status_code == 200 and r.json()["state"] == "resolved"

    history = [(h["action"], h["actor"]) for h in r.json()["history"]]
    assert history == [
        ("created", "SHADOW"),
        ("acknowledged", "Mission Specialist 2"),
        ("step_done", "Mission Specialist 2"),
        ("escalated", "Mission Specialist 2"),
        ("escalated", "Crew Medical Officer"),
        ("packet_sent", "Crew Medical Officer"),
        ("resolved", "Crew Medical Officer"),
    ]
    assert r.json()["packet_id"]
    published = events()
    assert len(published) == 5 and {e["type"] for e in published} == {"alert.updated"}
    assert all(e["crew_id"] == "cm-2" for e in published)
    assert alert_id not in [a["id"] for a in (await client.get("/api/v1/crew/cm-2/alerts", headers=A)).json()]


async def test_level_cannot_go_down(client):
    alert_id = await immune_id(client)
    r = await client.post(f"/api/v1/alerts/{alert_id}/escalate", headers=A, json={"to_level": 2})
    assert r.status_code == 409 and r.json()["error"]["code"] == "invalid_state"


async def test_ack_on_escalated_alert_is_409(client):
    r = await client.post(f"/api/v1/alerts/{await immune_id(client)}/ack", headers=A)
    assert r.status_code == 409


async def test_monitoring_moves_recheck_by_one_day(client):
    alert_id = await immune_id(client)
    before = (await client.get(f"/api/v1/alerts/{alert_id}", headers=C)).json()["recheck_at"]
    r = await client.post(f"/api/v1/alerts/{alert_id}/resolve", headers=C, json={"outcome": "monitoring"})
    body = r.json()
    assert r.status_code == 200 and body["state"] == "escalated"
    assert body["recheck_at"] > before and body["history"][-1]["action"] == "rechecked"


async def test_other_crew_and_unknown_alert(client):
    alert_id = await immune_id(client)
    assert (await client.get(f"/api/v1/alerts/{alert_id}", headers=auth("comandant"))).status_code == 403
    assert (await client.get(f"/api/v1/alerts/{alert_id}", headers=auth("earth"))).status_code == 403
    r = await client.get("/api/v1/alerts/al-9999", headers=A)
    assert r.status_code == 404 and r.json()["error"]["code"] == "not_found"
    step = await client.put(f"/api/v1/alerts/{alert_id}/plan/steps/st-99", headers=A, json={"done": True})
    assert step.status_code == 404


async def test_catalog_comes_from_data(client):
    data = client._transport.app.state.data
    all_immune = (await client.get("/api/v1/catalog/recommendations?topic=immune", headers=A)).json()
    assert {r["id"] for r in all_immune} == {r.id for r in data.catalog.recommendations if r.topic.value == "immune"}
    assert "steps" not in all_immune[0]
    one = await client.get("/api/v1/catalog/recommendations/immune-2-1", headers=auth("earth"))
    assert one.status_code == 200 and one.json()["level"] == 2
    assert (await client.get("/api/v1/catalog/recommendations/nope-1-1", headers=A)).status_code == 404


async def test_actions_are_saved(client):
    alert_id = await typing_alert_id(client)
    await client.post(f"/api/v1/alerts/{alert_id}/ack", headers=A)
    async with db.SessionLocal() as s:
        row = await s.scalar(select(AlertRow).where(AlertRow.id == alert_id))
    assert row.state == "acknowledged"
