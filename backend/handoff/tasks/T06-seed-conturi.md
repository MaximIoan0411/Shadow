# T06 — Seed: echipaj și conturi

**Cine:** A · **Prioritate:** P0 · **Durată estimată:** ~30 min · **Depinde de:** T03, T04 · **Deblochează:** T07, T11

## Ce construiești

La pornire există cei 4 membri ai echipajului și cele 5 conturi din `backend/seed/users.json`, cu parolele doar ca hash.

## De citit (atașează-le lui Claude)

- `backend/handoff/01_CONTEXT.md` (mereu)
- `backend/app/db/seed.py` (schelet)
- `backend/seed/users.json`
- `backend/app/security/passwords.py`
- `handoff/03_BAZA_DE_DATE.md` (crew, users)

## Pași

1. `seed_crew_and_users`: citește JSON-ul; creează `Crew` pentru fiecare cont cu `crew_id` (titlul rolului: din `display_name` sau o hartă mică).
2. `await session.flush()` după echipaj (cheile străine!).
3. Pentru fiecare cont: `password_hash = await asyncio.to_thread(passwords.hash, u["test_password"])`; creează `User`.
4. Apelează funcția din `lifespan`, în `async with db.SessionLocal() as s:` + `await s.commit()`.
5. Test: după pornire, `users` are 5 rânduri, `crew` 4, iar niciun `password_hash` nu conține parola în clar.

## Fișierele atinse

- `app/db/seed.py`
- `app/main.py`
- `tests/routers/test_seed.py` (nou)

## Gata când

- [ ] `uv run pytest -q` (din `backend/`) → toate trec
- [ ] `uv run --project backend python scripts/smoke.py` (din rădăcina repo-ului) → `OK`
- [ ] `uv run ruff check app tests` → fără erori
- [ ] PR mic, titlul `backend: T06 seed: echipaj și conturi`

## Capcane

- Hash-ul e lent intenționat (~50 ms): 5 conturi sunt OK; nu-l apela fără `to_thread`.

## Regula generală

Schimbi doar corpul funcțiilor. Căile, parametrii, `response_model` și erorile routerelor, `schemas.py`,
`ai_schemas.py`, `datafiles.py` și semnăturile din `security/` sunt contract. Mock-ul rămâne funcțional
pentru tot ce nu ține de acest task.
