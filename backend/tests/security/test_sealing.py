import base64
import json
import os
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.clock import clock
from app.db import session as db
from app.db.models.link import Packet
from app.link import scheduler
from app.security import sealing
from app.security.errors import SealError
from tests.conftest import auth

A, C, E = auth("specialist2"), auth("medic"), auth("earth")
HEADER = {
    "id": "pk-0001",
    "seq": 1,
    "direction": "down",
    "kind": "alert_l3",
    "key_id": "ship-2026-01",
    "created_at": "2027-04-15T07:00:00+00:00",
}
PAYLOAD = {"note": "night pulse up for 3 nights", "level": 3}


def flip_first_byte(text_b64: str) -> str:
    raw = bytearray(base64.b64decode(text_b64))
    raw[0] ^= 1
    return base64.b64encode(bytes(raw)).decode()


async def test_a_sealed_packet_opens_and_hides_its_content(client):
    blob = sealing.seal(PAYLOAD, HEADER)
    assert sealing.open(blob, HEADER) == PAYLOAD
    assert b"night pulse" not in blob and b"level" not in blob
    assert sealing.seal(PAYLOAD, HEADER) != blob  # a new nonce every time


@pytest.mark.parametrize("field", ["nonce_b64", "ciphertext_b64", "signature_b64"])
async def test_any_changed_part_is_detected(client, field):
    box = json.loads(sealing.seal(PAYLOAD, HEADER))
    box[field] = flip_first_byte(box[field])
    with pytest.raises(SealError):
        sealing.open(json.dumps(box).encode(), HEADER)


@pytest.mark.parametrize("change", [{"seq": 2}, {"kind": "weekly_summary"}, {"direction": "up"}, {"id": "pk-0002"}])
async def test_a_changed_header_is_detected(client, change):
    blob = sealing.seal(PAYLOAD, HEADER)
    with pytest.raises(SealError):
        sealing.open(blob, {**HEADER, **change})


async def test_only_the_ship_can_sign_a_packet_going_down(client):
    for sender in ("earth", "attacker"):  # Earth's key is real, but it is not the ship's
        with pytest.raises(SealError):
            sealing.open(sealing.seal(PAYLOAD, HEADER, sender=sender), HEADER)
    with pytest.raises(ValueError):
        sealing.seal(PAYLOAD, HEADER, sender="nobody")


async def test_the_link_key_alone_cannot_forge_a_packet(client):
    # someone who stole the AES key encrypts their own content, but cannot sign as the ship
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    keys = client._transport.app.state.keys
    real = json.loads(sealing.seal(PAYLOAD, HEADER))
    nonce = os.urandom(12)
    aad = sealing._aad(HEADER)
    forged = AESGCM(keys.link_aes_key).encrypt(nonce, b'{"note":"all values normal"}', aad)
    box = {**real, "nonce_b64": base64.b64encode(nonce).decode(), "ciphertext_b64": base64.b64encode(forged).decode()}
    with pytest.raises(SealError):
        sealing.open(json.dumps(box).encode(), HEADER)


async def test_garbage_is_rejected_not_an_error(client):
    for blob in (
        b"",
        b"not json",
        b"[]",
        b'{"nonce_b64": "x"}',
        json.dumps({"aad": HEADER, "payload": PAYLOAD}).encode(),
    ):
        with pytest.raises(SealError):
            sealing.open(blob, HEADER)


async def test_packets_are_encrypted_in_the_database(client):
    await client.post("/api/v1/earth/replies", headers=E, json={"crew_id": "cm-2", "body": "SECRET-WORDS-123"})
    async with db.SessionLocal() as s:
        [p] = (await s.scalars(select(Packet))).all()
    assert b"SECRET-WORDS-123" not in bytes(p.sealed) and p.payload is None
    detail = (await client.get(f"/api/v1/link/packets/{p.id}", headers=C)).json()
    assert len(base64.b64decode(detail["crypto"]["nonce_b64"])) == 12
    assert len(base64.b64decode(detail["crypto"]["signature_b64"])) == 64


async def test_a_packet_changed_in_transit_is_rejected_on_arrival(client):
    t0 = clock.now()
    clock.freeze(t0)
    r = await client.post("/api/v1/link/outbox", headers=A, json={"kind": "weekly_summary", "crew_id": "cm-2"})
    packet_id = r.json()["id"]
    async with db.SessionLocal() as s:
        p = await s.get(Packet, packet_id)
        box = json.loads(p.sealed)
        box["ciphertext_b64"] = flip_first_byte(box["ciphertext_b64"])
        p.sealed = json.dumps(box).encode()
        await s.commit()
    data = client._transport.app.state.data
    for moment in (t0, t0 + timedelta(seconds=700)):
        clock.freeze(moment)
        async with db.SessionLocal() as s:
            await scheduler.step(s, data)
            await s.commit()
    detail = (await client.get(f"/api/v1/link/packets/{packet_id}", headers=E)).json()
    assert detail["status"] == "rejected" and detail["reject_reason"] == "bad_signature" and detail["payload"] is None
