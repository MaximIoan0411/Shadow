import logging
import secrets
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

log = logging.getLogger("uvicorn.error")

BACKEND_DIR = Path(__file__).resolve().parents[1]
# .env from the repository root or from backend/ (the latter wins), wherever the server is started from
ENV_FILES = (str(BACKEND_DIR.parent / ".env"), str(BACKEND_DIR / ".env"))

MIN_SECRET_CHARS = 32
KNOWN_SECRETS = {"", "dev-secret-schimba-ma", "schimba-ma", "changeme", "secret", "test"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILES, extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./shadow.sqlite"
    reset_db_on_start: bool = True
    time_scale: float = 60
    data_dir: str = "../data"
    keys_dir: str = "../security/keys"
    jwt_secret: str = ""
    allow_mock_tokens: bool = False
    link_aes_key_b64: str = ""
    ai_url: str = "http://127.0.0.1:8001"
    ai_timeout_s: float = 20
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    background_tasks: bool = True


def get_settings() -> Settings:
    settings = Settings()
    if settings.jwt_secret in KNOWN_SECRETS or len(settings.jwt_secret) < MIN_SECRET_CHARS:
        # a missing, published or short secret would let anyone sign their own tokens: use a random one instead.
        # Tokens then stop working when the server restarts; set JWT_SECRET in .env to keep them.
        settings.jwt_secret = secrets.token_urlsafe(48)
        log.warning("JWT_SECRET is missing or weak: using a random secret for this run (tokens end at restart).")
    if settings.allow_mock_tokens:
        log.warning("ALLOW_MOCK_TOKENS is on: `Bearer mock-<username>` signs in WITHOUT a password. Tests only.")
    return settings
