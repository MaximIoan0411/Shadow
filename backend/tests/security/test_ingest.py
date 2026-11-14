from datetime import UTC, datetime, timedelta

from app.clock import clock
from app.security import validation
from app.services import security_log
from app.simulator.devices import signed_measurement
from tests.conftest import auth

URL = "/api/v1/ingest/measurements"
C = auth("medic")


def measurement(value=36.7, metric="temperature_c", unit="°C", device="wearable-cm-3", crew="cm-3", minutes=0):
    at = (clock.now() - timedelta(minutes=minutes)).isoformat()
    return signed_measurement(device, crew, metric, value, unit, at, b"")


async def test_valid_measurement_is_saved(client):
    r = await client.post(URL, json=measurement())
    assert r.status_code == 200 and r.json() == {"accepted": True, "rejection": None}


async def test_tampered_measurement_is_rejected(client):
    body = {**measurement(), "signature_b64": "invalid"}
    r = (await client.post(URL, json=body)).json()
    assert r["accepted"] is False and r["rejection"]["kind"] == "bad_signature"
    unknown = (await client.post(URL, json=measurement(device="wearable-cm-9"))).json()
    assert unknown["rejection"]["kind"] == "bad_signature"


async def test_pulse_400_is_implausible(client):
    r = (await client.post(URL, json=measurement(400, "night_pulse_bpm", "bpm"))).json()
    assert r["accepted"] is False and r["rejection"]["kind"] == "implausible"
    assert r["rejection"]["message"].startswith("Impossible value: 400 bpm")


async def test_twenty_identical_values_are_a_frozen_sensor(client):
    n = validation.FROZEN_REPEATS
    results = [(await client.post(URL, json=measurement(minutes=n - i))).json() for i in range(n)]
    assert all(r["accepted"] for r in results[:-1])
    assert results[-1]["rejection"]["kind"] == "frozen_sensor"


async def test_rejections_list_newest_first(client):
    await client.post(URL, json={**measurement(), "signature_b64": "invalid"})
    await client.post(URL, json=measurement(400, "night_pulse_bpm", "bpm"))
    rows = (await client.get("/api/v1/security/rejections", headers=C)).json()
    assert [r["kind"] for r in rows] == ["implausible", "bad_signature"] and rows[0]["id"] == "rj-0002"


async def test_parameters_come_from_data(client):
    params = (await client.get("/api/v1/evidence/parameters?key_only=true", headers=C)).json()
    ids = {p["id"] for p in params}
    assert "nightsignal_red_delta_bpm" in ids and all(p["is_key_threshold"] for p in params)


def test_junit_report_parsing():
    xml = """<testsuites><testsuite>
      <testcase classname="tests.engine.test_immune" name="test_nightsignal_red_after_two_nights" time="0.012"/>
      <testcase classname="tests.engine.test_x" name="test_fail" time="0.1"><failure message="x"/></testcase>
      <testcase classname="tests.engine.test_x" name="test_skip" time="0"><skipped/></testcase>
    </testsuite></testsuites>"""
    report = security_log.parse_junit(xml, datetime(2027, 4, 15, 7, tzinfo=UTC), 1.0)
    assert (report.passed, report.failed, report.skipped) == (1, 1, 1)
    assert report.tests[0].module == "tests/engine/test_immune.py" and report.tests[0].duration_ms == 12.0


async def test_engine_tests_run_for_the_evidence_screen(client):
    report = await security_log.run_engine_tests()
    assert report is not None and report.failed == 0 and report.passed > 50
    assert any(t.name == "test_nightsignal_red_after_two_nights" for t in report.tests)
    shown = (await client.get("/api/v1/evidence/tests", headers=C)).json()
    assert shown["passed"] == report.passed
