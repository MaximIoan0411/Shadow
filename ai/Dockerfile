# Build from the repository root:  docker build -f ai/Dockerfile .   (or `docker compose up --build`)
# The image keeps the repository layout (/app/ai, /app/data): the knowledge base also indexes ../data.
# The index and the embedding model (≈65 MB) are built into the image, so the service starts offline.
# The language model is NOT in the image: it is a llama-server reached at SHADOW_LLM_URL (see ai/README.md).
# Without it the service answers from the catalog (mode "mock").

FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /usr/local/bin/uv
ENV UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1 UV_PYTHON_DOWNLOADS=never
WORKDIR /app/ai
COPY ai/pyproject.toml ai/uv.lock ./
RUN uv sync --frozen --no-dev
ENV PATH="/app/ai/.venv/bin:$PATH"
COPY data/ /app/data/
COPY ai/ ./
# downloads the embedding model into models/embeddings and writes index/
RUN python -m rag.ingest


FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PATH="/app/ai/.venv/bin:$PATH" HF_HUB_OFFLINE=1
RUN useradd --system --user-group --uid 10001 --no-create-home app
WORKDIR /app/ai
COPY data/ /app/data/
COPY --from=builder --chown=app:app /app/ai/ ./

USER app
EXPOSE 8001
HEALTHCHECK --interval=5s --timeout=3s --start-period=30s --retries=10 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/status', timeout=2)"
CMD ["python", "-m", "uvicorn", "service.main:app", "--host", "0.0.0.0", "--port", "8001"]
