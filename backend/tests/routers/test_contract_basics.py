"""Teste de bază pe contract. Rămân valabile și după ce mock-ul e înlocuit cu logica reală."""
from tests.conftest import auth


async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200 and r.json()["ok"] is True


async def test_each_account_sees_only_own_data(client):
    assert (await client.get("/api/v1/crew/cm-2/dashboard", headers=auth("specialist2"))).status_code == 200
    r = await client.get("/api/v1/crew/cm-2/dashboard", headers=auth("comandant"))
    assert r.status_code == 403 and r.json()["error"]["code"] == "forbidden"
    assert (await client.get("/api/v1/crew/cm-2/dashboard", headers=auth("medic"))).status_code == 200


async def test_timeline_stops_at_current_day(client):
    mission = (await client.get("/api/v1/mission", headers=auth("specialist2"))).json()
    tl = (await client.get("/api/v1/crew/cm-2/timeline", headers=auth("specialist2"))).json()
    assert tl["days"][-1]["day"] == mission["mission_day"]


async def test_future_as_of_day_is_rejected(client):
    r = await client.get("/api/v1/crew/cm-2/dashboard?as_of_day=139", headers=auth("specialist2"))
    assert r.status_code == 422


async def test_keystrokes_reject_characters(client):
    r = await client.post("/api/v1/crew/cm-2/keystrokes/batches", headers=auth("specialist2"), json={
        "session_id": "s", "context": "demo",
        "events": [{"t_down_ms": 1, "t_up_ms": 2, "key_class": "char", "key": "a"}]})
    assert r.status_code == 422
