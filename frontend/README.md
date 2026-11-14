# SHADOW — frontend și aplicația de desktop

Interfața (Next.js 15, React 19, Tailwind v4), în engleză, legată de backend prin contractul din
`../contract/api/` și `src/lib/shadow-api.d.ts`. Rulează ca aplicație de desktop (Electron) sau în browser.

## Pornire pe Windows (prima dată)

Ai nevoie de **Node.js 20+** și, pentru backend, de **uv** (https://docs.astral.sh/uv/).

```powershell
cd Desktop\shadow\frontend
npm install
npm run app
```

`npm run app` construiește interfața și deschide fereastra SHADOW. Dacă backend-ul nu rulează deja, aplicația îl
pornește singură din `..\backend` (cu `uv run uvicorn`) și îl oprește la ieșire. Prima pornire a backend-ului
durează un minut, cât `uv` instalează dependențele; ecranul de autentificare arată „Starting the SHADOW server…”.

La fel pornește și **serviciul AI** din `..\ai` (portul 8001), dacă nu rulează deja. Modelul lui se alege în
`ai\.env` (vezi `ai\README.md`); fără model sau fără serviciu, medicul AI răspunde cu textul din catalog și
ecranul spune asta deschis. `SHADOW_NO_AI=1` oprește pornirea automată.

Pornirile următoare: `npm run app:start` (fără reconstruire).

Dacă vrei backend-ul separat (ca să-i vezi log-urile), într-un alt terminal:

```powershell
cd Desktop\shadow\backend
uv run uvicorn app.main:app --port 8000
```

## Conturile de test

| Cont | Parolă | Rol |
|---|---|---|
| Comandant | `cm1-shadow` | astronaut |
| Specialist de misiune 2 | `cm2-shadow` | astronaut, cu alertele din scenariu |
| Ofițer medical de bord | `cm3-shadow` | ofițer medical (coada medicală) |
| Inginer de zbor | `cm4-shadow` | astronaut |
| Medicul de zbor (fila „On Earth”) | `earth-shadow` | Pământul |

Fiecare fereastră are sesiunea ei (`Ctrl+N` deschide încă una), deci poți ține nava și Pământul alături.
Panoul de demo: iconița din antet sau `Ctrl+Shift+D`.

## Comenzi

| Comandă | Ce face |
|---|---|
| `npm run app` | construiește interfața și deschide aplicația de desktop |
| `npm run app:start` | deschide aplicația (fără reconstruire) |
| `npm run app:dev` | aplicația de desktop peste `next dev`, cu reîncărcare la salvare |
| `npm run dev` | doar în browser, la http://localhost:3000 (catalogul de design: `/kit`) |
| `npm run backend` | pornește backend-ul (`uv`) |
| `npm run typecheck` | verifică tipurile |
| `npm run api:types` | regenerează tipurile din contract |

## Cum e legat de backend

- Frontend-ul cere totul pe **aceeași origine**, la `/api/v1/…`. În `npm run dev` cererile le duce Next
  (`next.config.ts`, `SHADOW_API_URL`), în aplicație le duce Electron (`electron/main.cjs`). Fără CORS.
- `src/lib/endpoints.ts` are câte o funcție pentru fiecare endpoint din contract; `src/lib/queries.ts`, citirile.
- **Fără polling.** Un singur flux de evenimente (`src/lib/events.tsx`) invalidează datele la `alert.*`,
  `packet.*`, `radiation.*`, `dashboard.changed`; după o reconectare se reîncarcă tot.
- Tokenul stă doar în memorie. „Switch account” oprește colectorul de tastare, închide evenimentele, deconectează și
  golește toate datele.
- Tastarea trimite doar timpii și clasa tastei, niciodată textul.

## Structura

```
electron/        main.cjs (fereastra, serverul local, proxy, pornirea backend-ului), preload.cjs, build.cjs, dev.cjs
public/brand/    logo-ul
src/app/         login, (ship)/{dashboard, checkin, rhythm, exercise, alerts, ai, radiation, evidence, cmo},
                 mission-control/{, evidence}, kit
src/components/  ui, layout, body, charts, alerts, ai, keystrokes, pvt, link, radiation, evidence
src/lib/         api, endpoints, queries, events, session, status, format, toast, hooks, useKeystrokes, desktop
src/styles/      tokens.css (sistemul de design, vezi DESIGN.md)
```
