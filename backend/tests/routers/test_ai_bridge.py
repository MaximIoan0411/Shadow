import json

import httpx
import pytest

from app.services import ai as ai_service
from tests.conftest import auth

A = auth("specialist2")


@pytest.fixture
def ai_down(monkeypatch):
    def refuse(request):
        raise httpx.ConnectError("connection refused", request=request)

    monkeypatch.setattr(ai_service, "transport", httpx.MockTransport(refuse))


@pytest.fixture
def ai_up(monkeypatch):
    seen = {}

    def answer(request: httpx.Request):
        if request.url.path == "/status":
            return httpx.Response(200, json={"ready": True, "model": "model-3b-Q4_K_M", "mode": "local"})
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "answer": "Your night pulse is higher than your normal. Tell the crew medical officer.",
                "citations": [{"title": "Alavi et al. (2022)", "url": "https://example.org/alavi", "snippet": "night"}],
                "recommendation_ids": ["immune-2-1"],
                "model": "model-3b-Q4_K_M",
                "latency_ms": 900,
            },
        )

    monkeypatch.setattr(ai_service, "transport", httpx.MockTransport(answer))
    return seen


async def immune_id(client) -> str:
    alerts = (await client.get("/api/v1/crew/cm-2/alerts", headers=A)).json()
    return next(a["id"] for a in alerts if a["topic"] == "immune")


async def test_ai_down_falls_back_to_the_catalog(client, ai_down):
    body = {"crew_id": "cm-2", "message": "Why is my night pulse up?", "alert_id": await immune_id(client)}
    r = await client.post("/api/v1/ai/chat", headers=A, json=body)
    assert r.status_code == 200
    answer = r.json()
    data = client._transport.app.state.data
    assert answer["fallback"] is True and answer["model"] == "catalog"
    assert answer["answer"] == data.catalog.by_id()["immune-2-1"].action
    assert answer["recommendation_ids"] == ["immune-2-1"] and answer["citations"][0]["url"]
    assert answer["disclaimer"] == "Decision-support prototype, not a medical device."
    status = (await client.get("/api/v1/ai/status", headers=A)).json()
    assert status == {"ready": False, "model": None, "mode": "fallback"}


async def test_ai_down_without_alert_still_answers(client, ai_down):
    r = await client.post("/api/v1/ai/chat", headers=A, json={"crew_id": "cm-2", "message": "Hello"})
    assert r.status_code == 200 and r.json()["fallback"] is True and r.json()["citations"] == []
    # the catalog's answer names the open alerts, instead of pretending there is nothing to say
    titles = [a["title"] for a in (await client.get("/api/v1/crew/cm-2/alerts", headers=A)).json()]
    assert titles and all(title in r.json()["answer"] for title in titles)


async def test_a_general_question_carries_the_open_alerts_and_the_zones(client, ai_up):
    r = await client.post("/api/v1/ai/chat", headers=A, json={"crew_id": "cm-2", "message": "How can I improve my health?"})
    assert r.status_code == 200
    context = ai_up["body"]["context"]
    mine = (await client.get("/api/v1/crew/cm-2/alerts", headers=A)).json()
    sent = context["open_alerts"]
    assert {a["title"] for a in sent} == {a["title"] for a in mine}
    assert [a["level"] for a in sent] == sorted((a["level"] for a in sent), reverse=True)   # most serious first
    data = client._transport.app.state.data
    assert all(a["action"] == data.catalog.by_id()[a["recommendation_id"]].action for a in sent)
    immune = next(a for a in sent if a["topic"] == "immune")
    assert immune["observed"] and immune["level"] == 2
    zones = context["zones"]
    assert len(zones) == 4 and any(z["status"] != "ok" for z in zones)
    assert context["topic"] is None and context["recommendation"] is None
    assert "cm-2" not in json.dumps(ai_up["body"]) and "Mission Specialist" not in json.dumps(ai_up["body"])


async def test_a_question_about_one_alert_does_not_carry_the_others(client, ai_up):
    body = {"crew_id": "cm-2", "message": "Why is my night pulse up?", "alert_id": await immune_id(client)}
    await client.post("/api/v1/ai/chat", headers=A, json=body)
    assert ai_up["body"]["context"]["open_alerts"] == [] and ai_up["body"]["context"]["zones"] == []


async def test_the_medical_officer_sees_a_colleagues_level_1_alerts_only_from_level_2(client, ai_up):
    await client.post("/api/v1/ai/chat", headers=auth("medic"), json={"crew_id": "cm-2", "message": "How is she doing?"})
    sent = ai_up["body"]["context"]["open_alerts"]
    assert sent and all(a["level"] >= 2 for a in sent)
    everything = (await client.get("/api/v1/crew/cm-2/alerts", headers=A)).json()
    assert any(a["level"] == 1 for a in everything)   # the colleague does have a level 1 alert, it is not sent


async def test_ai_up_answer_comes_from_the_service(client, ai_up):
    body = {"crew_id": "cm-2", "message": "Why is my night pulse up?", "alert_id": await immune_id(client)}
    answer = (await client.post("/api/v1/ai/chat", headers=A, json=body)).json()
    assert answer["fallback"] is False and answer["model"] == "model-3b-Q4_K_M"
    assert answer["citations"][0]["title"] == "Alavi et al. (2022)"
    context = ai_up["body"]["context"]
    assert context["topic"] == "immune" and context["level"] == 2 and context["recommendation"]["id"] == "immune-2-1"
    assert context["mission_day"] == 96 and context["environment"] == "mars_transit"
    assert "cm-2" not in json.dumps(ai_up["body"]) and "Mission Specialist" not in json.dumps(ai_up["body"])
    status = (await client.get("/api/v1/ai/status", headers=A)).json()
    assert status["ready"] is True and status["mode"] == "local"


async def test_astronaut_asks_only_about_themselves(client, ai_down):
    r = await client.post("/api/v1/ai/chat", headers=A, json={"crew_id": "cm-1", "message": "Hi"})
    assert r.status_code == 403


async def test_answer_replaced_by_the_guard_is_shown_as_catalog_text(client, monkeypatch):
    # the AI service's guard rejected the model's answer (a medicine, a dose) and sent the catalog text instead
    def answer(request: httpx.Request):
        return httpx.Response(
            200,
            json={
                "answer": "What was observed: night pulse up. What you can do now: notify the crew medical officer.",
                "citations": [],
                "recommendation_ids": ["immune-2-1"],
                "model": "catalog",
                "latency_ms": 900,
            },
        )

    monkeypatch.setattr(ai_service, "transport", httpx.MockTransport(answer))
    body = {"crew_id": "cm-2", "message": "Which pill should I take?", "alert_id": await immune_id(client)}
    reply = (await client.post("/api/v1/ai/chat", headers=A, json=body)).json()
    assert reply["fallback"] is True and reply["model"] == "catalog"
