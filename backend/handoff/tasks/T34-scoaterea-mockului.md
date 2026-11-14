# T34 — Scoaterea mock-ului și verificarea finală

**Cine:** A+B · **Prioritate:** P0 · **Durată estimată:** ~45 min · **Depinde de:** toate · **Deblochează:** —

## Ce construiești

Niciun router nu mai folosește `app/examples.py`; fișierul se șterge; `/health` spune `mode: real`; toate verificările trec pe backend-ul real.

## De citit (atașează-le lui Claude)

- `backend/handoff/01_CONTEXT.md` (mereu)
- `backend/handoff/04_SCHELET.md` (ce a rămas „mock”)
- `scripts/smoke.py`

## Pași

1. `grep -rn "examples" app/` → fiecare utilizare rămasă se înlocuiește cu serviciul ei.
2. Șterge `app/examples.py`; `/health` → `"mode": "real"`.
3. `ALLOW_MOCK_TOKENS`: rămâne `true` doar dacă frontend-ul încă folosește tokenuri mock; altfel `false` în `.env` de demo (smoke.py folosește mock — rulează-l cu `ALLOW_MOCK_TOKENS=true`).
4. Regenerează documentele: `scripts/build_docs.py`, `scripts/build_handoff.py`, `scripts/gen_types.sh`.
5. Repetă demo-ul complet cu frontend-ul pornit.
6. Lista finală: niciun `NotImplementedError` rămas pe drumul demo-ului (`grep -rn NotImplementedError app/`).

## Fișierele atinse

- toate

## Gata când

- [ ] `uv run pytest -q` (din `backend/`) → toate trec
- [ ] `uv run --project backend python scripts/smoke.py` (din rădăcina repo-ului) → `OK`
- [ ] `grep -rn "examples\|NotImplementedError" app/` nu găsește nimic pe drumul demo-ului
- [ ] demo-ul merge cap-coadă de două ori la rând
- [ ] `uv run ruff check app tests` → fără erori
- [ ] PR mic, titlul `backend: T34 scoaterea mock-ului și verificarea finală`

## Regula generală

Schimbi doar corpul funcțiilor. Căile, parametrii, `response_model` și erorile routerelor, `schemas.py`,
`ai_schemas.py`, `datafiles.py` și semnăturile din `security/` sunt contract. Mock-ul rămâne funcțional
pentru tot ce nu ține de acest task.
