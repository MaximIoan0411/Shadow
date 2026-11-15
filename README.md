# SHADOW

**Every astronaut, against their own baseline.**
How you say you feel, next to what your body shows in flight.

SHADOW is an astronaut health-monitoring app built for **NASA Space Apps 2026**. It follows each crew member on a
long mission (the scenario is day 96 of a transit to Mars), compares every signal with that person's own baseline,
and raises an alert early, when several weak signals point the same way. Every threshold comes from a published
scientific source, the AI doctor runs on a local model and cites its sources, and the link to Earth is encrypted,
signed and delayed by 11 min 40 s, as it would be on the way to Mars.

> A decision-support prototype, not a medical device. All crew data is simulated.

---

## Contents

1. [What SHADOW does](#1-what-shadow-does)
2. [The four pillars](#2-the-four-pillars)
3. [Typing rhythm: fatigue without reading a single word](#3-typing-rhythm-fatigue-without-reading-a-single-word)
4. [Alerts: from the astronaut to Earth](#4-alerts-from-the-astronaut-to-earth)
5. [The AI doctor: a local model that cites its sources](#5-the-ai-doctor-a-local-model-that-cites-its-sources)
6. [Solar storm simulator](#6-solar-storm-simulator)
7. [Security, audited with Claude Mythos](#7-security-audited-with-claude-mythos)
8. [Only published science](#8-only-published-science)
9. [Architecture](#9-architecture)
10. [Running it](#10-running-it)
11. [Demo guide](#11-demo-guide)
12. [Repository](#12-repository)
13. [Limits](#13-limits)

---

## 1. What SHADOW does

On a mission to Mars there is no doctor on board who knows each astronaut's normal, and Earth answers 23 minutes
later. SHADOW keeps that normal for every crew member and watches how far each day moves from it.

| | |
|---|---|
| **Personal baseline** | every value is compared with the person's own median and spread, not with a population average |
| **Four pillars** | typing rhythm and reaction, heart, immune system, bone loading, shown on a 3D body |
| **Weak signals that connect** | small deviations from two or more pillars become *"Possible onset of an illness"* before any single value crosses an alert threshold |
| **Perception gap** | the morning check-in (*"how do you feel?"*) is set against what the data shows; a large gap is a signal in itself |
| **Three alert levels** | the astronaut, the crew medical officer, Earth |
| **AI doctor** | answers questions about the person's own data, using NASA and CSA documents, with citations |
| **Earth link** | real delay (11 min 40 s each way), communication windows, encrypted and signed packets |
| **Solar storm** | replays the real May 2024 storm (NASA DONKI): the dose rate climbs, the alert fires, the crew takes shelter |
| **Evidence** | every threshold with its source, the automated tests, the recommendation catalog, the access log |

It runs as a desktop app (Electron) on the ship's console, in a browser, and on a phone.

## 2. The four pillars

| Pillar | What it watches | Signals |
|---|---|---|
| **Typing** (behaviour) | fatigue and attention | keystroke rhythm during normal typing, psychomotor vigilance test (reaction time) |
| **Heart** (cardiovascular) | adaptation to microgravity | night heart rate, heart rate variability, blood pressure |
| **Sentinel** (immune) | early signs of an infection or of stress | night pulse, body temperature, sleep, a stress index that includes radiation dose and days of isolation |
| **Loading** (musculoskeletal) | bone loss | the mechanical load of each exercise session (sets, reps, weight), projected against the bone loss expected in flight |

Each pillar gives a score from 0 to 100 and a state: *within limits*, *watch* or *alert*. The engine
(`backend/app/engine/`) is plain, deterministic code: the same data always gives the same result, and every result
lists the evidence behind it.

Two rules work across pillars:

- **Cross signals.** Small deviations that are not alerts on their own (night pulse +7 bpm, temperature +0.4 °C,
  one hour less sleep, typing 18 % slower) are weighed together. When independent signals from at least two pillars
  agree, SHADOW raises *"Possible onset of an illness"*, with a confidence level.
- **Environmental cause.** When the same signal appears in three or more crew members on the same day, the cause is
  most likely the cabin, not the person, and SHADOW says so.

## 3. Typing rhythm: fatigue without reading a single word

Astronauts type every day: logs, checklists, messages. SHADOW uses that typing as a fatigue sensor that needs no
extra device and no extra time.

**What is recorded.** For each key: when it was pressed, when it was released, and its class (`char`, `space`,
`backspace`, `enter`, `other`). **The text itself never leaves the keyboard.** The app cannot know what was typed,
only how.

**What is computed** (`backend/app/engine/pillars/behavioral.py`):

| Feature | Meaning | Weight in the fatigue index |
|---|---|---|
| hold time | how long a key stays pressed | 0.4 |
| typing speed | keys per minute | 0.4 |
| flight time | the time from one key to the next | 0.1 |
| correction rate | share of backspaces | 0.1 |

Each feature is compared with the person's own baseline (built over the first 7 days, at least 30 keys per
session). The deviations become a **fatigue index from 0 to 100**: 50 is *watch*, 75 is *alert*. A session in which
the astronaut types 18 % slower and holds keys 239 ms longer than usual is flagged, and the finding joins the cross
signals.

**Why it works.** Hold time during natural typing detects psychomotor impairment with an AUC of 0.76–0.79
(Giancardo et al. 2015, *Scientific Reports* 5:9678); typing patterns track time awake and mental fatigue
(Fang et al. 2026, *PLOS Digital Health* 5(3):e0001281). The **reaction test** (PVT) on the same screen is the
measure NASA already uses on the ISS; SHADOW compares each result with the astronaut's own earlier tests.

## 4. Alerts: from the astronaut to Earth

| Level | Who sees it | Example |
|---|---|---|
| 1 | the astronaut | typing slower than usual, one bad night |
| 2 | the astronaut and the **crew medical officer** | night pulse +7 bpm three nights in a row |
| 3 | **Earth** (the flight surgeon), sent by the medical officer | the medical officer asks for advice |

Each alert shows what was observed, against which baseline, the source of the threshold, and a plan from the
recommendation catalog (*what to do, what to measure, when to check again*). SHADOW never recommends medicines or
doses and never makes a diagnosis: the crew medical officer decides.

**Only the medical officer sends an alert to Earth.** The alert leaves the ship as an encrypted and signed packet,
waits for a communication window, and reaches the flight surgeon 11 min 40 s later. The reply makes the same trip
back. Earth sees only the packets that arrived, never the crew's raw data.

## 5. The AI doctor: a local model that cites its sources

The AI doctor answers questions such as *"Why has my night pulse gone up?"* or *"How am I doing today?"*.

| | |
|---|---|
| **Model** | Qwen3.5-4B (Q4_K_M quantisation), served by `llama-server` from llama.cpp. About 3 GB: it runs on the ship's own computer, with no cloud service and no data leaving the ship |
| **For the demo** | the same `llama-server` runs on a Google Colab GPU, behind an HTTPS tunnel that requires an API key, because the presentation laptop has no GPU (`ai/colab/shadow_llm.ipynb`) |
| **Knowledge** | retrieval over 22 official documents (NASA Human Research Program evidence reports, NASA risk pages, the OCHMO radiation brief, CSA space medicine) plus the team's thresholds, recommendations and body functions; hybrid search (meaning and keywords) with a relevance cut-off |
| **Context** | the person's own data: pillar states, open alerts, the zones of the body that need attention |
| **Citations** | every answer lists the sources it used; the reader opens each one |
| **Guard** | `ai/service/guard.py` blocks medicines, doses, diagnoses, off-topic questions, and any *"you are doing well"* while an alert is open; a blocked answer is replaced with the catalog text, marked as such |
| **Fallback** | if the model does not answer in time, the app shows the catalog recommendation with its source and says so openly |
| **Privacy** | conversations are not stored; the backend checks that the person may see the data before the question reaches the model |

## 6. Solar storm simulator

On a mission to Mars, the ship sees a solar storm before Earth can warn it: NASA's warning needs time to be issued
and another 11 min 40 s to arrive.

SHADOW replays the **Gannon storm of 11 May 2024**: solar particle event `2024-05-11T02:10:00-SEP-001` (GOES
>100 MeV), linked to an X5.8 flare, a coronal mass ejection and **Ground Level Enhancement 74**, taken from **NASA
DONKI** (`data/donki/donki_sep_event.json`).

1. The on-board dosimeter's dose rate climbs above the background of the last 24 hours.
2. After **3 consecutive readings at or above 2× the 24-hour mean** (threshold from Guo et al. 2021, MSL/RAD
   measurements), the alert *"Solar storm: go to the shelter"* fires for the whole crew.
3. The astronaut confirms *"I am in the shelter"*; the dose rate inside drops, as in NASA's shielding brief
   (OCHMO-TB-020: 214 mSv without and 68 mSv with optimised stowage).
4. The screen shows the dose accumulated during the event and how many minutes the on-board alert came **before**
   NASA's warning arrived.

The event, its time and its sources are real; the shape of the dose curve is synthetic, because the dose measured
during the 2024 event is not published.

## 7. Security, audited with Claude Mythos

Health data from a crew is sensitive, and a link to Earth can be spoofed. Security is in the running code
(`backend/app/security/`), not only on paper.

| Threat | Defence |
|---|---|
| fake measurements | every wearable signs its readings with **Ed25519**; unknown devices, devices signing for another astronaut and replayed readings are rejected |
| impossible or frozen sensor values | physical limits per metric; the same value 20 times in a row is rejected as a frozen sensor and shown in *Evidence* |
| a forged or altered packet on the Earth link | **AES-256-GCM** encryption plus an **Ed25519** signature; the signature is checked **before** decryption, and any change to the header or content rejects the packet |
| stolen passwords | only **argon2id** hashes are stored; 5 wrong passwords in 5 minutes lock the account for 60 s |
| stolen or reused sessions | signed tokens (HS256, 12 h) bound to one account; sign-out revokes the token, and the revocation survives a restart |
| an astronaut reading a colleague's data | one access rule for every `/crew/{id}` route; the medical officer's reads are logged |
| secret changes to the record | a **hash-chained access log**: each entry carries the fingerprint of the one before; the chain is verified at start-up and on demand, and a broken chain is shown as an alert |

**The audit.** The security code and the access rules were audited with **Claude Mythos**, Anthropic's
Mythos-class model. Each weakness found was first reproduced on the running code, then fixed, then covered by
a test that fails on the old code: **16 vulnerabilities were found and fixed in the application**, among them a
login bypass through test tokens, unsigned measurements, packets stored in clear text and a token that worked again
after a restart. `security/audit/check_endpoints.py` checks that all 57 endpoints refuse a request without a valid
token (except the four that must be public) and that no astronaut can open another's data.

Details: `security/threat-model.md`, `security/architecture.md`, `security/checklist.md`,
`security/audit/findings.md`.

## 8. Only published science

SHADOW does not invent numbers. Every threshold the engine uses lives in `data/parameters.json` with its citation,
DOI or URL, and a note on how strong the evidence is.

| | |
|---|---|
| **169 thresholds**, each with its scientific source | *Evidence → Thresholds and sources* |
| **50 recommendations** in the catalog, each with its source | *Evidence → Recommendation catalog* |
| **22 official NASA and CSA documents** behind the AI doctor | `ai/corpus/` |
| **111 automated tests** of the engine, visible in the app | *Evidence → Automated tests* |
| **319 backend tests** in total, including security | `cd backend && uv run pytest` |

Where the literature gives no number, SHADOW says so and marks the value as a working hypothesis.

## 9. Architecture

```
wearables (signed) ─┐
                    ▼
app (Next.js, Electron) ──► backend (FastAPI, :8000) ──► AI service (:8001) ──► llama-server (local, or Colab via tunnel)
                                 │
                                 ├── engine: baselines, pillars, cross signals, triage, radiation
                                 ├── security: signatures, encryption, tokens, access log
                                 └── Earth link: queue, delay, windows, sealed packets ──► Earth (flight surgeon)
```

| Part | Technology |
|---|---|
| `frontend/` | Next.js 15, React 19, Tailwind CSS 4, a WebGL 3D body, Electron; English interface |
| `backend/` | Python, FastAPI, SQLAlchemy (async, SQLite), uv |
| `ai/` | FastAPI service, retrieval index, llama.cpp `llama-server` |
| `contract/` | the API contract (OpenAPI) shared by the frontend and the backend |
| `data/` | thresholds, catalog, texts, NASA DONKI event, mission scenario |
| `security/` | threat model, architecture, audit, key generation |

## 10. Running it

You need **Node.js 20+** and **uv** (https://docs.astral.sh/uv/).

```bash
cd frontend
npm install
npm run app
```

`npm run app` builds the interface and opens the SHADOW window. It also starts the backend and the AI service if
they are not already running, and stops them on exit. The first start takes about a minute while uv installs the
dependencies.

Without a model, the AI doctor answers with the catalog text and says so. To connect the model, see `ai/README.md`
(a local `llama-server`, or the Colab notebook).

To run the parts separately:

```bash
cd backend && uv run uvicorn app.main:app --port 8000      # API, docs at http://localhost:8000/docs
cd ai && uv run uvicorn service.main:app --port 8001       # AI service
cd frontend && npm run dev                                 # interface in the browser, http://localhost:3000
```

Every start replays the scenario from day 96. The access log and revoked tokens are kept.

### Test accounts

| Account | Password | Role |
|---|---|---|
| Commander | `cm1-shadow` | astronaut |
| Mission Specialist 2 | `cm2-shadow` | astronaut, with the scenario's alerts |
| Crew Medical Officer | `cm3-shadow` | crew medical officer |
| Flight Engineer | `cm4-shadow` | astronaut |
| Flight Surgeon (*On Earth* tab) | `earth-shadow` | Earth |

Each window has its own session (`Ctrl+N` opens another), so the ship and Earth can sit side by side.

## 11. Demo guide

The demo panel opens from the flask icon in the header or with `Ctrl+Shift+D`.

| To show | Do this |
|---|---|
| the body and the cross signal | sign in as *Mission Specialist 2*: *My body*, then a pillar |
| the perception gap | *Check-in*: mood 4/5, then save; the gap appears on the right |
| typing rhythm | *Rhythm and reaction*: type a sentence; the reaction test is on the second tab |
| the AI doctor with sources | *Alerts* → the night pulse alert → ask the AI doctor; open *1 source* |
| an alert sent to Earth | *Crew Medical Officer* → *Medical queue* → *Send to Earth*; then *Flight Surgeon* sees it arrive |
| a forged packet | demo panel → *Spoofed packet*; it arrives *Rejected: invalid signature* and is never decrypted |
| a frozen sensor and the access log | demo panel → *Frozen sensor*; then *Evidence* → *Rejections* and *Access log* |
| the solar storm | *Radiation* → demo panel → *Solar storm*; wait for the alert, then *I am in the shelter* |

## 12. Repository

| Folder | Contents |
|---|---|
| `frontend/` | interface and desktop app (`frontend/README.md`) |
| `backend/` | API, engine, security code, tests (`backend/README.md`) |
| `ai/` | AI doctor service, corpus, Colab notebook (`ai/README.md`) |
| `contract/` | API, AI, security and data contracts |
| `data/` | shared data and its sources (`data/README.md`) |
| `security/` | threat model, architecture, checklist, audit |
| `scripts/` | documentation generator, contract checks, data validation |
| `docs/` | plan, task lists, design assets |

The team documentation inside the folders is written in Romanian; the interface and this README are in English.

## 13. Limits

- **Not a medical device.** SHADOW supports the crew medical officer's decision; it does not diagnose or treat.
- **Simulated data.** The crew, their wearables and their history are simulated; the solar event and all the
  thresholds are real.
- **Open security items** are listed in `security/audit/findings.md`: no rate limiting, the database and keys are not
  encrypted on disk, no automatic sign-out, and the demo panel is open to every account.
- **The Earth link is simulated** in the same process; the delay, the windows and the cryptography are real.
