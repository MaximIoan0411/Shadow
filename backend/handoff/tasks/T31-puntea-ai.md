# T31 — Puntea către medicul AI

**Cine:** A · **Prioritate:** P1 · **Durată estimată:** ~45 min · **Depinde de:** T17 · **Deblochează:** —

## Ce construiești

`POST /ai/chat` construiește contextul (alerta, dovezile, recomandarea din catalog), apelează serviciul AI cu limită de 20 s și cade pe textul din catalog dacă nu răspunde. Niciodată eroare din cauza AI-ului.

## De citit (atașează-le lui Claude)

- `backend/handoff/01_CONTEXT.md` (mereu)
- `backend/app/routers/ai.py` (mock)
- `backend/app/services/ai.py` (schelet)
- `backend/app/ai_schemas.py`
- `contract/ai/README.md` §3–5

## Pași

1. Astronautul întreabă doar despre `crew_id`-ul lui (regula există).
2. Contextul `AiContext`: din `alert_id` (dacă e dat): topic, level, titlu, dovezi, recomandarea din catalog; plus `mission_day`, mediul. **Fără nume și fără `crew_id`.**
3. Apel: `httpx.AsyncClient(timeout=settings.ai_timeout_s).post(f"{settings.ai_url}/chat", json=…)`, **fără sesiune de bază deschisă** în timpul așteptării.
4. Răspuns → `AiChatResponse` (`fallback=False`, `latency_ms` măsurat, `disclaimer`).
5. Orice eroare (timeout, conexiune refuzată, 503, 422) → `answer = recommendation.action`, `citations = [sursa recomandării]`, `fallback=True`, `model="catalog"`.
6. `GET /ai/status`: din `GET {ai_url}/status`; dacă nu răspunde → `ready=False`, `mode="fallback"`.
7. Teste: cu serviciul AI oprit, `/ai/chat` dă 200 și `fallback=True`; cu mock-ul AI pornit (sau `httpx.MockTransport`), `fallback=False` și citarea vine din serviciu.

## Fișierele atinse

- `app/services/ai.py`
- `app/routers/ai.py`
- `tests/routers/test_ai_bridge.py` (nou)

## Gata când

- [ ] `uv run pytest -q` (din `backend/`) → toate trec
- [ ] `uv run --project backend python scripts/smoke.py` (din rădăcina repo-ului) → `OK`
- [ ] `cd ai && uv run uvicorn service.main:app --port 8001` + backend → răspunsul vine din mock-ul AI
- [ ] `uv run ruff check app tests` → fără erori
- [ ] PR mic, titlul `backend: T31 puntea către medicul ai`

## Regula generală

Schimbi doar corpul funcțiilor. Căile, parametrii, `response_model` și erorile routerelor, `schemas.py`,
`ai_schemas.py`, `datafiles.py` și semnăturile din `security/` sunt contract. Mock-ul rămâne funcțional
pentru tot ce nu ține de acest task.
