import time

from tests.conftest import auth

A = auth("specialist2")
C = auth("medic")


def zones(dashboard: dict) -> dict:
    return {p["pillar"]: p["status"] for p in dashboard["pillars"]}


async def test_cm2_dashboard_now(client):
    r = await client.get("/api/v1/crew/cm-2/dashboard", headers=A)
    assert r.status_code == 200
    d = r.json()
    assert [p["pillar"] for p in d["pillars"]] == ["behavioral", "cardio", "immune", "musculoskeletal"]
    assert zones(d)["immune"] == "alert" and zones(d)["behavioral"] == "watch"
    assert d["overall_status"] == "alert" and d["mission_day"] == 96
    assert d["alerts_active_count"] == 2 and d["top_alert"]["topic"] == "immune"
    immune = next(p for p in d["pillars"] if p["pillar"] == "immune")
    assert immune["active_alert_id"] == d["top_alert"]["id"] and immune["name"] == "Sentinel"
    assert d["checkin_done_today"] is False and d["perception_gap"]["status"] == "unknown"
    assert [s["key"] for s in d["streaks"]] == ["checkin", "split_training", "pvt"]
    assert d["streaks"][0]["days"] == 95
    assert [(r["kind"], r["done"]) for r in d["reminders"]] == [("checkin", False), ("pvt", False), ("exercise", False)]


async def test_checkin_updates_dashboard(client):
    await client.post("/api/v1/crew/cm-2/checkins", headers=A, json={"mood": 4, "sleep_hours": 5.5})
    d = (await client.get("/api/v1/crew/cm-2/dashboard", headers=A)).json()
    assert d["checkin_done_today"] is True and d["reminders"][0]["done"] is True
    assert d["perception_gap"]["status"] == "alert" and d["perception_gap"]["gap"] >= 25


async def test_cm1_all_ok(client):
    d = (await client.get("/api/v1/crew/cm-1/dashboard", headers=auth("comandant"))).json()
    assert set(zones(d).values()) == {"ok"} and d["alerts_active_count"] == 0 and d["top_alert"] is None


async def test_as_of_day_93_sentinel_ok(client):
    d = (await client.get("/api/v1/crew/cm-2/dashboard?as_of_day=93", headers=A)).json()
    assert d["mission_day"] == 93 and zones(d)["immune"] == "ok" and d["alerts_active_count"] == 0
    d95 = (await client.get("/api/v1/crew/cm-2/dashboard?as_of_day=95", headers=A)).json()
    assert zones(d95)["immune"] == "alert" and zones(d95)["behavioral"] == "watch"


async def test_future_day_is_422(client):
    r = await client.get("/api/v1/crew/cm-2/dashboard?as_of_day=97", headers=A)
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"


async def test_dashboard_is_fast(client):
    await client.get("/api/v1/crew/cm-2/dashboard", headers=A)
    started = time.perf_counter()
    await client.get("/api/v1/crew/cm-2/dashboard", headers=A)
    assert time.perf_counter() - started < 0.4


async def test_immune_panel(client):
    p = (await client.get("/api/v1/crew/cm-2/pillars/immune", headers=A)).json()
    assert p["status"] == "alert" and p["active_alert_id"] and p["plan_steps"]
    assert [m["key"] for m in p["metrics"]] == ["night_pulse_bpm", "temperature_c", "sleep_hours", "stress_index"]
    night = p["metrics"][0]
    assert night["deviation_abs"] > 5 and night["status"] == "alert" and night["source"] == "simulated"
    chart = p["chart"]
    assert chart["metric_key"] == "night_pulse_bpm" and [pt["day"] for pt in chart["points"]] == list(range(87, 97))
    assert 53 < chart["baseline"] < 55 and chart["threshold"] == chart["baseline"] + 4
    assert chart["band_low"] < chart["baseline"] < chart["band_high"]
    assert p["sources"] and p["function_text"] and p["data_is_simulated"] is True


async def test_behavioral_and_placeholder_panels(client):
    b = (await client.get("/api/v1/crew/cm-2/pillars/behavioral", headers=A)).json()
    assert b["status"] == "watch" and b["chart"]["metric_key"] == "keys_per_min"
    assert b["metrics"][0]["value"] < b["metrics"][0]["baseline"]
    heart = (await client.get("/api/v1/crew/cm-2/pillars/cardio", headers=A)).json()
    assert heart["data_is_simulated"] is True and heart["plan_steps"] == [] and heart["chart"]["points"]


async def test_series(client):
    s = (
        await client.get("/api/v1/crew/cm-2/pillars/immune/series?metric=night_pulse_bpm&from_day=87", headers=A)
    ).json()
    assert [p["day"] for p in s["points"]] == list(range(87, 97))
    assert [p["status"] for p in s["points"]][-3:] == ["alert", "alert", "alert"]
    r = await client.get("/api/v1/crew/cm-2/pillars/immune/series?metric=keys_per_min", headers=A)
    assert r.status_code == 404


async def test_timeline(client):
    t = (await client.get("/api/v1/crew/cm-2/timeline", headers=A)).json()
    assert len(t["days"]) == 96 and t["days"][-1]["day"] == 96
    by_day = {d["day"]: d for d in t["days"]}
    assert by_day[93]["pillars"]["immune"] == "ok"
    assert by_day[94]["pillars"]["immune"] == "watch" and by_day[95]["pillars"]["immune"] == "alert"
    assert by_day[95]["pillars"]["behavioral"] == "watch" and by_day[50]["overall_status"] == "ok"
    assert "Sentinel alert" in by_day[94]["events"] and "Sentinel alert escalated" in by_day[95]["events"]


async def test_crew_list_for_cmo(client):
    rows = (await client.get("/api/v1/crew", headers=C)).json()
    by_id = {r["member"]["id"]: r for r in rows}
    assert by_id["cm-2"]["overall_status"] == "alert" and by_id["cm-2"]["active_alerts"] == 2
    assert by_id["cm-2"]["highest_level"] == 2 and by_id["cm-1"]["overall_status"] == "ok"
    assert (await client.get("/api/v1/crew", headers=A)).status_code == 403
