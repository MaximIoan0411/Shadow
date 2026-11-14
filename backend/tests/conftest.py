import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient


@pytest.fixture(scope="session", autouse=True)
def throwaway_keys(tmp_path_factory):
    # the tests never touch the real keys in security/keys/keys_files: the backend creates a fresh set here
    import os

    os.environ["SHADOW_KEYS_DIR"] = str(tmp_path_factory.mktemp("keys"))
    yield
    os.environ.pop("SHADOW_KEYS_DIR", None)


@pytest.fixture(autouse=True)
def no_background_tasks(monkeypatch):
    # the mission ticker and the link scheduler would push events into the tests' queues;
    # tests call the scheduler step by step instead
    monkeypatch.setenv("BACKGROUND_TASKS", "false")
    # tests sign in with `mock-<user>` tokens; outside the tests they are off by default
    monkeypatch.setenv("ALLOW_MOCK_TOKENS", "true")


@pytest.fixture
async def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 'test.sqlite'}")
    monkeypatch.setenv("TIME_SCALE", "1")
    monkeypatch.setenv("JWT_SECRET", "test-secret-of-at-least-32-characters")
    from app.main import create_app

    app = create_app()
    async with LifespanManager(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c


def auth(username: str) -> dict:
    return {"Authorization": f"Bearer mock-{username}"}
