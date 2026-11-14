import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from app.security import access_log, lockout, tokens
from tests.conftest import auth

LOGIN = "/api/v1/auth/login"
ME = "/api/v1/auth/me"


@pytest.fixture(autouse=True)
def clean_lockout():
    lockout.reset_all()
    yield
    lockout.reset_all()


async def sign_in(client, username="specialist2", password="cm2-shadow"):
    return await client.post(LOGIN, json={"username": username, "password": password})


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_login_returns_real_token_that_works_on_me(client):
    r = await sign_in(client)
    assert r.status_code == 200
    body = r.json()
    token = body["access_token"]
    assert not token.startswith("mock-") and token.count(".") == 2
    assert body["token_type"] == "bearer" and body["expires_in"] == tokens.TTL_S
    assert body["user"]["crew_id"] == "cm-2"

    me = await client.get(ME, headers=bearer(token))
    assert me.status_code == 200
    assert me.json()["username"] == "specialist2" and me.json()["role"] == "astronaut"


async def test_logout_revokes_the_token(client):
    token = (await sign_in(client)).json()["access_token"]
    assert (await client.post("/api/v1/auth/logout", headers=bearer(token))).status_code == 200
    r = await client.get(ME, headers=bearer(token))
    assert r.status_code == 401 and r.json()["error"]["code"] == "unauthorized"


async def test_other_accounts_password_is_rejected(client):
    r = await sign_in(client, "specialist2", "cm1-shadow")
    assert r.status_code == 401
    assert r.json()["error"] == {
        "code": "invalid_credentials",
        "message": "Wrong username or password.",
        "details": None,
    }


async def test_unknown_user_gets_same_error(client):
    r = await sign_in(client, "nobody", "whatever")
    assert r.status_code == 401 and r.json()["error"]["code"] == "invalid_credentials"


async def test_five_wrong_passwords_lock_only_that_account(client):
    for _ in range(5):
        assert (await sign_in(client, "inginer", "wrong")).status_code == 401
    r = await sign_in(client, "inginer", "cm4-shadow")
    assert r.status_code == 429
    assert r.json()["error"]["code"] == "too_many_attempts"
    assert r.json()["error"]["details"]["retry_after_s"] > 0
    assert (await sign_in(client, "comandant", "cm1-shadow")).status_code == 200


async def test_role_and_crew_come_only_from_token(client):
    token = (await sign_in(client)).json()["access_token"]
    assert (await client.get("/api/v1/crew/cm-2/dashboard", headers=bearer(token))).status_code == 200
    assert (await client.get("/api/v1/crew/cm-1/dashboard", headers=bearer(token))).status_code == 403


async def test_tampered_token_is_rejected(client):
    token = (await sign_in(client)).json()["access_token"]
    header, body, sig = token.split(".")
    r = await client.get(ME, headers=bearer(f"{header}.{body}.{sig[:-2]}xx"))
    assert r.status_code == 401


async def test_login_and_failures_are_written_to_access_log(client):
    before = len(access_log._entries)
    await sign_in(client, "specialist2", "wrong")
    await sign_in(client)
    actions = [(e.action, e.outcome) for e in access_log._entries[before:]]
    assert actions == [("login_failed", "denied"), ("login", "allowed")]


async def test_accounts_come_from_database(client):
    accounts = (await client.get("/api/v1/auth/accounts")).json()
    assert [a["username"] for a in accounts] == ["comandant", "specialist2", "medic", "inginer", "earth"]
    assert [a["location"] for a in accounts] == ["ship"] * 4 + ["earth"]


async def test_mock_token_accepted_when_allowed(client):
    assert (await client.get(ME, headers=auth("specialist2"))).status_code == 200


async def test_mock_token_rejected_when_not_allowed(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 'nomock.sqlite'}")
    monkeypatch.setenv("JWT_SECRET", "test")
    monkeypatch.setenv("ALLOW_MOCK_TOKENS", "false")
    from app.main import create_app

    app = create_app()
    async with LifespanManager(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get(ME, headers=auth("specialist2"))
            assert r.status_code == 401 and r.json()["error"]["code"] == "unauthorized"
            real = (await sign_in(c)).json()["access_token"]
            assert (await c.get(ME, headers=bearer(real))).status_code == 200
