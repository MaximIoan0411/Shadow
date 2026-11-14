from sqlalchemy import String, Text, select
from sqlalchemy.orm import selectinload

from app import deps
from app.db import session as db
from app.db.models.alerts import Alert
from app.db.models.measurements import KeystrokeSession
from tests.conftest import auth

A = auth("specialist2")
URL = "/api/v1/crew/{}/keystrokes/batches"


def keys(n: int, *, flight: float = 280.0, hold: float = 96.0, start: float = 1000.0) -> list[dict]:
    return [
        {"t_down_ms": start + i * flight, "t_up_ms": start + i * flight + hold, "key_class": "char"} for i in range(n)
    ]


async def post(client, crew_id: str, username: str, session_id: str, events: list[dict], context="free_typing"):
    body = {"session_id": session_id, "context": context, "events": events}
    return await client.post(URL.format(crew_id), headers=auth(username), json=body)


async def behavioral_alerts() -> list[Alert]:
    """The open typing alerts (the history also has the resolved crew-wide sleep alerts of day 40, T29)."""
    stmt = (
        select(Alert).where(Alert.topic == "behavioral", Alert.state != "resolved").options(selectinload(Alert.history))
    )
    async with db.SessionLocal() as s:
        return list((await s.scalars(stmt)).all())


async def test_replay_creates_cm2_typing_alert_on_day_95(client):
    [alert] = await behavioral_alerts()
    assert alert.crew_id == "cm-2" and alert.mission_day == 95
    assert alert.level == 1 and alert.status == "watch" and alert.state == "active"
    assert alert.title == "Typing 18% slower than usual"
    assert alert.recommendation_id == "behavioral-1-1"
    assert [h.action for h in alert.history] == ["created"]
    async with db.SessionLocal() as s:
        typed = await s.get(KeystrokeSession, "sim-cm-2-d095")
    assert alert.created_at == typed.updated_at and alert.created_at.hour == 7
    assert [e["metric_key"] for e in alert.evidence] == ["keys_per_min", "hold_ms_mean"]


async def test_history_sessions_are_judged_except_the_baseline(client):
    async with db.SessionLocal() as s:
        rows = (await s.scalars(select(KeystrokeSession).where(KeystrokeSession.crew_id == "cm-2"))).all()
    by_day = {r.mission_day: r for r in rows}
    assert all(by_day[d].status == "unknown" and by_day[d].fatigue_index is None for d in range(1, 8))
    assert by_day[50].status == "ok" and by_day[50].fatigue_index < 15
    assert by_day[95].status == "watch" and 65 <= by_day[95].fatigue_index < 75


async def test_batches_accumulate_and_short_sessions_are_not_judged(client):
    first = (await post(client, "cm-2", "specialist2", "s-live-1", keys(10))).json()
    assert first["features"]["n_keys"] == 10 and first["status"] == "unknown" and first["fatigue_index"] is None
    assert first["baseline_ready"] is True and first["baseline_sessions"] == 7
    assert first["baseline"]["keys_per_min"] > 200 and first["baseline"]["n_keys"] > 2000
    second = (await post(client, "cm-2", "specialist2", "s-live-1", keys(30, start=1000 + 10 * 280))).json()
    assert second["features"]["n_keys"] == 40
    assert second["features"]["flight_ms_mean"] == 280 and second["features"]["hold_ms_mean"] == 96
    assert second["status"] == "ok" and second["fatigue_index"] < 15
    assert set(second["deviation_z"]) == {"hold_ms_mean", "keys_per_min", "flight_ms_mean", "backspace_rate"}


async def test_slow_session_creates_alert_and_events_once(client):
    q = deps.subscribe()
    try:
        r = await post(client, "cm-1", "comandant", "s-slow", keys(40, flight=400, hold=130))
        first_events = [q.get_nowait() for _ in range(q.qsize())]
        again = await post(client, "cm-1", "comandant", "s-slow", keys(20, flight=400, hold=130, start=1000 + 40 * 400))
        later_events = [q.get_nowait() for _ in range(q.qsize())]
    finally:
        deps.unsubscribe(q)
    assert r.status_code == 200 and r.json()["status"] == "alert" and r.json()["fatigue_index"] == 100
    assert [e["type"] for e in first_events] == ["alert.created", "dashboard.changed"]
    assert first_events[0]["crew_id"] == "cm-1" and first_events[0]["data"]["level"] == 1
    assert first_events[1]["data"] == {"reason": "keystrokes"}
    assert again.json()["status"] == "alert" and later_events == []
    mine = [a for a in await behavioral_alerts() if a.crew_id == "cm-1"]
    assert len(mine) == 1 and mine[0].title == "Typing 34% slower than usual" and mine[0].status == "alert"


async def test_slow_session_updates_the_open_alert(client):
    r = await post(client, "cm-2", "specialist2", "s-slow-2", keys(40, flight=420, hold=120))
    assert r.json()["status"] == "alert"
    [alert] = [a for a in await behavioral_alerts() if a.crew_id == "cm-2"]
    assert alert.mission_day == 95 and alert.level == 1 and alert.status == "alert"
    assert alert.title == "Typing 32% slower than usual"


async def test_session_of_another_account_is_refused(client):
    assert (await post(client, "cm-2", "specialist2", "s-shared", keys(5))).status_code == 200
    r = await post(client, "cm-1", "comandant", "s-shared", keys(5))
    assert r.status_code == 403 and r.json()["error"]["code"] == "forbidden"
    assert (await post(client, "cm-2", "comandant", "s-other", keys(5))).status_code == 403


async def test_characters_and_long_ids_are_rejected(client):
    with_char = [{**keys(1)[0], "key": "a"}]
    assert (await post(client, "cm-2", "specialist2", "s-char", with_char)).status_code == 422
    r = await post(client, "cm-2", "specialist2", "x" * 65, keys(3))
    assert r.status_code == 422 and r.json()["error"]["details"]["fields"][0]["field"] == "session_id"


async def test_summary(client):
    await post(client, "cm-2", "specialist2", "s-now", keys(40))
    r = (await client.get("/api/v1/crew/cm-2/keystrokes/summary?last=6", headers=A)).json()
    assert r["baseline_ready"] is True and r["baseline"]["keys_per_min"] > 200
    assert r["current"]["n_keys"] == 40 and r["status"] == "ok"
    assert len(r["sessions"]) == 6 and r["sessions"][-1]["session_id"] == "s-now"
    assert r["sessions"][-2]["session_id"] == "sim-cm-2-d095" and r["sessions"][-2]["status"] == "watch"
    assert [s["at"] for s in r["sessions"]] == sorted(s["at"] for s in r["sessions"])


def test_database_holds_no_typed_text():
    text_columns = {c.name for c in KeystrokeSession.__table__.columns if isinstance(c.type, String | Text)}
    assert text_columns == {"session_id", "crew_id", "context", "status"}
