import sqlite3
from contextlib import asynccontextmanager

from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, inspect

EXPECTED_TABLES = 16


def table_names(path) -> set[str]:
    engine = create_engine(f"sqlite:///{path}")
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


async def test_startup_creates_sqlite_file_with_all_tables(client, tmp_path):
    path = tmp_path / "test.sqlite"
    assert path.exists()
    names = table_names(path)
    assert len(names) == EXPECTED_TABLES
    assert {"crew", "users", "alerts", "packets", "access_log"} <= names


async def test_health_reports_db_ok(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["db"] == "ok"


async def test_startup_empties_an_old_database(tmp_path, monkeypatch):
    path = tmp_path / "old.sqlite"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE stale (id INTEGER)")
    conn.close()
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{path}")
    monkeypatch.setenv("RESET_DB_ON_START", "true")

    from app.main import create_app

    async with LifespanManager(create_app()):
        names = table_names(path)
    assert "stale" not in names
    assert len(names) == EXPECTED_TABLES


async def test_startup_keeps_database_when_reset_is_off(tmp_path, monkeypatch):
    path = tmp_path / "keep.sqlite"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE stale (id INTEGER)")
    conn.close()
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{path}")
    monkeypatch.setenv("RESET_DB_ON_START", "false")

    from app.main import create_app

    async with LifespanManager(create_app()):
        names = table_names(path)
    assert "stale" in names


@asynccontextmanager
async def running_backend():
    """One run of the backend, from startup to shutdown, with the settings currently in the environment."""
    from app.main import create_app

    app = create_app()
    async with LifespanManager(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c


async def sign_in(c, username: str, password: str) -> dict:
    token = (await c.post("/api/v1/auth/login", json={"username": username, "password": password})).json()
    return {"Authorization": f"Bearer {token['access_token']}"}


async def test_a_restart_keeps_the_access_log_and_the_signed_out_tokens(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 'ship.sqlite'}")
    monkeypatch.setenv("JWT_SECRET", "the-same-secret-on-every-start-0123456789")   # tokens outlive a restart
    monkeypatch.setenv("RESET_DB_ON_START", "true")

    async with running_backend() as c:
        medic = await sign_in(c, "medic", "cm3-shadow")
        await c.get("/api/v1/crew/cm-2/dashboard", headers=medic)          # written to the access log
        await c.put("/api/v1/sim/clock", headers=medic, json={"mission_day": 97})
        left = await sign_in(c, "specialist2", "cm2-shadow")
        await c.post("/api/v1/auth/logout", headers=left)
        assert (await c.get("/api/v1/auth/me", headers=left)).status_code == 401
        before = (await c.get("/api/v1/access-log?limit=500", headers=medic)).json()
    assert {"login", "read_dashboard", "logout"} <= {e["action"] for e in before}

    async with running_backend() as c:                                      # the backend restarts
        # a token signed out before the restart stays refused; one that was never signed out still works
        assert (await c.get("/api/v1/auth/me", headers=left)).status_code == 401
        assert (await c.get("/api/v1/auth/me", headers=medic)).status_code == 200
        # the scenario starts over ...
        assert (await c.get("/api/v1/mission", headers=medic)).json()["mission_day"] == 96
        # ... but who read what is still there, and the chain goes on from the last entry
        after = (await c.get("/api/v1/access-log?limit=500", headers=medic)).json()
        assert [e["id"] for e in before] == [e["id"] for e in after][-len(before):]
        check = (await c.get("/api/v1/access-log/integrity", headers=medic)).json()
        assert check["intact"] is True and check["entries"] >= len(before)
        await c.get("/api/v1/crew/cm-2/dashboard", headers=medic)
        newest = (await c.get("/api/v1/access-log?limit=1", headers=medic)).json()[0]
        assert newest["id"] > before[0]["id"]
        assert (await c.get("/api/v1/access-log/integrity", headers=medic)).json()["intact"] is True


async def test_a_kept_table_from_an_older_version_starts_empty(tmp_path, monkeypatch):
    path = tmp_path / "older.sqlite"
    with sqlite3.connect(path) as conn:   # no migrations: an access log with another layout cannot be read
        conn.execute("CREATE TABLE access_log (id INTEGER PRIMARY KEY, who TEXT)")
        conn.execute("INSERT INTO access_log (who) VALUES ('someone')")
    conn.close()
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{path}")
    monkeypatch.setenv("RESET_DB_ON_START", "true")

    async with running_backend() as c:
        medic = await sign_in(c, "medic", "cm3-shadow")
        log = (await c.get("/api/v1/access-log", headers=medic)).json()
    assert [e["action"] for e in log] == ["login"] and log[0]["id"] == 1
