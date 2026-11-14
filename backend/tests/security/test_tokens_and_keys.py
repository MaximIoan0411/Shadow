import base64
import json
import stat
import sys
import time

import jwt
import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.config import get_settings
from app.db import session as db
from app.db.models.users import RevokedToken
from app.security import keys as security_keys
from app.security import lockout, passwords, tokens
from app.security.errors import InvalidToken
from tests.conftest import auth

ME = "/api/v1/auth/me"
SECRET = "a-secret-of-at-least-32-characters-123"


def claims(**changes) -> dict:
    return {"sub": "u-cm-3", "role": "cmo", "crew_id": "cm-3", "jti": "x", "exp": int(time.time()) + 600, **changes}


def b64(data: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()


# --------------------------------------------------------------------------- tokens


def test_token_round_trip():
    token, issued = tokens.issue(user_id="u-cm-2", role="astronaut", crew_id="cm-2", secret=SECRET)
    assert tokens.decode(token, secret=SECRET) == issued


@pytest.mark.parametrize(
    "token",
    [
        jwt.encode(claims(), "another-secret-of-at-least-32-characters", algorithm="HS256"),
        jwt.encode(claims(exp=int(time.time()) - 5), SECRET, algorithm="HS256"),
        jwt.encode(claims(), SECRET, algorithm="HS512"),
        b64({"alg": "none", "typ": "JWT"}) + "." + b64(claims()) + ".",
        jwt.encode({k: v for k, v in claims().items() if k != "jti"}, SECRET, algorithm="HS256"),
        jwt.encode(claims(role=7), SECRET, algorithm="HS256"),
        "not-a-token",
        "",
    ],
    ids=["other secret", "expired", "other algorithm", "unsigned", "no jti", "role is a number", "garbage", "empty"],
)
def test_bad_tokens_are_refused(token):
    with pytest.raises(InvalidToken):
        tokens.decode(token, secret=SECRET)


async def test_published_default_secrets_cannot_forge_a_token(tmp_path, monkeypatch):
    # a clone without .env: the secrets that ever appeared in the repository must not sign anything
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 'fresh.sqlite'}")
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.delenv("ALLOW_MOCK_TOKENS", raising=False)
    from app.main import create_app

    app = create_app()
    async with LifespanManager(app), AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        for secret in ("dev-secret-schimba-ma", "schimba-ma", "test", ""):
            forged = jwt.encode(claims(), secret or "x", algorithm="HS256")
            assert (await c.get(ME, headers={"Authorization": f"Bearer {forged}"})).status_code == 401
        # and the password-less mock tokens are off unless someone turns them on
        assert (await c.get(ME, headers=auth("medic"))).status_code == 401


async def test_logout_is_stored_in_the_database(client):
    r = await client.post("/api/v1/auth/login", json={"username": "specialist2", "password": "cm2-shadow"})
    token = r.json()["access_token"]
    await client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    async with db.SessionLocal() as s:
        [row] = (await s.scalars(select(RevokedToken))).all()
    assert len(row.jti) == 32
    # a reset must not bring signed-out tokens back to life
    await client.post("/api/v1/sim/reset", headers=auth("medic"))
    assert (await client.get(ME, headers={"Authorization": f"Bearer {token}"})).status_code == 401


# --------------------------------------------------------------------------- settings


def test_weak_secret_is_replaced_and_strong_secret_is_kept(monkeypatch):
    for weak in ("", "schimba-ma", "dev-secret-schimba-ma", "short"):
        monkeypatch.setenv("JWT_SECRET", weak)
        first, second = get_settings().jwt_secret, get_settings().jwt_secret
        assert len(first) >= 32 and first != weak and first != second
    monkeypatch.setenv("JWT_SECRET", SECRET)
    assert get_settings().jwt_secret == SECRET


def test_mock_tokens_are_off_by_default(monkeypatch):
    monkeypatch.delenv("ALLOW_MOCK_TOKENS", raising=False)
    assert get_settings().allow_mock_tokens is False


# --------------------------------------------------------------------------- keys


