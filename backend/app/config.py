"""Setările, citite din .env / mediu (pydantic-settings). TASK T01.

Se citesc la APEL (get_settings()), nu la import, ca testele să le poată schimba înainte de create_app().
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./shadow.sqlite"
    reset_db_on_start: bool = True
    time_scale: float = 60
    data_dir: str = "../data"
    jwt_secret: str = "dev-secret-schimba-ma"   # T07: în producție obligatoriu din .env
    allow_mock_tokens: bool = True              # T07: acceptă și „mock-<utilizator>” (testele, smoke.py, frontend-ul pe mock)
    link_aes_key_b64: str = ""
    ai_url: str = "http://localhost:8001"
    ai_timeout_s: float = 20
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]


def get_settings() -> Settings:
    return Settings()
