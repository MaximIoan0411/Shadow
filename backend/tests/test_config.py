from app.main import create_app


def test_settings_read_from_env_at_create_app(monkeypatch):
    monkeypatch.setenv("TIME_SCALE", "7")
    app = create_app()
    assert app.state.settings.time_scale == 7


def test_cors_origins_come_from_settings(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", '["http://frontend.test:3000"]')
    app = create_app()
    assert app.state.settings.cors_origins == ["http://frontend.test:3000"]
    cors = next(m for m in app.user_middleware if m.cls.__name__ == "CORSMiddleware")
    assert cors.kwargs["allow_origins"] == ["http://frontend.test:3000"]


async def test_validation_error_message_is_english(client):
    r = await client.post("/api/v1/auth/login", json={})
    assert r.status_code == 422
    body = r.json()["error"]
    assert body["code"] == "validation_error"
    assert body["message"] == "The submitted data does not match the contract."
