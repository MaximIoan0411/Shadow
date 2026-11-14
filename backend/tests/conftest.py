"""Fixture-ul comun (backend/PLAN_DE_ATAC_BACKEND.md, secțiunea 13).

Fiecare test primește aplicația proaspătă, cu baza de date într-un fișier temporar (NU în memorie: acolo
scrierile în paralel se pierd fără eroare), cu lifespan rulat (seed, istoric, ceas)."""
import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 'test.sqlite'}")
    monkeypatch.setenv("TIME_SCALE", "1")
    monkeypatch.setenv("JWT_SECRET", "test")
    from app.main import create_app  # aplicația creată DUPĂ setarea mediului
    app = create_app()
    async with LifespanManager(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c


def auth(username: str) -> dict:
    """Antetul pentru un cont de test. În mock tokenul e „mock-<utilizator>”; se schimbă când vin tokenurile reale."""
    return {"Authorization": f"Bearer mock-{username}"}
