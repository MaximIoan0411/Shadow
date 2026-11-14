# Jurnal backend

## T00 — Pornire și verificare

**Ce s-a făcut:** Am verificat mediul (uv 0.13.7, Python 3.12, `uv sync` fără schimbări) și am rulat toate verificările din task. Serverul mock pornește, `/docs` se deschide, login-ul cu `specialist2` / `cm2-shadow` întoarce token, iar `GET /api/v1/crew/cm-2/dashboard` arată alerta imunitară din scenariu (`al-1042`, „Puls de noapte +7 bpm, 3 nopți la rând”, nivel 2, escaladată). Nu s-a modificat niciun fișier de cod.

**Fișiere modificate:**
- backend/JURNAL.md — creat, cu acest raport (singurul fișier nou)

**Teste adăugate:**
- niciunul (taskul nu cere teste)

**Rezultate:** pytest 5 trecute / 0 picate · ruff check ok (`All checks passed!`) · ruff format: NU rulat (vezi decizii) · smoke ok (`OK: API 56 endpoint-uri + permisiuni + conturi separate + reguli 1.2 · data 50 recomandări · AI 9 modele identice · securitate 20 funcții (13 încă provizorii)`)

**Endpointuri devenite reale:** niciunul

**Texte rămase în română:** toate răspunsurile mock (din `app/examples.py`: titluri de piloni, headline-uri, titluri de alerte, nume afișate) și textele din `data/`. Neatinse, pentru că T00 nu modifică fișiere; se traduc în taskurile care ating fiecare router.

**Decizii luate singur:**
- `uv run ruff format` NU l-am rulat, doar `--check`: ar reformata 63 de fișiere (spații înainte de comentarii, rânduri goale), inclusiv contractul (`app/schemas.py`, `app/ai_schemas.py`, `app/datafiles.py`) și `app/security/*`. T00 spune „nimic de schimbat”. De hotărât în echipă dacă se face o singură dată, într-un PR separat.
- `JURNAL.md` e în `backend/` (lângă `CUM_LUCRAM.MD`), nu în rădăcina repo-ului, ca să rămân doar în `backend/`.
- Portul 8000: pe `localhost` (IPv6 `::1`) răspunde alt program, un container Docker („Salut Compose”). SHADOW ascultă pe `127.0.0.1:8000`. Am testat pe `127.0.0.1`.
- Observație: smoke numără 56 de endpoint-uri, `00_CITESTE_INTAI.md` spune 57. Smoke trece; doar o nepotrivire în document.

**Cum verific eu de mână:**
1. `cd backend; uv run uvicorn app.main:app --reload --port 8000`, apoi deschide **http://127.0.0.1:8000/docs** (nu `localhost`, cât timp merge containerul Docker pe 8000).
2. În Swagger: `POST /api/v1/auth/login` cu `{"username":"specialist2","password":"cm2-shadow"}` → „Authorize” cu `access_token`.
3. `GET /api/v1/crew/cm-2/dashboard` → `top_alert.id = "al-1042"`, `topic = "immune"`.

**Mesaj de commit propus:** backend: T00 pornire și verificare

**Următorul task:** T01 (dependențele lui sunt gata: da)