def test_keys_are_created_once_and_then_reused(tmp_path, monkeypatch):
    monkeypatch.setenv("SHADOW_KEYS_DIR", str(tmp_path / "k"))
    first = security_keys.load_keys()
    second = security_keys.load_keys()
    assert first.ship_private == second.ship_private and first.link_aes_key == second.link_aes_key
    assert len(first.link_aes_key) == 32 and len(first.ship_private) == 32 and first.ship_private != first.earth_private
    assert set(first.device_public) == {f"wearable-cm-{i}" for i in range(1, 5)}
    assert first.device_crew["wearable-cm-2"] == "cm-2"
    if sys.platform != "win32":
        mode = stat.S_IMODE((tmp_path / "k" / "private" / "ship.pem").stat().st_mode)
        assert mode == 0o600


def test_a_broken_or_missing_key_stops_startup_with_a_clear_message(tmp_path, monkeypatch):
    monkeypatch.setenv("SHADOW_KEYS_DIR", str(tmp_path / "k"))
    security_keys.load_keys()
    with pytest.raises(security_keys.KeysError, match="LINK_AES_KEY_B64"):
        security_keys.load_keys(link_aes_key_b64="not base64 !!")
    with pytest.raises(security_keys.KeysError, match="32 bytes"):
        security_keys.load_keys(link_aes_key_b64=base64.b64encode(b"too short").decode())
    (tmp_path / "k" / "private" / "ship.pem").write_text("not a key")
    with pytest.raises(security_keys.KeysError, match="ship.pem"):
        security_keys.load_keys()
    # no generator next to the keys folder and no keys: nothing is invented
    monkeypatch.setenv("SHADOW_KEYS_DIR", str(tmp_path / "empty"))
    with pytest.raises(security_keys.KeysError, match="generate_keys.py"):
        security_keys.load_keys(keys_dir=str(tmp_path / "no-generator-here"))


# --------------------------------------------------------------------------- passwords and lockout


def test_passwords_are_argon2id_and_long_input_is_refused_before_hashing():
    stored = passwords.hash("cm2-shadow")
    assert stored.startswith("$argon2id$") and passwords.verify("cm2-shadow", stored)
    assert not passwords.verify("cm1-shadow", stored) and not passwords.verify("cm2-shadow", "not a hash")
    started = time.perf_counter()
    assert not passwords.verify("x" * 5_000_000, stored)
    assert time.perf_counter() - started < 0.05


def test_made_up_usernames_do_not_fill_the_memory():
    lockout.reset_all()
    for i in range(lockout.MAX_TRACKED + 500):
        lockout.record_failure(f"ghost-{i}")
    assert len(lockout._failed) + len(lockout._locked_until) <= lockout.MAX_TRACKED
    lockout.reset_all()


async def test_oversized_input_is_refused_at_the_door(client):
    r = await client.post("/api/v1/auth/login", json={"username": "medic", "password": "x" * 257})
    assert r.status_code == 422
    r = await client.post("/api/v1/auth/login", json={"username": "m" * 41, "password": "x"})
    assert r.status_code == 422
    a = auth("specialist2")
    long_history = [{"role": "user", "content": "x" * 2001}]
    r = await client.post(
        "/api/v1/ai/chat", headers=a, json={"crew_id": "cm-2", "message": "hi", "history": long_history}
    )
    assert r.status_code == 422
    many = [{"role": "user", "content": "x"}] * 21
    r = await client.post("/api/v1/ai/chat", headers=a, json={"crew_id": "cm-2", "message": "hi", "history": many})
    assert r.status_code == 422
    trials = [{"stimulus_at_ms": i * 1000, "rt_ms": 300} for i in range(1001)]
    r = await client.post(
        "/api/v1/crew/cm-2/pvt", headers=a, json={"started_at": "2027-04-15T07:00:00Z", "trials": trials}
    )
    assert r.status_code == 422
    r = await client.post(
        "/api/v1/crew/cm-2/checkins",
        headers={**a, "Content-Type": "application/json"},
        content='{"mood": 3, "sleep_hours": NaN}',
    )
    assert r.status_code == 422
