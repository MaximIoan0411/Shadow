# 03 — Baza de date

**Generat** de `scripts/build_handoff.py` din `backend/app/db/models/`. Nu editați de mână; schimbați modelele.

## Reguli

- **SQLite, asincron** (`aiosqlite`), mod WAL, `foreign_keys=ON`, `busy_timeout=5000` (`app/db/session.py`).
- **Fără migrări:** baza se șterge și se recreează la fiecare pornire (`RESET_DB_ON_START=true`), cu `create_all()`
  și seed. Schimbi un model → repornești. Nu se comite niciun fișier `.sqlite`.
- **Datele-oră** sunt `UTCDateTime`: refuză o dată fără fus orar; toate sunt **timp de misiune** (`clock.now()`).
- **Id-urile** cu prefix (`al-0001`, `pk-0007`) le dă `app/ids.py` (contor în `sim_state`), în tranzacția scrierii.
- **Relațiile** au `lazy="raise"`: încărcați-le cu `selectinload(...)`. În asincron, accesul leneș dă eroare.
- **Ordinea inserărilor:** fără relații ORM, într-un singur `flush()` ordinea nu e garantată. Inserați întâi
  `crew`, apoi `await session.flush()`, apoi restul (altfel: `FOREIGN KEY constraint failed`).
- **Câmpurile JSON** sunt pentru date citite întregi; tot ce apare într-un `WHERE` e coloană normală.
- **Verificat** pe un fișier SQLite real: create_all, cheile străine, unicitatea check-in-ului pe zi,
  unicitatea (direction, seq) a pachetelor (blochează replay-ul), relațiile cu `selectinload`, fusul orar UTC.

## Tabelele

### `access_log` — `AccessLog` (security.py)

hash = SHA-256(prev_hash + JSON canonic al intrării), primele 16 caractere (security.access_log.entry_hash). NU există UPDATE sau DELETE pe acest tabel.

| Coloană | Tip | Null | Cheie | Implicit | Notă |
|---|---|---|---|---|---|
| `id` | Integer | nu | PK |  |  |
| `at` | UTCDateTime | nu |  |  |  |
| `actor` | String(80) | nu |  |  |  |
| `actor_role` | String(12) | nu |  |  |  |
| `action` | String(24) | nu |  |  |  |
| `resource` | String(120) | nu |  |  |  |
| `crew_id` | String(16) | da |  |  |  |
| `outcome` | String(8) | nu |  |  | allowed \| denied |
| `prev_hash` | String(16) | nu |  |  |  |
| `hash` | String(16) | nu |  |  |  |

Constrângeri și indecși: INDEX `ix_access_log_crew_id` (crew_id)

### `alert_history` — `AlertHistory` (alerts.py)

| Coloană | Tip | Null | Cheie | Implicit | Notă |
|---|---|---|---|---|---|
| `id` | Integer | nu | PK |  |  |
| `alert_id` | String(16) | nu | FK → `alerts.id` |  |  |
| `at` | UTCDateTime | nu |  |  |  |
| `actor` | String(80) | nu |  |  | display_name sau "SHADOW" |
| `role` | String(12) | da |  |  |  |
| `action` | String(16) | nu |  |  | created \| acknowledged \| step_done \| escalated \| packet_sent \| earth_replied \| rechecked \| resolved |
| `note` | Text | da |  |  |  |

Constrângeri și indecși: INDEX `ix_alert_history_alert_id` (alert_id)

Relații: `alert` → Alert (lazy=raise)

### `alerts` — `Alert` (alerts.py)

| Coloană | Tip | Null | Cheie | Implicit | Notă |
|---|---|---|---|---|---|
| `id` | String(16) | nu | PK |  | "al-1042" |
| `crew_id` | String(16) | nu | FK → `crew.id` |  |  |
| `topic` | String(20) | nu |  |  | AlertTopic |
| `level` | Integer | nu |  |  | 1 \| 2 \| 3 |
| `status` | String(8) | nu |  |  | watch \| alert |
| `state` | String(14) | nu |  |  | active \| acknowledged \| escalated \| resolved |
| `title` | String(160) | nu |  |  |  |
| `explanation` | Text | nu |  |  |  |
| `cause` | String(14) | nu |  | `'unknown'` | individual \| environmental \| unknown |
| `cause_explanation` | Text | nu |  | `''` |  |
| `evidence` | JSON | nu |  | `[]` | listă de Evidence |
| `recommendation_id` | String(32) | nu |  |  | din data/catalog/recommendations.json |
| `recheck_at` | UTCDateTime | da |  |  |  |
| `packet_id` | String(16) | da |  |  |  |
| `earth_reply` | Text | da |  |  |  |
| `created_at` | UTCDateTime | nu |  |  |  |
| `updated_at` | UTCDateTime | nu |  |  |  |
| `mission_day` | Integer | nu |  |  |  |

