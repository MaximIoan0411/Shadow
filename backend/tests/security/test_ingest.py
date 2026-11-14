import json
from datetime import UTC, datetime, timedelta

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.clock import clock
from app.security import validation
from app.services import security_log
from app.simulator.devices import signed_measurement
from tests.conftest import auth

URL = "/api/v1/ingest/measurements"
C = auth("medic")


def device_key(client, device: str) -> bytes:
    return client._transport.app.state.keys.device_private[device]


def other_key() -> bytes:
    """A valid Ed25519 key that no device is registered with."""
    return Ed25519PrivateKey.generate().private_bytes(
        serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption()
    )


def measurement(client, value=36.7, metric="temperature_c", unit="°C", device="wearable-cm-3", crew="cm-3", minutes=0):
    at = (clock.now() - timedelta(minutes=minutes)).isoformat()
    return signed_measurement(device, crew, metric, value, unit, at, device_key(client, device))


async def test_valid_measurement_is_saved(client):
    r = await client.post(URL, json=measurement(client))
    assert r.status_code == 200 and r.json() == {"accepted": True, "rejection": None}


async def test_whole_number_values_keep_their_signature(client):
    # the device signs `61`; after validation the backend holds 61.0, which is written differently
    body = measurement(client, 61, "night_pulse_bpm", "bpm")
    assert '"value": 61,' in json.dumps(body)
    assert (await client.post(URL, json=body)).json()["accepted"] is True


async def test_tampered_measurement_is_rejected(client):
    body = {**measurement(client), "signature_b64": "invalid"}
    r = (await client.post(URL, json=body)).json()
    assert r["accepted"] is False and r["rejection"]["kind"] == "bad_signature"
    changed = {**measurement(client), "value": 39.9}  # the value was changed after the device signed it
    assert (await client.post(URL, json=changed)).json()["rejection"]["kind"] == "bad_signature"
    at = clock.now().isoformat()
    unknown = signed_measurement("wearable-cm-9", "cm-3", "temperature_c", 36.7, "°C", at, other_key())
    assert (await client.post(URL, json=unknown)).json()["rejection"]["kind"] == "bad_signature"


async def test_any_text_is_not_a_signature(client):
    for signature in ("orice", "PROVIZORIU", "", "AAAA"):
        r = (await client.post(URL, json={**measurement(client), "signature_b64": signature})).json()
        assert r["accepted"] is False and r["rejection"]["kind"] == "bad_signature", signature


async def test_signature_from_another_key_is_rejected(client):
    at = clock.now().isoformat()
    forged = signed_measurement("wearable-cm-3", "cm-3", "temperature_c", 36.7, "°C", at, other_key())
    assert (await client.post(URL, json=forged)).json()["rejection"]["kind"] == "bad_signature"


async def test_a_device_cannot_speak_for_another_crew_member(client):
    # correctly signed by the wearable of cm-1, but about cm-2
    body = measurement(client, 44, "night_pulse_bpm", "bpm", device="wearable-cm-1", crew="cm-2")
    r = (await client.post(URL, json=body)).json()
    assert r["accepted"] is False and r["rejection"]["kind"] == "bad_signature"
    assert r["rejection"]["message"].startswith("wearable-cm-1 is not registered for cm-2")


async def test_the_same_measurement_sent_twice_is_a_replay(client):
    body = measurement(client)
    assert (await client.post(URL, json=body)).json()["accepted"] is True
    again = (await client.post(URL, json=body)).json()
    assert again["accepted"] is False and again["rejection"]["kind"] == "replay"


async def test_nan_and_infinity_are_not_measurements(client):
    for value in ("NaN", "Infinity", "-Infinity"):
        raw = json.dumps(measurement(client)).replace("36.7", value)
        r = await client.post(URL, content=raw, headers={"Content-Type": "application/json"})
        assert r.status_code == 422, value


async def test_pulse_400_is_implausible(client):
    r = (await client.post(URL, json=measurement(client, 400, "night_pulse_bpm", "bpm"))).json()
    assert r["accepted"] is False and r["rejection"]["kind"] == "implausible"
    assert r["rejection"]["message"].startswith("Impossible value: 400 bpm")


async def test_twenty_identical_values_are_a_frozen_sensor(client):
    n = validation.FROZEN_REPEATS
    results = [(await client.post(URL, json=measurement(client, minutes=n - i))).json() for i in range(n)]
    assert all(r["accepted"] for r in results[:-1])
    assert results[-1]["rejection"]["kind"] == "frozen_sensor"


async def test_rejections_list_newest_first(client):
    await client.post(URL, json={**measurement(client), "signature_b64": "invalid"})
    await client.post(URL, json=measurement(client, 400, "night_pulse_bpm", "bpm"))
    rows = (await client.get("/api/v1/security/rejections", headers=C)).json()
    assert [r["kind"] for r in rows] == ["implausible", "bad_signature"] and rows[0]["id"] == "rj-0002"


async def test_an_astronaut_does_not_see_a_colleagues_rejected_values(client):
    await client.post(URL, json=measurement(client, 400, "night_pulse_bpm", "bpm"))  # about cm-3
    mine = (await client.get("/api/v1/security/rejections", headers=auth("medic"))).json()
    assert [r["crew_id"] for r in mine] == ["cm-3"]
    assert (await client.get("/api/v1/security/rejections", headers=auth("specialist2"))).json() == []


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
