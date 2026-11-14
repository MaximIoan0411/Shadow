# frontend — interfața SHADOW (Next.js)

**Cine lucrează aici:** frontend (2)

Next.js (App Router) + TypeScript + Tailwind v4, cu sistemul de design preluat din Quaternion.

```bash
npm install
cp .env.local.example .env.local        # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev                             # http://localhost:3000  (deocamdată duce la /kit)
```

Backend-ul mock trebuie pornit în paralel: `cd ../backend && uv sync && uv run uvicorn app.main:app --reload --port 8000`.

| Citește | Pentru |
|---|---|
| `DESIGN.md` (aici) + pagina `/kit` | componentele, culorile, regulile vizuale |
| `../docs/FRONTEND_SARCINI.md` | ce construim: ecranele, în ordinea priorității |
| `../contract/api/README.md` | endpoint-urile, modelele, erorile, evenimentele live |

`src/lib/api.ts` (clientul) și `src/lib/shadow-api.d.ts` (tipurile) vorbesc cu backend-ul **doar prin contract**.
După o schimbare de contract: `npm run api:types` (sau `bash ../scripts/gen_types.sh`).