Constrângeri și indecși: INDEX `ix_alert_crew_topic_state` (crew_id, topic, state)

Relații: `steps` → PlanStep (lazy=raise); `history` → AlertHistory (lazy=raise)

### `checkins` — `Checkin` (measurements.py)

Check-in-ul de dimineață. UNUL pe zi de misiune (al doilea îl înlocuiește). Câmpurile respinse sunt NULL, iar motivele stau în `rejected` (listă de FieldRejection, ca JSON).

| Coloană | Tip | Null | Cheie | Implicit | Notă |
|---|---|---|---|---|---|
| `id` | String(16) | nu | PK |  | "ck-0096" |
| `crew_id` | String(16) | nu | FK → `crew.id` |  |  |
| `mission_day` | Integer | nu |  |  |  |
| `created_at` | UTCDateTime | nu |  |  |  |
| `mood` | Integer | nu |  |  | 1..5 |
| `systolic_mmhg` | Float | da |  |  |  |
| `diastolic_mmhg` | Float | da |  |  |  |
| `pulse_bpm` | Float | da |  |  |  |
| `glucose_mg_dl` | Float | da |  |  |  |
| `temperature_c` | Float | da |  |  |  |
| `sleep_hours` | Float | da |  |  |  |
| `meals_eaten` | String(8) | da |  |  | all \| some \| none |
| `note` | Text | da |  |  |  |
| `source` | String(12) | nu |  | `'manual'` | manual \| simulated (istoricul) |
| `rejected` | JSON | nu |  | `[]` |  |

Constrângeri și indecși: UNIQUE (crew_id, mission_day); INDEX `ix_checkins_crew_id` (crew_id)

### `crew` — `Crew` (users.py)

Un membru al echipajului. 4 rânduri, din seed. id = "cm-1" … "cm-4".

| Coloană | Tip | Null | Cheie | Implicit | Notă |
|---|---|---|---|---|---|
| `id` | String(16) | nu | PK |  |  |
| `display_name` | String(80) | nu |  |  |  |
| `initials` | String(4) | nu |  |  |  |
| `role_title` | String(80) | nu |  |  |  |
| `is_cmo` | Boolean | nu |  | `False` |  |

### `exercise_sessions` — `ExerciseSession` (measurements.py)

O sesiune de exerciții. `sets` = listă de ExerciseSet (exercise, reps, load_kg), ca JSON.

| Coloană | Tip | Null | Cheie | Implicit | Notă |
|---|---|---|---|---|---|
| `id` | String(16) | nu | PK |  | "ex-0211" |
| `crew_id` | String(16) | nu | FK → `crew.id` |  |  |
| `mission_day` | Integer | nu |  |  |  |
| `kind` | String(12) | nu |  |  | resistance \| aerobic |
| `started_at` | UTCDateTime | nu |  |  |  |
| `duration_min` | Float | nu |  |  |  |
| `sets` | JSON | nu |  | `[]` |  |
| `loading_score` | Float | nu |  |  |  |
| `source` | String(12) | nu |  |  |  |

Constrângeri și indecși: INDEX `ix_ex_crew_day` (crew_id, mission_day)

### `keystroke_sessions` — `KeystrokeSession` (measurements.py)

