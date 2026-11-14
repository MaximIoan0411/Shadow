"""Clientul pentru llama-server (API compatibil OpenAI), local sau pe Colab, prin tunel.

Serviciul trimite doar promptul gata făcut (rolul, recomandarea, dovezile fără nume, fragmentele găsite și
întrebarea). Cheia API e cerută de llama-server (`--api-key`), fiindcă tunelul e public.
"""
import re

import httpx

from .config import Settings

THINKING = re.compile(r"<think>.*?</think>", re.S)
CLOSE_THINKING = "</think>"


class LlmUnavailable(RuntimeError):
    """Modelul nu răspunde: serviciul întoarce 503, iar backend-ul trece pe textul din catalog."""


class LlmClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        headers = {"Authorization": f"Bearer {settings.llm_api_key}", "ngrok-skip-browser-warning": "1"}
        timeout = httpx.Timeout(settings.timeout_s, connect=5.0)
        self.http = httpx.AsyncClient(base_url=settings.llm_url, headers=headers, timeout=timeout)
        self.model_name: str | None = None

    async def model(self) -> str | None:
        """Numele modelului servit, sau None dacă serverul nu răspunde."""
        try:
            response = await self.http.get("/v1/models", timeout=5.0)
            response.raise_for_status()
            models = response.json().get("data", [])
            self.model_name = models[0]["id"] if models else "llama-server"
        except (httpx.HTTPError, ValueError, KeyError, IndexError):
            return None
        return self.model_name

    async def complete(self, messages: list[dict], max_tokens: int = 320) -> str:
        payload = {
            "model": self.model_name or "default",
            "messages": messages,
            "temperature": 0.3,
            "top_p": 0.9,
            "max_tokens": max_tokens,
            # Qwen3.5 / Gemma 4 pot „gândi” înainte de răspuns; aici vrem doar răspunsul, repede
            "chat_template_kwargs": {"enable_thinking": False},
        }
        try:
            response = await self.http.post("/v1/chat/completions", json=payload)
            response.raise_for_status()
            text = response.json()["choices"][0]["message"]["content"] or ""
        except (httpx.HTTPError, ValueError, KeyError, IndexError) as error:
            raise LlmUnavailable(str(error)) from error
        text = THINKING.sub("", text)
        # unele șabloane deschid <think> chiar în prompt, deci în răspuns apare doar închiderea
        if CLOSE_THINKING in text:
            text = text.rsplit(CLOSE_THINKING, 1)[1]
        # un <think> rămas neînchis (răspuns tăiat de limită) ajunge la gardă, care îl respinge
        return text.strip()

    async def close(self) -> None:
        await self.http.aclose()
