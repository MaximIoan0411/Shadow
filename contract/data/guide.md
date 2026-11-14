# SHADOW — contractul backend ↔ data/

Folderul `data/` ține **conținutul** aplicației: pragurile cu sursele lor, catalogul de recomandări, textele
explicative, mediile, evenimentul solar real și scenariul misiunii. Nu are cod. Îl citesc backend-ul (toate
fișierele) și serviciul AI (catalogul și sursele, pentru corpus).

Formatul fiecărui fișier e definit ca model Pydantic în `backend/app/datafiles.py`. Din el se generează JSON
Schema în `contract/data/schemas/`, pe care le pot folosi editoarele pentru completare automată și validare.

## Fișierele

| Fișier | Model | JSON Schema | Ce conține |
|---|---|---|---|
{{FILES_TABLE}}

## Regulile

1. **Nicio cifră fără sursă.** O valoare aleasă de echipă e marcată „derivat”; una neverificată, „NEVERIFICAT”
   (sau `verification = "unverified"`) și se prezintă ca ipoteză.
2. **Schimbările de format se anunță** (câmp nou obligatoriu, câmp redenumit, tip schimbat): strică încărcarea.
   **Schimbările de conținut** (un text corectat, un prag actualizat cu sursa lui) se pot face oricând.
3. **Fișierele se validează în trei locuri:** la pornirea backend-ului (oprește pornirea, cu lista tuturor
   problemelor), în `scripts/smoke.py` și cu `scripts/validate_data.py`.
4. **Textele pentru utilizator sunt în română**, cel mult două propoziții fiecare, gata de afișat.
5. **`min` și `max` din `checkin_indicators.json` sunt limitele fizic posibile**, nu cele normale. Le folosesc și
   check-in-ul (valori imposibile → `rejected`), și validarea echipei de securitate.

## Cum se încarcă

```python
from app.datafiles import load_all

data = load_all()                         # DATA_DIR din mediu, altfel data/ din rădăcina repo-ului
data.params.value("nightsignal_red_delta_bpm")        # → 4
data.params.key_threshold_ids()                       # cele 33 de praguri folosite de motor
data.catalog.by_id()["immune-2-1"].action             # textul recomandării
data.catalog.first(AlertTopic.immune, level=2)        # prima recomandare pentru subiect și nivel
data.environments.default                             # "mars_transit"
data.scenario.start_day                               # 96
```

`load_all()` verifică și legăturile dintre fișiere: pragurile din `praguri_cheie_triaj` există, mediul din
scenariu există, evenimentul solar din scenariu e cel din fișierul DONKI, sursa dozei fiecărui mediu există în
`parameters.json`.

```bash
uv run --project backend python scripts/validate_data.py     # „OK” sau lista problemelor
```

## Ce NU stă în data/

| Ce | Unde |
|---|---|
| conturile de test | `backend/seed/users.json` |
| cheile | nicăieri în git (`security/keys/generate_keys.py`) |
| documentele NASA pentru AI | `ai/corpus/` |
| baza de date | se creează la pornirea backend-ului |
| cod | `backend/`, `ai/` |

## Observații despre fișierele actuale

- `catalog/recommendations.json` e construit din `parameters.json` → `piloni.*.recomandari` (50 de recomandări).
  Recomandarea despre conjuncția solară (subiectul „comunicare”) nu are subiect în contract și a rămas doar în
  `parameters.json`.
- `steps` (pașii planului) există pentru `immune-1-1`, `immune-2-1`, `behavioral-1-1` și `radiation-1-1`, cele
  din demo. Pentru restul, backend-ul împarte `action` în propoziții.
- `keystroke_baseline_duration` avea valoarea `null`; e acum 7 zile, marcat „derivat” (ales de echipă).
- Forma curbei de radiații din simulator e sintetică; din `donki/donki_sep_event.json` se folosesc doar orele și
  identificatorii evenimentului real.

---

## Modelele

Generate din `backend/app/datafiles.py`. Unde un model refolosește un model din contractul API (de exemplu
`CheckinIndicator`, `EnvironmentInfo`, `Recommendation`), descrierea completă a câmpurilor e și în
`contract/api/README.md`.

{{MODELS}}
