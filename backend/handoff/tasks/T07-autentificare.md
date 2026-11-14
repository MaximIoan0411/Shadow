# T07 — Autentificarea reală

**Cine:** A · **Prioritate:** P0 · **Durată estimată:** ~60 min · **Depinde de:** T06 · **Deblochează:** T08

## Ce construiești

Login, conturi, `me` și logout lucrează cu baza de date și tokenuri reale; `deps.current_user` decodează tokenul. Tokenurile `mock-<utilizator>` rămân acceptate cât `ALLOW_MOCK_TOKENS=true` (testele și frontend-ul pe mock).

## De citit (atașează-le lui Claude)

- `backend/handoff/01_CONTEXT.md` (mereu)
- `backend/app/routers/auth.py`
- `backend/app/deps.py`
- `backend/app/services/auth.py` (schelet)
- `contract/security/README.md`
- `handoff/02_CONTRACT_ENDPOINTS.md` (T07)

## Pași

1. `services/auth.list_accounts`: conturile din bază → `LoginAccount` (`location = "earth"` pentru rolul earth).
2. `services/auth.login`: ordinea din `contract/security/README.md` §2: `lockout.check` → `passwords.verify` (cu `DUMMY_HASH` dacă nu există) → `record_failure`/`clear` → `tokens.issue(secret=settings.jwt_secret)` → `access_log.write(login | login_failed)`.
3. `AccountLocked` → `ApiError(429, "too_many_attempts", …, {"retry_after_s": …})`; parolă greșită → `ApiError(401, "invalid_credentials", "Utilizator sau parolă greșită.")`.
4. `services/auth.user_from_token`: `mock-<u>` (dacă e permis) sau `tokens.decode` + `tokens.is_revoked` + contul din bază → `schemas.User`; `InvalidToken` → 401 `unauthorized`.
5. `deps.current_user` devine `async` și primește sesiunea + setările; restul dependențelor (`require_roles`, `crew_access`) rămân la fel.
6. `logout`: `tokens.revoke(session, claims.jti, expires_at)` + `access_log.write(logout)`.
7. Routerul `auth.py`: corpurile apelează serviciul; scoate `_HASHES` și citirea din `examples.USERS`.
8. Teste: login corect dă un token real care merge la `/auth/me`; după logout același token dă 401; parola altui cont dă 401; 5 greșeli dau 429; `mock-specialist2` merge cu `ALLOW_MOCK_TOKENS=true` și dă 401 cu `false`.

## Fișierele atinse

- `app/services/auth.py`
- `app/routers/auth.py`
- `app/deps.py`
- `tests/security/test_auth_flow.py` (nou)

## Gata când

- [ ] `uv run pytest -q` (din `backend/`) → toate trec
- [ ] `uv run --project backend python scripts/smoke.py` (din rădăcina repo-ului) → `OK` (smoke folosește tokenuri mock)
- [ ] `role` și `crew_id` vin doar din token, nu din cerere
- [ ] `uv run ruff check app tests` → fără erori
- [ ] PR mic, titlul `backend: T07 autentificarea reală`

## Nu face

- Nu scrie criptografie: folosește `security/tokens.py`, `passwords.py`, `lockout.py`.
- Nu schimba forma răspunsului `LoginResponse`.

## Capcane

- `current_user` devenit `async` cu `Depends(get_session)`: FastAPI le înlănțuie singur; nu deschide sesiuni manual în dependență.

## Regula generală

Schimbi doar corpul funcțiilor. Căile, parametrii, `response_model` și erorile routerelor, `schemas.py`,
`ai_schemas.py`, `datafiles.py` și semnăturile din `security/` sunt contract. Mock-ul rămâne funcțional
pentru tot ce nu ține de acest task.
