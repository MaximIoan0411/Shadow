# T33 — Demo: reset, salt de zi, atacuri

**Cine:** A · **Prioritate:** P0 · **Durată estimată:** ~60 min · **Depinde de:** T24 · **Deblochează:** —

## Ce construiești

Butoanele de demo merg pe date reale: `/sim/reset` reface totul (ziua 96) în câteva secunde, `PUT /sim/clock` sare înainte, pachetul falsificat e respins de coadă, senzorul înghețat e respins de validare.

## De citit (atașează-le lui Claude)

- `backend/handoff/01_CONTEXT.md` (mereu)
- `backend/app/routers/demo.py`, `routers/mission.py` (sim/clock)
- `backend/app/services/demo.py` (schelet)
- `backend/app/main.py` (lifespan)
- `security/attacks/` (scripturile echipei de securitate)

## Pași

1. Extrage din `lifespan` o funcție `bootstrap(app)` (bază + seed + istoric + replay + ceas) și una `start_tasks / stop_tasks`.
2. `/sim/reset`: `stop_tasks` → golește tabelele (sau `drop_all` + `create_all`) → `bootstrap` → `start_tasks` → `lockout.reset_all()` → `dashboard.changed` (`reason="reset"`) și `mission.tick`. Țintă: sub 5 s.
3. `PUT /sim/clock` cu `mission_day` (înainte): generează zilele lipsă cu `scenario.generate(from_day=curent+1, to_day=nou)`, scrie-le, rulează `pipeline` pe ele, apoi `clock.jump_to_day`; `dashboard.changed` (`reason="jump"`).
4. `/demo/inject-spoof`: creează un pachet `down` sigilat cu `sender="attacker"` (varianta provizorie a `sealing` îl respinge; cea reală, prin cheia greșită) → planificatorul îl respinge → `packet.rejected`.
5. `/demo/frozen-sensor`: trimite prin `ingest` de 20 de ori aceeași valoare → a 20-a e respinsă.
6. Teste: după reset, ziua e 96 și alertele sunt cele din replay; saltul la ziua 98 creează zilele 97–98; pachetul falsificat ajunge `rejected`.

## Fișierele atinse

- `app/services/demo.py`
- `app/routers/demo.py`
- `app/routers/mission.py`
- `app/main.py`
- `tests/routers/test_demo.py` (nou)

## Gata când

- [ ] `uv run pytest -q` (din `backend/`) → toate trec
- [ ] `uv run --project backend python scripts/smoke.py` (din rădăcina repo-ului) → `OK`
- [ ] repetiția completă a demo-ului de două ori la rând, cu `/sim/reset` între ele
- [ ] `uv run ruff check app tests` → fără erori
- [ ] PR mic, titlul `backend: T33 demo: reset, salt de zi, atacuri`

## Regula generală

Schimbi doar corpul funcțiilor. Căile, parametrii, `response_model` și erorile routerelor, `schemas.py`,
`ai_schemas.py`, `datafiles.py` și semnăturile din `security/` sunt contract. Mock-ul rămâne funcțional
pentru tot ce nu ține de acest task.
