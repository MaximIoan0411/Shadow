from types import SimpleNamespace

import pytest
from asgi_lifespan import LifespanManager

from app.datafiles import DataBundle, DataError
from app.deps import get_data
from app.security.keys import Keys


@pytest.fixture
def db_env(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 'test.sqlite'}")


async def test_empty_data_dir_stops_startup_with_missing_files(db_env, tmp_path, monkeypatch):
    empty = tmp_path / "empty_data"
    empty.mkdir()
    monkeypatch.setenv("DATA_DIR", str(empty))

    from app.main import create_app

    with pytest.raises(DataError) as err:
        async with LifespanManager(create_app()):
            pass
    message = str(err.value)
    assert "parameters.json" in message
    assert "scenario" in message


async def test_get_data_returns_loaded_bundle(db_env):
    from app.main import create_app

    app = create_app()
    async with LifespanManager(app):
        data = get_data(SimpleNamespace(app=app))
        assert isinstance(data, DataBundle)
        assert data.params.value("nightsignal_red_delta_bpm") == 4
        assert isinstance(app.state.keys, Keys)


async def test_relative_data_dir_is_resolved_from_backend(db_env, monkeypatch, tmp_path):
    monkeypatch.setenv("DATA_DIR", "../data")
    monkeypatch.chdir(tmp_path)

    from app.main import create_app

    app = create_app()
    async with LifespanManager(app):
        assert app.state.data.scenario.start_day == 96
