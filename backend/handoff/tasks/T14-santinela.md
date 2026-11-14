# T14 — Pilonul Santinela (NightSignal)

**Cine:** B · **Prioritate:** P0 · **Durată estimată:** ~45 min · **Depinde de:** T12, T13 · **Deblochează:** T15

## Ce construiești

Regula NightSignal (Alavi et al. 2022) pe pulsul de noapte, față de mediana personală: galben la o noapte ≥ +3 bpm, roșu la două nopți la rând ≥ +4 bpm. Plus indicele de stres și scorul pilonului.

## De citit (atașează-le lui Claude)

- `backend/handoff/01_CONTEXT.md` (mereu)
- `backend/app/engine/pillars/immune.py` (schelet)
- `data/parameters.json`: `nightsignal_yellow_delta`, `nightsignal_red_delta_bpm`, `nightsignal_red_consecutive_nights`, `nightsignal_min_nights_baseline`
- `data/catalog/recommendations.json`: `immune-1-1`, `immune-2-1`

## Pași

1. Baseline-ul: nopțile **de dinainte** de cea evaluată (fără zilele cu alertă imunitară), `min_n = nightsignal_min_nights_baseline` (7).
2. Delta = pulsul nopții − mediana.
3. Roșu: ultimele `red_nights` (2) nopți toate ≥ `red_delta` (4) → `Finding(level=2, status="alert", recommendation_id="immune-2-1")`.
4. Altfel galben: ultima noapte ≥ `yellow_delta` (3) → `Finding(level=1, status="watch", recommendation_id="immune-1-1")`.
5. Titlul în română cu cifrele: „Puls de noapte +7 bpm, 3 nopți la rând”; dovezile (`EvidenceItem`) pentru puls, temperatură și somn.
6. `stress_index`: 0..100 (o combinație simplă, documentată în docstring); `score`: 100 − penalizare după delta.
7. Teste în `tests/engine/test_immune.py` cu serii scrise de mână: o noapte +4 → galben; două nopți +4 → roșu; +3,9 și +4 → nu roșu; baseline-ul nu e gata (5 nopți) → None; **și pe scenariu**: cm-2 galben în ziua 94, roșu în ziua 95.

## Fișierele atinse

- `app/engine/pillars/immune.py`
- `tests/engine/test_immune.py` (nou)

## Gata când

- [ ] `uv run pytest tests/engine/test_immune.py -q`
- [ ] testul `test_nightsignal_red_after_two_nights` există (apare în ecranul Evidence)
- [ ] `uv run ruff check app tests` → fără erori
- [ ] PR mic, titlul `backend: T14 pilonul santinela (nightsignal)`

## Nu face

- Nu scrie pragurile în cod: le primești ca parametri.

## Regula generală

Schimbi doar corpul funcțiilor. Căile, parametrii, `response_model` și erorile routerelor, `schemas.py`,
`ai_schemas.py`, `datafiles.py` și semnăturile din `security/` sunt contract. Mock-ul rămâne funcțional
pentru tot ce nu ține de acest task.