O sesiune de tastare: loturile cu același session_id se ADUNĂ aici. FĂRĂ caractere, doar sume de timpi. Acumulatorii (sum, sumsq) permit medii și deviații corecte când vin loturi noi; câmpurile *_mean/*_sd sunt recalculate din ei la fiecare lot.

| Coloană | Tip | Null | Cheie | Implicit | Notă |
|---|---|---|---|---|---|
| `session_id` | String(64) | nu | PK |  |  |
| `crew_id` | String(16) | nu | FK → `crew.id` |  |  |
| `context` | String(16) | nu |  |  | free_typing \| checkin_note \| ai_chat \| demo |
| `started_at` | UTCDateTime | nu |  |  |  |
| `updated_at` | UTCDateTime | nu |  |  |  |
| `mission_day` | Integer | nu |  |  |  |
| `n_keys` | Integer | nu |  | `0` |  |
| `hold_sum` | Float | nu |  | `0.0` |  |
| `hold_sumsq` | Float | nu |  | `0.0` |  |
| `flight_n` | Integer | nu |  | `0` |  |
| `flight_sum` | Float | nu |  | `0.0` |  |
| `flight_sumsq` | Float | nu |  | `0.0` |  |
| `backspaces` | Integer | nu |  | `0` |  |
| `active_ms` | Float | nu |  | `0.0` | timp de tastare, fără pauzele > 2 s |
| `last_down_ms` | Float | da |  |  | pentru flight între loturi |
| `hold_ms_mean` | Float | nu |  | `0.0` |  |
| `hold_ms_sd` | Float | nu |  | `0.0` |  |
| `flight_ms_mean` | Float | nu |  | `0.0` |  |
| `flight_ms_sd` | Float | nu |  | `0.0` |  |
| `backspace_rate` | Float | nu |  | `0.0` |  |
| `keys_per_min` | Float | nu |  | `0.0` |  |
| `fatigue_index` | Float | da |  |  |  |
| `status` | String(8) | nu |  | `'unknown'` |  |
| `is_baseline` | Boolean | nu |  | `False` | intră în baseline-ul contului |

Constrângeri și indecși: INDEX `ix_keystroke_sessions_crew_id` (crew_id)

### `measurements` — `Measurement` (measurements.py)

TABEL LUNG: o valoare pe rând. Pulsul de noapte, HRV, temperatura de la senzor, scorurile pe zi (landing_readiness, stress_index, loading_score…). metric_key = cheile din contract/api (secțiunea 3).

| Coloană | Tip | Null | Cheie | Implicit | Notă |
|---|---|---|---|---|---|
| `id` | Integer | nu | PK |  |  |
| `crew_id` | String(16) | nu | FK → `crew.id` |  |  |
| `metric_key` | String(40) | nu |  |  |  |
| `value` | Float | nu |  |  |  |
| `unit` | String(16) | nu |  |  |  |
| `measured_at` | UTCDateTime | nu |  |  |  |
| `mission_day` | Integer | nu |  |  |  |
| `source` | String(12) | nu |  |  | device \| manual \| simulated |
| `device_id` | String(40) | da |  |  |  |

Constrângeri și indecși: INDEX `ix_meas_crew_metric_day` (crew_id, metric_key, mission_day)

### `packets` — `Packet` (link.py)

| Coloană | Tip | Null | Cheie | Implicit | Notă |
|---|---|---|---|---|---|
| `id` | String(16) | nu | PK |  | "pk-0007" |
| `seq` | Integer | nu |  |  |  |
| `direction` | String(4) | nu |  |  | down \| up |
| `kind` | String(16) | nu |  |  | alert_l3 \| weekly_summary \| earth_reply \| donki_alert |
| `status` | String(12) | nu |  |  | queued \| in_transit \| delivered \| rejected |
| `title` | String(160) | nu |  |  |  |
| `sender` | String(80) | nu |  |  |  |
| `level` | Integer | da |  |  |  |
| `alert_status` | String(8) | da |  |  |  |
| `crew_id` | String(16) | da | FK → `crew.id` |  |  |
| `alert_id` | String(16) | da | FK → `alerts.id` |  |  |
| `in_reply_to` | String(16) | da |  |  |  |
| `header` | JSON | nu |  |  | sealing.HEADER_FIELDS |
| `sealed` | LargeBinary | nu |  |  |  |
| `size_bytes` | Integer | nu |  |  |  |
| `created_at` | UTCDateTime | nu |  |  |  |
| `sent_at` | UTCDateTime | da |  |  |  |
| `arrives_at` | UTCDateTime | da |  |  |  |
| `delivered_at` | UTCDateTime | da |  |  |  |
| `signature_valid` | Boolean | da |  |  |  |
| `reject_reason` | String(16) | da |  |  | bad_signature \| replay |
| `payload` | JSON | da |  |  | completat la livrare |
| `read` | Boolean | nu |  | `False` | mesaj citit la bord |

Constrângeri și indecși: UNIQUE (direction, seq); INDEX `ix_packet_status` (status)

### `plan_steps` — `PlanStep` (alerts.py)

Un pas din planul alertei. `step_id` ("st-1") e unic doar în alerta lui (așa apare în contract).

| Coloană | Tip | Null | Cheie | Implicit | Notă |
|---|---|---|---|---|---|
| `id` | Integer | nu | PK |  |  |
| `alert_id` | String(16) | nu | FK → `alerts.id` |  |  |
| `step_id` | String(8) | nu |  |  |  |
| `position` | Integer | nu |  |  |  |
| `text` | Text | nu |  |  |  |
| `done` | Boolean | nu |  | `False` |  |
| `done_at` | UTCDateTime | da |  |  |  |

Constrângeri și indecși: UNIQUE (alert_id, step_id)

Relații: `alert` → Alert (lazy=raise)

### `pvt_results` — `PvtResult` (measurements.py)

Un test de reacție PVT-B (3 minute). Primele 2–3 sunt antrenament (is_practice) și nu intră în baseline.

| Coloană | Tip | Null | Cheie | Implicit | Notă |
|---|---|---|---|---|---|
| `id` | String(16) | nu | PK |  | "pvt-0031" |
| `crew_id` | String(16) | nu | FK → `crew.id` |  |  |
| `at` | UTCDateTime | nu |  |  |  |
| `mission_day` | Integer | nu |  |  |  |
| `n_trials` | Integer | nu |  |  |  |
| `mean_rt_ms` | Float | nu |  |  |  |
| `mean_speed` | Float | nu |  |  | media 1/RT, în 1/s |
| `lapses` | Integer | nu |  |  | RT ≥ 355 ms |
| `false_starts` | Integer | nu |  |  |  |
| `is_practice` | Boolean | nu |  | `False` |  |
| `baseline_speed` | Float | da |  |  |  |
| `deviation_sd` | Float | da |  |  |  |
| `status` | String(8) | nu |  |  |  |

Constrângeri și indecși: INDEX `ix_pvt_results_crew_id` (crew_id)

### `radiation_readings` — `RadiationReading` (measurements.py)

O citire a dozimetrului de la bord. O singură serie pentru toată nava.

| Coloană | Tip | Null | Cheie | Implicit | Notă |
|---|---|---|---|---|---|
| `id` | Integer | nu | PK |  |  |
| `t` | UTCDateTime | nu |  |  |  |
| `dose_rate_usv_h` | Float | nu |  |  |  |
| `mean_24h_usv_h` | Float | nu |  |  |  |
| `sheltered` | Boolean | nu |  | `False` |  |

Constrângeri și indecși: INDEX `ix_radiation_readings_t` (t)

### `rejections` — `Rejection` (security.py)

O valoare sau un pachet respins: semnătură invalidă, valoare imposibilă, senzor înghețat, replay.

| Coloană | Tip | Null | Cheie | Implicit | Notă |
|---|---|---|---|---|---|
| `id` | String(16) | nu | PK |  | "rj-0003" |
| `at` | UTCDateTime | nu |  |  |  |
| `kind` | String(16) | nu |  |  | RejectionKind |
| `source` | String(60) | nu |  |  | device_id sau packet id |
| `crew_id` | String(16) | da |  |  |  |
| `metric_key` | String(40) | da |  |  |  |
| `value` | Float | da |  |  |  |
| `message` | Text | nu |  |  |  |

### `revoked_tokens` — `RevokedToken` (users.py)

Tokenurile ieșite prin logout, până la expirare (security.tokens.revoke / is_revoked).

| Coloană | Tip | Null | Cheie | Implicit | Notă |
|---|---|---|---|---|---|
| `jti` | String(64) | nu | PK |  |  |
| `expires_at` | UTCDateTime | nu |  |  |  |

### `sim_state` — `SimState` (sim.py)

| Coloană | Tip | Null | Cheie | Implicit | Notă |
|---|---|---|---|---|---|
| `key` | String(40) | nu | PK |  |  |
| `value` | JSON | nu |  |  |  |

### `users` — `User` (users.py)

Un cont. Câte unul pe astronaut + contul `earth`. Parola doar ca hash (security.passwords).

| Coloană | Tip | Null | Cheie | Implicit | Notă |
|---|---|---|---|---|---|
| `id` | String(16) | nu | PK |  | "u-cm-2", "u-earth" |
| `username` | String(40) | nu |  unic |  |  |
| `password_hash` | String(255) | nu |  |  |  |
| `display_name` | String(80) | nu |  |  |  |
| `initials` | String(4) | nu |  |  |  |
| `role` | String(12) | nu |  |  | astronaut \| cmo \| earth |
| `crew_id` | String(16) | da | FK → `crew.id` |  | None doar pentru earth |

Constrângeri și indecși: INDEX `ix_users_username` (username)

