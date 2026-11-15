# Build from the repository root:  docker build -f backend/Dockerfile .
# The image keeps the repository layout (/app/backend, /app/data, /app/security/keys),
# because the backend reads ../data and creates its keys with ../security/keys/generate_keys.py.

FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /usr/local/bin/uv
ENV UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1 UV_PYTHON_DOWNLOADS=never
WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock ./
# the dev group stays in: the Evidence screen runs `pytest tests/engine` at startup
RUN uv sync --frozen


FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PATH="/app/backend/.venv/bin:$PATH"
WORKDIR /app/backend
COPY --from=builder /app/backend/.venv ./.venv
COPY data/ /app/data/
COPY security/keys/generate_keys.py /app/security/keys/generate_keys.py
COPY backend/ ./

ENV DATA_DIR=/app/data \
    KEYS_DIR=/app/security/keys \
    DATABASE_URL=sqlite+aiosqlite:////app/backend/shadow.sqlite \
    AI_URL=http://ai:8001

EXPOSE 8000
HEALTHCHECK --interval=5s --timeout=3s --start-period=20s --retries=10 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
