# ai — medicul AI (serviciu separat)

**Cine lucrează aici:** AI

Serviciu propriu pe portul **8001**. Singurul lui client e backend-ul. Pentru o întrebare: caută 3–4 fragmente în
baza de cunoștințe, construiește promptul, cere răspunsul de la model, verifică regulile și întoarce doar citările
folosite. Răspunde în **engleză**, ca interfața.

```
aplicația → backend (8000) → serviciul AI (8001, pe laptop) → llama-server (local sau pe Colab, prin tunel)
```

## Pornire

```bash
uv sync
uv run python -m rag.ingest                                # o dată: indexul (≈4 min pe un procesor slab)
uv run uvicorn service.main:app --port 8001                # http://localhost:8001/docs
```

Fără model (`ai/.env` lipsă sau gol) serviciul rulează ca **mock**: reformulează recomandarea din catalog, cu sursa ei.

Aplicația de desktop (`npm run app` în `frontend/`) pornește singură acest serviciu dacă nu rulează deja; comanda
de mai sus e pentru când vreți să-i vedeți log-urile. Indexul (`rag.ingest`) se construiește tot de mână, o dată.

## Modelul pe Colab

1. Deschideți `colab/shadow_llm.ipynb` în Google Colab (`File → Upload notebook`), din browserul de pe laptopul pe
   care rulează serviciul. `Runtime → Change runtime type → A100` sau `L4` (merge și pe T4, dar prima compilare
   durează 40+ minute, fiindcă mașina are doar 2 nuclee).
2. În Colab, la **Secrets** (cheia din bara din stânga), adăugați și dați acces notebook-ului:
   | Secret | Ce e |
   |---|---|
   | `SHADOW_LLM_API_KEY` | o parolă lungă, inventată de voi (dacă lipsește, notebook-ul generează una) |
   | `NGROK_AUTHTOKEN` | opțional; fără el tunelul e cloudflared, fără cont |
   | `NGROK_DOMAIN` | opțional; domeniul fix gratuit din ngrok, ca adresa să nu se schimbe la fiecare pornire |
3. `Runtime → Run all`. Prima rulare pe o placă nouă compilează llama.cpp (≈10 min pe A100/L4); compilarea se
   păstrează în Drive, separat pentru fiecare tip de placă, iar pornirile următoare durează ≈1 minut.
4. Copiați cele trei rânduri afișate la final în `ai/.env` (model: `.env.example`; nu intră în git).
5. Reporniți serviciul. `GET /status` trebuie să arate `ready: true`, `mode: colab_simulation`; în aplicație, chatul
   arată „Colab simulation”.

Tab-ul Colab trebuie lăsat deschis: sesiunea gratuită se oprește după o perioadă fără activitate sau după câteva ore.
Fără domeniu fix, adresa tunelului se schimbă la fiecare pornire, deci `ai/.env` se actualizează de fiecare dată.

Dacă tunelul sau Colab cad, serviciul întoarce repede `503 model_unavailable`, iar backend-ul arată textul din catalog.
Pentru un model local, același `llama-server` pe acest calculator: `SHADOW_LLM_URL=http://127.0.0.1:8080`,
`SHADOW_LLM_MODE=local`.

## Baza de cunoștințe

| Ce | Unde |
|---|---|
| lista documentelor oficiale (NASA, CSA) | `corpus/catalog.json` |
| textele lor, descărcate o dată (intră în git, ca demo-ul să meargă offline) | `corpus/docs/`, `corpus/sources.json` |
| descărcarea, din nou | `uv run --extra corpus python -m rag.fetch` |
| datele echipei, indexate și ele (praguri, recomandări, funcțiile corpului) | `../data/` |
| indexul (nu intră în git) | `index/`, refăcut cu `uv run python -m rag.ingest` |
| căutarea: după sens + după cuvinte, cu prag de relevanță | `rag/retrieve.py` |

Modelul de embedding (`BAAI/bge-small-en-v1.5`, ≈65 MB) se descarcă la primul `rag.ingest` în `models/embeddings/`;
după aceea totul merge fără internet.

## Evaluare

```bash
uv run python -m eval.run_eval            # căutarea: aduce surse din subiectul corect?
uv run python -m eval.run_eval --chat     # răspunsurile, prin serviciu (cu modelul din ai/.env)
```

| Citește | Pentru |
|---|---|
| `../contract/ai/README.md` | contractul cu backend-ul: cereri, răspunsuri, erori, limita de 20 s |
| `../docs/AI_SARCINI.md` | ce construim: modelul, corpusul, RAG, promptul, evaluarea, planul B |
| `prompts/system.md`, `prompts/answer.md` | regulile modelului și cererea completată |
| `service/guard.py` | verificările din cod: fără medicamente, doze, diagnostice; citările folosite |

`service/schemas.py` e contract: o copie identică stă în `backend/app/ai_schemas.py`, iar `scripts/smoke.py`
pică la orice diferență. Se schimbă amândouă în același PR.
