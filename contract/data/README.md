# SHADOW — contractul backend ↔ data/

Folderul `data/` ține **conținutul** aplicației: pragurile cu sursele lor, catalogul de recomandări, textele
explicative, mediile, evenimentul solar real și scenariul misiunii. Nu are cod. Îl citesc backend-ul (toate
fișierele) și serviciul AI (catalogul și sursele, pentru corpus).

Formatul fiecărui fișier e definit ca model Pydantic în `backend/app/datafiles.py`. Din el se generează JSON
Schema în `contract/data/schemas/`, pe care le pot folosi editoarele pentru completare automată și validare.

## Fișierele

| Fișier | Model | JSON Schema | Ce conține |
|---|---|---|---|
| `data/parameters.json` | [ParametersFile](#parametersfile) | `schemas/parameters.schema.json` | data/parameters.json — pragurile, fiecare cu sursa lui. |
| `data/environments.json` | [EnvironmentsFile](#environmentsfile) | `schemas/environments.schema.json` | data/environments.json — cele 4 medii ale comutatorului. |
| `data/texts/checkin_indicators.json` | [CheckinIndicatorsFile](#checkinindicatorsfile) | `schemas/texts__checkin_indicators.schema.json` | data/texts/checkin_indicators.json — câmpurile check-in-ului. `min`/`max` = limitele FIZIC posibile. |
| `data/texts/body_functions.json` | [BodyFunctionsFile](#bodyfunctionsfile) | `schemas/texts__body_functions.schema.json` | data/texts/body_functions.json — exact 4 intrări, câte una pe pilon. |
| `data/catalog/recommendations.json` | [CatalogFile](#catalogfile) | `schemas/catalog__recommendations.schema.json` | data/catalog/recommendations.json. |
| `data/scenario/scenario.json` | [ScenarioFile](#scenariofile) | `schemas/scenario__scenario.schema.json` | data/scenario/scenario.json — ce se întâmplă în fiecare zi a misiunii simulate. |
| `data/donki/donki_sep_event.json` | [DonkiFile](#donkifile) | `schemas/donki__donki_sep_event.schema.json` | data/donki/donki_sep_event.json — evenimentul real NASA DONKI (11 mai 2024). |

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

### Enumerări (valori fixe)

#### AlertTopic

Subiectul unei alerte: un pilon, radiațiile sau un semnal încrucișat.

| Valoare | Înseamnă |
|---|---|
| `behavioral` |  |
| `cardio` |  |
| `immune` |  |
| `musculoskeletal` |  |
| `radiation` |  |
| `cross_signal` |  |

#### Hazard

Cele 5 pericole NASA HRP.

| Valoare | Înseamnă |
|---|---|
| `radiation` |  |
| `isolation` |  |
| `distance` |  |
| `gravity` |  |
| `hostile_environment` |  |

#### Pillar

Cei patru piloni. Fiecare are o zonă pe corpul interactiv.

| Valoare | Înseamnă |
|---|---|
| `behavioral` |  |
| `cardio` |  |
| `immune` |  |
| `musculoskeletal` |  |

#### Derivation

| Valoare | Înseamnă |
|---|---|
| `published` |  |
| `derived` |  |

#### EnvironmentId

| Valoare | Înseamnă |
|---|---|
| `iss` |  |
| `moon_base` |  |
| `mars_transit` |  |
| `mars_base` |  |

#### Verification

| Valoare | Înseamnă |
|---|---|
| `verified` |  |
| `unverified` |  |

### Obiecte

#### CheckinIndicator

Descrierea unui câmp din check-in. Frontend-ul construiește formularul din lista asta.

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `key` | text | da |  Ex.: `"systolic_mmhg"` |
| `label` | text | da |  Ex.: `"Tensiunea (sistolică)"` |
| `unit` | text | da |  Ex.: `"mmHg"` |
| `input` | `"number"` \| `"scale_1_5"` \| `"choice"` | da |  |
| `min` | număr \| null | nu | Sub această valoare, câmpul e respins ca imposibil. |
| `max` | număr \| null | nu | Peste această valoare, câmpul e respins ca imposibil. |
| `step` | număr \| null | nu |  |
| `choices` | listă de text \| null | nu | Doar pentru input = choice. |
| `required` | true/false | nu |  |
| `how_to_measure` | text | da | Coloana „Cum se măsoară”. |
| `what_it_means` | text | da | Coloana „Ce înseamnă valoarea”. |
| `why_in_space` | text | da | Coloana „De ce contează în spațiu”. |
| `pillar` | [Pillar](#pillar) \| null | nu |  |
| `source` | [SourceRef](#sourceref) \| null | nu |  |

#### SourceRef

O sursă științifică. Apare lângă orice prag, text sau recomandare.

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `citation` | text | da |  Ex.: `"Alavi et al. (2022), Nature Medicine 28:175–184"` |
| `url` | text | da |  Ex.: `"https://www.nature.com/articles/s41591-021-01593-2"` |
| `verification` | [Verification](#verification) | nu |  |
| `derivation` | [Derivation](#derivation) | nu |  |
| `evidence_strength` | text \| null | nu | puternică / moderată / slabă / analog terestru / doar animale Ex.: `"moderată"` |

#### ParamSource

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `citare` | text | da |  |
| `doi` | text \| null | nu |  |
| `url` | text \| null | nu |  |

#### Param

Un parametru. `valoare` poate fi număr, text, listă, dicționar sau null — motorul citește doar pragurile cheie.

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `id` | text | da |  |
| `nume` | text | da |  |
| `valoare` | orice | da |  |
| `unitate` | text | da |  |
| `explicatie` | text | da |  |
| `status` | `"VERIFICAT"` \| `"NEVERIFICAT"` | da |  |
| `derivare` | `"publicat"` \| `"derivat"` | da |  |
| `nota_derivare` | text | nu |  |
| `forta_dovezii` | text | da |  |
| `relativ_la_baseline` | true/false | nu |  |
| `verificat_cum` | text | nu |  |
| `sursa` | [ParamSource](#paramsource) | da |  |
| `surse_suplimentare` | listă de orice | nu |  |

#### HrpRisk

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `nume` | text | da |  |
| `url` | text | da |  |

#### ParamRecommendation

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `nivel` | `"1_singur"` \| `"2_ofiter_medical"` \| `"3_pamant"` | da |  |
| `declansator` | text | da |  |
| `actiune` | text | da |  |
| `risc_hrp` | text | da |  |
| `risc_hrp_url` | text | da |  |
| `status` | `"VERIFICAT"` \| `"NEVERIFICAT"` | da |  |
| `sursa` | [ParamSource](#paramsource) | da |  |
| `nota` | text \| null | nu |  |

#### ParamPillar

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `titlu` | text | da |  |
| `riscuri_hrp` | listă de [HrpRisk](#hrprisk) | da |  |
| `parametri` | listă de [Param](#param) | da |  |
| `recomandari` | listă de [ParamRecommendation](#paramrecommendation) | da |  |

#### ParametersFile

data/parameters.json — pragurile, fiecare cu sursa lui.

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `meta` | obiect | da |  |
| `praguri_cheie_triaj` | obiect {cheie: listă de text} | da | Pe subiect: id-urile pragurilor folosite direct de motor. |
| `piloni` | obiect {cheie: [ParamPillar](#parampillar)} | da |  |
| `eveniment_sep_simulator` | obiect | da |  |
| `corecturi_plan` | obiect | nu |  |
| `note_dovezi_slabe` | obiect | nu |  |

#### EnvironmentEntry

Un mediu. Câmpurile din EnvironmentInfo ajung direct la frontend; restul sunt doar pentru backend.

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `id` | [EnvironmentId](#environmentid) | da |  |
| `name` | text | da |  Ex.: `"Tranzit spre Marte"` |
| `one_way_delay_s` | număr | da | Întârzierea legăturii într-un sens, în secunde de MISIUNE. Ex.: `700` |
| `gravity_g` | număr | da | Gravitația, în g. Ex.: `0.0` |
| `baseline_dose_usv_h` | număr | da | Rata de doză de fond pentru simulator, µSv/h. Ex.: `65.8` |
| `emphasized_hazards` | listă de [Hazard](#hazard) | da | Pericolele care contează cel mai mult în acest mediu. |
| `description` | text | da |  |
| `delay_range_s` | pereche (număr, număr) \| null | nu | Intervalul real al întârzierii într-un sens (Marte: 3–22 min). `one_way_delay_s` e valoarea folosită în demo. (min elemente 2; max elemente 2) |
| `dose_source_param` | text \| null | nu | Id-ul din parameters.json de unde vine doza de fond. |
| `sources` | listă de [SourceRef](#sourceref) | nu |  |

#### EnvironmentsFile

data/environments.json — cele 4 medii ale comutatorului.

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `default` | text | da | Id-ul mediului la pornire. |
| `environments` | listă de [EnvironmentEntry](#environmententry) | da |  |

#### CheckinIndicatorsFile

data/texts/checkin_indicators.json — câmpurile check-in-ului. `min`/`max` = limitele FIZIC posibile.

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `indicators` | listă de [CheckinIndicator](#checkinindicator) | da |  |

#### BodyFunction

Textele panoului unei zone a corpului (cerință din brief: funcția părții corpului).

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `pillar` | [Pillar](#pillar) | da |  |
| `name` | text | da |  Ex.: `"Santinela"` |
| `body_zone` | `"brain"` \| `"heart"` \| `"immune"` \| `"bones"` | da |  |
| `function_text` | text | da | Max. 2 propoziții. |
| `hazard` | [Hazard](#hazard) | da |  |
| `hazard_text` | text | da |  |
| `limits_text` | text | da |  |
| `sources` | listă de [SourceRef](#sourceref) | nu |  |

#### BodyFunctionsFile

data/texts/body_functions.json — exact 4 intrări, câte una pe pilon.

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `pillars` | listă de [BodyFunction](#bodyfunction) | da |  |

#### CatalogEntry

O recomandare din catalog. Câmpurile din Recommendation ajung la frontend; `steps` și `recheck_days`
le folosește backend-ul ca să construiască planul alertei.

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `id` | text | da | Format: <topic>-<nivel>-<nr>, ex. `immune-2-1`. Ex.: `"immune-2-1"` |
| `topic` | [AlertTopic](#alerttopic) | da |  |
| `level` | `1` \| `2` \| `3` | da |  |
| `trigger` | text | da | Când se aplică. |
| `action` | text | da | Ce are de făcut. |
| `hrp_risk` | text | da | Riscul NASA HRP corespunzător. |
| `hrp_risk_url` | text | da |  |
| `source` | [SourceRef](#sourceref) | da |  |
| `steps` | listă de text \| null | nu | Pașii planului (2–4). Lipsă = backend-ul împarte `action` în propoziții. |
| `recheck_days` | număr întreg | nu | După câte zile se reverifică alerta. (min 1; max 3) |
| `note` | text \| null | nu |  |

#### CatalogFile

data/catalog/recommendations.json.

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `recommendations` | listă de [CatalogEntry](#catalogentry) | da |  |

#### ScenarioEvent

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `days` | pereche (număr întreg, număr întreg) | da | Prima și ultima zi, inclusiv. (min elemente 2; max elemente 2) |
| `crew` | `"all"` \| listă de text \| text | da | `all`, un crew_id sau o listă. |
| `kind` | `"poor_sleep"` \| `"skipped_exercise"` \| `"infection_onset"` \| `"keystroke_slowdown"` \| `"solar_storm"` \| `"cardio_deconditioning"` | da |  |
| `params` | obiect | nu | Mărimea efectului, specifică fiecărui `kind`. |
| `note` | text | nu |  |

#### ScenarioFile

data/scenario/scenario.json — ce se întâmplă în fiecare zi a misiunii simulate.

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `seed` | număr întreg | da |  |
| `total_days` | număr întreg | nu |  |
| `start` | dată-oră (ISO 8601) | da | Ora 00:00 a zilei 1, UTC. |
| `start_day` | număr întreg | nu | Ziua în care pornește ceasul live; zilele de dinainte se generează la pornire. |
| `start_time` | text | nu |  (format ^\d{2}:\d{2}$) |
| `environment` | text | nu |  |
| `crew_baselines` | obiect {cheie: obiect {cheie: număr}} | da | Pe crew_id: normalul personal pe fiecare cheie de metrică. |
| `events` | listă de [ScenarioEvent](#scenarioevent) | da |  |

#### DonkiSep

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `sepID` | text | da |  |
| `eventTime` | text | da |  |
| `link` | text | da |  |
| `instruments` | listă de obiect | da |  |

#### DonkiFile

data/donki/donki_sep_event.json — evenimentul real NASA DONKI (11 mai 2024).

| Câmp | Tip | Obligatoriu | Descriere |
|---|---|---|---|
| `source` | text | da |  |
| `chosen_sep` | [DonkiSep](#donkisep) | da |  |
| `linked_cme` | listă de obiect | nu |  |

