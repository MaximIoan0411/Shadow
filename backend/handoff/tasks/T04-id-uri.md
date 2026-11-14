# T04 — Id-urile cu prefix

**Cine:** A · **Prioritate:** P0 · **Durată estimată:** ~20 min · **Depinde de:** T03 · **Deblochează:** T06

## Ce construiești

`next_id(session, "al")` dă `al-0001`, `al-0002`…, iar `next_seq(session, "down")` dă 1, 2…, cu contorul în `sim_state`, în aceeași tranzacție.

## De citit (atașează-le lui Claude)

- `backend/handoff/01_CONTEXT.md` (mereu)
- `backend/app/ids.py` (schelet)
- `backend/app/db/models/sim.py`

## Pași

1. Citește rândul `id:<prefix>` din `sim_state` (`session.get(SimState, key)`); dacă lipsește, pornește de la 0.
2. Crește `n`, scrie înapoi (**atribuie un dict nou**, nu modifica dict-ul pe loc: JSON-ul nu se detectează ca schimbat).
3. Formatează cu `WIDTH` cifre: `f"{prefix}-{n:0{WIDTH}d}"`.
4. `next_seq` la fel, cu cheia `seq:<direction>`.
5. Teste: trei apeluri dau 0001, 0002, 0003; prefixe diferite au contoare separate; după rollback contorul nu a crescut.

## Fișierele atinse

- `app/ids.py`
- `tests/routers/test_ids.py` (nou)

## Gata când

- [ ] `uv run pytest -q` (din `backend/`) → toate trec
- [ ] `uv run ruff check app tests` → fără erori
- [ ] PR mic, titlul `backend: T04 id-urile cu prefix`

## Capcane

- `sim_state.value["n"] += 1` NU se salvează: SQLAlchemy nu vede schimbările în interiorul unui JSON. Atribuie `row.value = {"n": n}`.

## Regula generală

Schimbi doar corpul funcțiilor. Căile, parametrii, `response_model` și erorile routerelor, `schemas.py`,
`ai_schemas.py`, `datafiles.py` și semnăturile din `security/` sunt contract. Mock-ul rămâne funcțional
pentru tot ce nu ține de acest task.
