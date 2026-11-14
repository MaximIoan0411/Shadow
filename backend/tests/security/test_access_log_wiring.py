import pytest

from app.security import access_log
from tests.conftest import auth


@pytest.fixture
def new_entries():
    start = len(access_log._entries)
    return lambda: access_log._entries[start:]


async def test_denied_read_is_logged(client, new_entries):
    r = await client.get("/api/v1/crew/cm-2/dashboard", headers=auth("comandant"))
    assert r.status_code == 403
    [e] = new_entries()
    assert (e.action, e.outcome, e.crew_id) == ("access_denied", "denied", "cm-2")
    assert e.actor == "Commander" and e.actor_role == "astronaut"
    assert e.resource == "crew/cm-2/dashboard"


async def test_cmo_reading_another_member_is_logged(client, new_entries):
    r = await client.get("/api/v1/crew/cm-2/dashboard", headers=auth("medic"))
    assert r.status_code == 200
    [e] = new_entries()
    assert (e.action, e.outcome, e.crew_id, e.actor_role) == ("read_dashboard", "allowed", "cm-2", "cmo")


async def test_astronaut_reading_own_data_is_not_logged(client, new_entries):
    assert (await client.get("/api/v1/crew/cm-2/dashboard", headers=auth("specialist2"))).status_code == 200
    assert new_entries() == []


async def test_earth_role_denied_is_logged(client, new_entries):
    assert (await client.get("/api/v1/crew/cm-2/dashboard", headers=auth("earth"))).status_code == 403
    [e] = new_entries()
    assert (e.action, e.actor_role, e.crew_id) == ("access_denied", "earth", "cm-2")


async def test_cmo_reading_alert_is_logged(client, new_entries):
    own = (await client.get("/api/v1/crew/cm-2/alerts", headers=auth("specialist2"))).json()
    alert_id = next(a["id"] for a in own if a["topic"] == "immune")
    assert (await client.get(f"/api/v1/alerts/{alert_id}", headers=auth("medic"))).status_code == 200
    [e] = new_entries()
    assert (e.action, e.resource, e.crew_id) == ("read_alert", f"alerts/{alert_id}", "cm-2")


async def test_no_secrets_in_log(client, new_entries):
    await client.post("/api/v1/auth/login", json={"username": "specialist2", "password": "cm2-shadow"})
    await client.get("/api/v1/crew/cm-2/dashboard", headers=auth("medic"))
    text = repr(new_entries())
    assert "cm2-shadow" not in text and "mock-" not in text and "Bearer" not in text


async def test_access_log_endpoint_newest_first_and_filtered(client):
    await client.get("/api/v1/crew/cm-2/dashboard", headers=auth("medic"))
    await client.get("/api/v1/crew/cm-2/dashboard", headers=auth("comandant"))

    mine = (await client.get("/api/v1/access-log", headers=auth("specialist2"))).json()
    assert mine and all(e["crew_id"] == "cm-2" for e in mine)
    assert [e["id"] for e in mine] == sorted((e["id"] for e in mine), reverse=True)
    assert mine[0]["action"] == "access_denied"

    ignored = (await client.get("/api/v1/access-log?crew_id=cm-1", headers=auth("specialist2"))).json()
    assert all(e["crew_id"] == "cm-2" for e in ignored)

    everything = (await client.get("/api/v1/access-log?limit=500", headers=auth("medic"))).json()
    assert {e["crew_id"] for e in everything} >= {"cm-2"}
    assert len((await client.get("/api/v1/access-log?limit=1", headers=auth("medic"))).json()) == 1


async def test_access_log_endpoint_forbidden_for_earth(client):
    assert (await client.get("/api/v1/access-log", headers=auth("earth"))).status_code == 403
