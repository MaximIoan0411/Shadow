# ai — medicul AI (serviciu separat)

**Cine lucrează aici:** AI

Serviciu propriu pe portul **8001**. Singurul lui client e backend-ul. Acum rulează ca **mock**: răspunde după
contract, fără model (reformulează recomandarea primită și îi citează sursa).

```bash
uv sync
uv run uvicorn service.main:app --reload --port 8001     # http://localhost:8001/docs
```

| Citește | Pentru |
|---|---|
| `../contract/ai/README.md` | contractul cu backend-ul: cereri, răspunsuri, erori, limita de 20 s |
| `../docs/AI_SARCINI.md` | ce construim: modelul local, corpusul, RAG, promptul, evaluarea, planul B |

`service/schemas.py` e contract: o copie identică stă în `backend/app/ai_schemas.py`, iar `scripts/smoke.py`
pică la orice diferență. Se schimbă amândouă în același PR.

Nu intră în git: `models/` (fișierele GGUF) și `index/` (indexul RAG, se reface din `corpus/`).
