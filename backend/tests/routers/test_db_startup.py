import sqlite3

from asgi_lifespan import LifespanManager
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


async def test_startup_deletes_old_database(tmp_path, monkeypatch):
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
