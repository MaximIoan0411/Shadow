"""Setările serviciului AI, din variabile de mediu sau din ai/.env (care nu intră în git)."""
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def _read_env_file() -> dict[str, str]:
    if not ENV_FILE.exists():
        return {}
    pairs = (line.split("=", 1) for line in ENV_FILE.read_text(encoding="utf-8").splitlines() if "=" in line and not line.lstrip().startswith("#"))
    return {key.strip(): value.strip().strip('"').strip("'") for key, value in pairs}


@dataclass(frozen=True)
class Settings:
    llm_url: str
    llm_api_key: str
    mode: Literal["local", "colab_simulation", "mock"]
    timeout_s: float


def load_settings() -> Settings:
    values = {**_read_env_file(), **os.environ}
    url = values.get("SHADOW_LLM_URL", "").rstrip("/")
    mode = values.get("SHADOW_LLM_MODE", "colab_simulation") if url else "mock"
    if mode not in ("local", "colab_simulation"):
        mode = "colab_simulation" if url else "mock"
    return Settings(llm_url=url, llm_api_key=values.get("SHADOW_LLM_API_KEY", ""), mode=mode,
                    timeout_s=float(values.get("SHADOW_LLM_TIMEOUT", "15")))
