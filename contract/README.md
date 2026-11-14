# SHADOW — contractele

**Versiunea 1.2** · NASA Space Apps 2026

Un contract e înțelegerea dintre două părți ale aplicației: ce își trimit, în ce formă, cu ce reguli. Dacă ambele
părți îl respectă, se pot construi separat și se potrivesc la integrare. Fiecare contract are o **sursă de adevăr
în cod**, iar documentația de aici e generată din ea, deci nu poate rămâne în urmă.

| Contract | Între | Sursa de adevăr | Documentația |
|---|---|---|---|
| **API** | frontend ↔ backend | `backend/app/schemas.py` + routerele | [api/README.md](api/README.md) · `api/openapi.yaml` |
| **AI** | backend ↔ serviciul AI | `ai/service/schemas.py` (copie în `backend/app/ai_schemas.py`) | [ai/README.md](ai/README.md) · `ai/openapi.yaml` |
| **Securitate** | backend ↔ codul de securitate | semnăturile din `backend/app/security/` | [security/README.md](security/README.md) |
| **Data** | backend (și AI) ↔ `data/` | `backend/app/datafiles.py` | [data/README.md](data/README.md) · `data/schemas/*.schema.json` |

```
                ┌────────────┐
                │  frontend  │
                └─────┬──────┘
                      │ API (HTTP + SSE)
┌──────────┐    ┌─────▼──────┐  AI (HTTP)   ┌────────────┐
│  data/   ├───►│  backend   ├─────────────►│ serviciul  │
└────┬─────┘    │ ┌────────┐ │              │     AI     │
     │  Data    │ │security│ │ Securitate   └─────▲──────┘
     │          │ └────────┘ │ (apeluri)          │
     │          └────────────┘                    │
     └────────────── catalog + surse (corpus) ────┘
```

## Ce citește fiecare echipă

| Echipa | Citește |
|---|---|
| Frontend | `api/README.md` |
| Backend | toate patru |
| Securitate | `security/README.md`, apoi `api/README.md` secțiunile 4 și 8 |
| AI | `ai/README.md`, apoi `data/README.md` (catalogul și sursele) |
| Cine ține `data/` | `data/README.md` |

## Regulile comune

1. **Se editează sursa de adevăr și `guide.md`**, niciodată un `README.md` generat (în afară de acesta).
2. După orice schimbare, din rădăcina repo-ului:
   ```bash
   uv run --project backend python scripts/smoke.py        # verifică tot
   uv run --project backend python scripts/build_docs.py   # regenerează contract/
   bash scripts/gen_types.sh                               # tipurile TypeScript, dacă s-a schimbat API-ul
   ```
3. **Fără anunț:** câmpuri noi opționale, endpoint-uri noi, texte corectate.
   **Cu anunț înainte:** câmpuri noi obligatorii, valori noi în enumerări, semnături de funcții, formatul unui fișier.
   **Doar împreună cu cealaltă echipă:** redenumiri, ștergeri, schimbări de tip sau de cale.
4. PR-urile care schimbă un contract au titlul care începe cu `contract:`.

## Istoric

| Versiune | Ce s-a schimbat |
|---|---|
| 1.2 | contractele interne (AI, securitate, data); misiunea pornește în ziua 96; derulatorul doar pe trecut; ceasul doar înainte; `AiStatus.mode = "mock"`; structura nouă a repo-ului |
| 1.1 | cont separat pentru fiecare astronaut; `/auth/accounts`, `/auth/logout`, `429 too_many_attempts` |
| 1.0 | contractul API inițial, 55 de endpoint-uri, server mock |
